import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { isDeepStrictEqual } from 'node:util';

// このファイル(cli/lib/init.js)の 2 つ上がパッケージ直下
export const PACKAGE_ROOT = fileURLToPath(new URL('../..', import.meta.url));
const PACKAGE_JSON = JSON.parse(fs.readFileSync(path.join(PACKAGE_ROOT, 'package.json'), 'utf8'));
export const VERSION = PACKAGE_JSON.version;

// package.json の "files" のうち、CLI 自身(cli/)以外を導入先にコピーする。ディレクトリは配下をすべて含める。
// "files" にはパスをそのまま書く前提で、ワイルドカードは解釈しない。
const PATHS_TO_COPY = PACKAGE_JSON.files.filter((entry) => !entry.startsWith('cli/'));

// 既存があれば上書きせず、足りない設定だけを足す
const SETTINGS_FILE = '.claude/settings.json';
// KARURA が管理するファイルなので、既存と内容が違っても衝突にせず書き直す
export const MANIFEST_FILE = '.karura/manifest.json';

const WRITE_ACTIONS = new Set(['create', 'overwrite', 'merge']);

/**
 * 導入先の 1 ファイルに対する操作。planInit が作り、applyPlan が実行する。
 * @typedef {object} Step
 * @property {string} relativePath 導入先から見た相対パス(区切りは /)
 * @property {string} destPath 書き込み先の絶対パス
 * @property {'create' | 'overwrite' | 'merge' | 'skip' | 'conflict'} action
 * @property {Buffer} [content] 書き込む内容。conflict 以外で持つ
 * @property {boolean} executable 書き込んだあとに実行権限を付けるか
 * @property {string} [reason] conflict の理由
 * @property {boolean} [forceable] conflict を --force で解消できるか
 */

const toPosixPath = (nativePath) => nativePath.split(path.sep).join('/');
const sha256 = (content) => createHash('sha256').update(content).digest('hex');
const toJsonBuffer = (value) => Buffer.from(`${JSON.stringify(value, null, 2)}\n`);
const isPlainObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);

// 導入先の中のパスは導入先からの相対パスで示す。導入先そのものと導入先の外は絶対パスで示す
function toDisplayPath(targetDir, absolutePath) {
  const relativePath = path.relative(targetDir, absolutePath);
  const isOutsideTarget =
    relativePath === '..' || relativePath.startsWith(`..${path.sep}`) || path.isAbsolute(relativePath);
  if (relativePath === '' || isOutsideTarget) return absolutePath;
  return toPosixPath(relativePath);
}

// ホームフォルダに導入すると、~/.claude/ と ~/CLAUDE.md がすべてのプロジェクトに効いてしまう
export function isHomeDirectory(dir) {
  const homeDir = os.homedir();
  if (path.resolve(dir) === path.resolve(homeDir)) return true;
  try {
    return fs.realpathSync.native(dir) === fs.realpathSync.native(homeDir);
  } catch {
    // dir がまだ無いなら、ホームフォルダではない
    return false;
  }
}

export function listFilesToCopy() {
  const files = [];
  for (const copyPath of PATHS_TO_COPY) {
    const absolutePath = path.join(PACKAGE_ROOT, copyPath);
    if (!fs.statSync(absolutePath).isDirectory()) {
      files.push(copyPath);
      continue;
    }
    // シンボリックリンクは isFile() が false になるため、コピー対象から外れる
    for (const entry of fs.readdirSync(absolutePath, { recursive: true, withFileTypes: true })) {
      if (!entry.isFile()) continue;
      const entryPath = path.join(entry.parentPath, entry.name);
      files.push(toPosixPath(path.relative(PACKAGE_ROOT, entryPath)));
    }
  }
  return files.sort();
}

// existing の値を残したまま、additions にしかないキーと配列の要素だけを足す
export function addMissing(existing, additions) {
  if (Array.isArray(existing) && Array.isArray(additions)) {
    const merged = [...existing];
    for (const item of additions) {
      const alreadyIncluded = merged.some((current) => isDeepStrictEqual(current, item));
      if (!alreadyIncluded) merged.push(item);
    }
    return merged;
  }
  if (isPlainObject(existing) && isPlainObject(additions)) {
    const merged = { ...existing };
    for (const [key, value] of Object.entries(additions)) {
      merged[key] = Object.hasOwn(existing, key) ? addMissing(existing[key], value) : value;
    }
    return merged;
  }
  // 値どうし、または型が食い違う場合は、既存の値を優先する
  return existing;
}

// 導入先のパスを根元から 1 つずつたどり、書き込めない理由があれば返す。なければ null を返す。
// - シンボリックリンク・ハードリンク: たどると導入先の外のファイルを書き換えるおそれがある
// - 途中のパスにあるファイル: フォルダを作れず、書き込みが途中で失敗する
function findUnwritableReason(targetDir, relativePath) {
  const segments = relativePath.split('/');
  let currentPath = targetDir;
  for (const [index, segment] of segments.entries()) {
    currentPath = path.join(currentPath, segment);
    let stat;
    try {
      stat = fs.lstatSync(currentPath);
    } catch (error) {
      // ここから先はまだ無いので、新しく作れる
      if (error.code === 'ENOENT') return null;
      throw error;
    }
    const displayPath = toDisplayPath(targetDir, currentPath);
    const isLastSegment = index === segments.length - 1;
    if (stat.isSymbolicLink()) return `${displayPath} がシンボリックリンクです`;
    if (!isLastSegment && !stat.isDirectory()) return `${displayPath} がフォルダではありません`;
    if (isLastSegment && !stat.isFile()) return 'ファイルではないものが置かれています';
    if (isLastSegment && stat.nlink > 1) return '別の場所のファイルとハードリンクでつながっています';
  }
  return null;
}

function findNearestExistingDirectory(filePath) {
  let dir = path.dirname(filePath);
  // ルートまでたどったら止める(存在しないドライブを指定された場合など)
  while (!fs.existsSync(dir) && path.dirname(dir) !== dir) dir = path.dirname(dir);
  return dir;
}

// 書き込む操作について、書き込む権限がなければ理由を返す。権限があれば null を返す。
// 書き込みの途中で権限エラーになり、一部だけ書いた状態を残さないため。
function findPermissionDeniedReason(step, targetDir) {
  if (!WRITE_ACTIONS.has(step.action)) return null;
  // まだ無いファイルは、すでにある一番近いフォルダに書き込めるかで判断する
  const checkedPath = step.action === 'create' ? findNearestExistingDirectory(step.destPath) : step.destPath;
  try {
    fs.accessSync(checkedPath, fs.constants.W_OK);
    return null;
  } catch {
    return `${toDisplayPath(targetDir, checkedPath)} に書き込む権限がありません`;
  }
}

function planSettingsMerge(karuraContent, destPath) {
  const existingContent = fs.readFileSync(destPath);
  let existingSettings;
  try {
    // Windows のエディタが先頭に付けることがある BOM は、JSON.parse では読めないため取り除く
    existingSettings = JSON.parse(existingContent.toString('utf8').replace(/^\uFEFF/, ''));
  } catch {
    // 利用者の deny 設定などを失わないよう、--force を付けても上書きしない
    return { action: 'conflict', reason: 'JSON として読めません', forceable: false };
  }
  const karuraSettings = JSON.parse(karuraContent.toString('utf8'));
  const mergedSettings = addMissing(existingSettings, karuraSettings);
  if (isDeepStrictEqual(mergedSettings, existingSettings)) {
    return { action: 'skip', content: existingContent };
  }
  return { action: 'merge', content: toJsonBuffer(mergedSettings) };
}

/** @returns {Step} */
function planFile(relativePath, targetDir, { force }) {
  const sourcePath = path.join(PACKAGE_ROOT, relativePath);
  const destPath = path.join(targetDir, relativePath);
  const content = fs.readFileSync(sourcePath);
  const executable = (fs.statSync(sourcePath).mode & 0o111) !== 0;
  const step = { relativePath, destPath, executable };

  const unwritableReason = findUnwritableReason(targetDir, relativePath);
  if (unwritableReason) return { ...step, action: 'conflict', reason: unwritableReason, forceable: false };
  if (!fs.existsSync(destPath)) return { ...step, action: 'create', content };
  if (relativePath === SETTINGS_FILE) return { ...step, ...planSettingsMerge(content, destPath) };
  if (content.equals(fs.readFileSync(destPath))) return { ...step, action: 'skip', content };
  if (force) return { ...step, action: 'overwrite', content };
  return { ...step, action: 'conflict', reason: '既存のファイルと内容が異なります', forceable: true };
}

/** @returns {Step} */
function planManifest(targetDir, fileSteps) {
  const destPath = path.join(targetDir, MANIFEST_FILE);
  const step = { relativePath: MANIFEST_FILE, destPath, executable: false };
  const unwritableReason = findUnwritableReason(targetDir, MANIFEST_FILE);
  if (unwritableReason) return { ...step, action: 'conflict', reason: unwritableReason, forceable: false };

  // 衝突したファイルは内容を持たない。衝突があれば何も書き込まないので、除いて記録してかまわない
  const writableSteps = fileSteps.filter((fileStep) => fileStep.action !== 'conflict');
  const hashes = Object.fromEntries(writableSteps.map((fileStep) => [fileStep.relativePath, sha256(fileStep.content)]));
  const content = toJsonBuffer({ karuraVersion: VERSION, files: hashes });
  if (!fs.existsSync(destPath)) return { ...step, action: 'create', content };
  if (content.equals(fs.readFileSync(destPath))) return { ...step, action: 'skip', content };
  return { ...step, action: 'overwrite', content };
}

/**
 * 何も書き込まずに、導入記録を含むファイルごとの操作を決める。
 * @returns {Step[]}
 */
export function planInit(targetDir, { force = false } = {}) {
  const fileSteps = listFilesToCopy().map((relativePath) => planFile(relativePath, targetDir, { force }));
  const steps = [...fileSteps, planManifest(targetDir, fileSteps)];
  return steps.map((step) => {
    const permissionDeniedReason = findPermissionDeniedReason(step, targetDir);
    if (!permissionDeniedReason) return step;
    return { ...step, action: 'conflict', reason: permissionDeniedReason, forceable: false };
  });
}

// 読める人にだけ実行権限を足す。0755 に固定すると、利用者が狭めていた既存のファイルの権限を広げてしまうため
function addExecutePermission(filePath) {
  const permissions = fs.statSync(filePath).mode & 0o777;
  fs.chmodSync(filePath, permissions | ((permissions & 0o444) >> 2));
}

/** @param {Step[]} steps */
export function applyPlan(steps) {
  if (steps.some((step) => step.action === 'conflict')) {
    throw new Error('衝突があるため書き込めません。');
  }
  for (const step of steps) {
    if (!WRITE_ACTIONS.has(step.action)) continue;
    fs.mkdirSync(path.dirname(step.destPath), { recursive: true });
    fs.writeFileSync(step.destPath, step.content);
    if (step.executable) addExecutePermission(step.destPath);
  }
}
