import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { after, test } from 'node:test';
import { MANIFEST_FILE, PACKAGE_ROOT, VERSION, addMissing, listFilesToCopy } from '../lib/init.js';

const KARURA_BIN = path.join(PACKAGE_ROOT, 'cli', 'bin', 'karura.js');
const TEST_ROOT = fs.mkdtempSync(path.join(os.tmpdir(), 'karura-test-'));
after(() => fs.rmSync(TEST_ROOT, { recursive: true, force: true }));

let tempDirCount = 0;
const makeTempDir = () => fs.mkdtempSync(path.join(TEST_ROOT, `${tempDirCount++}-`));
const runKarura = (...args) => runKaruraWith({}, ...args);
const runKaruraWith = (spawnOptions, ...args) =>
  spawnSync(process.execPath, [KARURA_BIN, ...args], { encoding: 'utf8', ...spawnOptions });
const readFile = (dir, relativePath) => fs.readFileSync(path.join(dir, relativePath));
const writeFile = (dir, relativePath, content) => {
  fs.mkdirSync(path.dirname(path.join(dir, relativePath)), { recursive: true });
  fs.writeFileSync(path.join(dir, relativePath), content);
};
const readSettings = (dir) => JSON.parse(readFile(dir, '.claude/settings.json').toString('utf8'));
const KARURA_SETTINGS = readSettings(PACKAGE_ROOT);

// Windows ではシンボリックリンクの作成やファイルの権限の扱いが異なるため対象外にする
const skipOnWindows = { skip: process.platform === 'win32' };
// root は権限に関係なく書き込めるため、権限のテストは対象外にする
const skipOnWindowsOrRoot = { skip: process.platform === 'win32' || process.getuid?.() === 0 };

test('コピー対象に必要なファイルが含まれる', () => {
  const files = listFilesToCopy();
  for (const expected of [
    'CLAUDE.md',
    '.claude/settings.json',
    '.claude/skills/d1-business-requirement-document/SKILL.md',
    'scripts/check-markers.sh',
    'docs/D0.project-management/artifact-flow.md',
  ]) {
    assert.ok(files.includes(expected), expected);
  }
  assert.ok(files.every((file) => !file.startsWith('cli/')), 'CLI 自身はコピーしない');
});

test('空のディレクトリに全ファイルを作成し、導入記録を書く', () => {
  const dir = makeTempDir();
  const result = runKarura('init', dir);
  assert.equal(result.status, 0, result.stderr);

  const manifest = JSON.parse(readFile(dir, MANIFEST_FILE).toString('utf8'));
  assert.equal(manifest.karuraVersion, VERSION);
  assert.deepEqual(Object.keys(manifest.files), listFilesToCopy());
  for (const file of listFilesToCopy()) {
    const content = readFile(dir, file);
    assert.ok(content.equals(readFile(PACKAGE_ROOT, file)), file);
    assert.equal(manifest.files[file], createHash('sha256').update(content).digest('hex'), file);
  }
  if (process.platform !== 'win32') {
    assert.ok(fs.statSync(path.join(dir, 'scripts/check-markers.sh')).mode & 0o100);
  }
});

test('存在しないディレクトリを指定すると作成する', () => {
  const dir = path.join(makeTempDir(), 'new', 'project');
  assert.equal(runKarura('init', dir).status, 0);
  assert.ok(fs.existsSync(path.join(dir, 'CLAUDE.md')));
});

test('--dry-run は何も書き込まない', () => {
  const dir = makeTempDir();
  const result = runKarura('init', dir, '--dry-run');
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /作成\tCLAUDE\.md/);
  assert.deepEqual(fs.readdirSync(dir), []);
});

test('内容が異なる既存ファイルがあると、何も書き込まずに終了コード 1 で止まる', () => {
  const dir = makeTempDir();
  writeFile(dir, 'CLAUDE.md', '# 既存の規約\n');
  const result = runKarura('init', dir);
  assert.equal(result.status, 1);
  assert.match(result.stderr, /CLAUDE\.md\(既存のファイルと内容が異なります\)/);
  assert.match(result.stderr, /上書きしてよい場合は --force/);
  assert.equal(readFile(dir, 'CLAUDE.md').toString('utf8'), '# 既存の規約\n');
  assert.deepEqual(fs.readdirSync(dir), ['CLAUDE.md']);
});

test('--dry-run でも衝突があれば終了コード 1 を返す', () => {
  const dir = makeTempDir();
  writeFile(dir, 'CLAUDE.md', '# 既存の規約\n');
  const result = runKarura('init', dir, '--dry-run');
  assert.equal(result.status, 1);
  assert.match(result.stdout, /衝突\tCLAUDE\.md/);
});

test('--force は内容が異なる既存ファイルを上書きする', () => {
  const dir = makeTempDir();
  writeFile(dir, 'CLAUDE.md', '# 既存の規約\n');
  const result = runKarura('init', dir, '--force');
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /上書き\tCLAUDE\.md/);
  assert.ok(readFile(dir, 'CLAUDE.md').equals(readFile(PACKAGE_ROOT, 'CLAUDE.md')));
});

test('同じ内容の既存ファイルは衝突にせず、再実行できる', () => {
  const dir = makeTempDir();
  assert.equal(runKarura('init', dir).status, 0);
  const result = runKarura('init', dir);
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /変更なし \d+/);
});

test('ファイルの位置にディレクトリがあると、--force を付けても止まる', () => {
  const dir = makeTempDir();
  fs.mkdirSync(path.join(dir, 'CLAUDE.md'));
  const result = runKarura('init', dir, '--force');
  assert.equal(result.status, 1);
  assert.match(result.stderr, /CLAUDE\.md\(ファイルではないものが置かれています\)/);
  assert.match(result.stderr, /--force を付けても書き込まないものがあります/);
});

test('シンボリックリンクのファイルは、--force を付けてもたどらずに止まる', skipOnWindows, () => {
  const root = makeTempDir();
  const dir = path.join(root, 'project');
  const outsideFile = path.join(root, 'important.txt');
  fs.writeFileSync(outsideFile, '大事なファイル\n');
  fs.mkdirSync(path.join(dir, '.karura'), { recursive: true });
  fs.symlinkSync(outsideFile, path.join(dir, MANIFEST_FILE));

  for (const extraArgs of [[], ['--force']]) {
    const result = runKarura('init', dir, ...extraArgs);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /\.karura\/manifest\.json\(\.karura\/manifest\.json がシンボリックリンクです\)/);
  }
  assert.equal(fs.readFileSync(outsideFile, 'utf8'), '大事なファイル\n');
  assert.deepEqual(fs.readdirSync(dir), ['.karura']);
});

test('シンボリックリンクのフォルダは、たどらずに止まる', skipOnWindows, () => {
  const root = makeTempDir();
  const dir = path.join(root, 'project');
  const outsideDir = path.join(root, 'outside');
  fs.mkdirSync(dir);
  fs.mkdirSync(outsideDir);
  fs.symlinkSync(outsideDir, path.join(dir, 'scripts'));

  const result = runKarura('init', dir);
  assert.equal(result.status, 1);
  assert.match(result.stderr, /scripts\/check-markers\.sh\(scripts がシンボリックリンクです\)/);
  assert.deepEqual(fs.readdirSync(outsideDir), []);
  assert.deepEqual(fs.readdirSync(dir), ['scripts']);
});

test('途中のパスにファイルがあると、何も書き込まずに止まる', () => {
  const dir = makeTempDir();
  writeFile(dir, 'scripts', 'not a directory\n');
  const result = runKarura('init', dir, '--force');
  assert.equal(result.status, 1);
  assert.match(result.stderr, /scripts\/check-markers\.sh\(scripts がフォルダではありません\)/);
  assert.deepEqual(fs.readdirSync(dir), ['scripts']);
});

test('addMissing は既存の値を残し、足りないキーと配列の要素だけを足す', () => {
  const userHook = { matcher: 'Bash', hooks: [{ type: 'command', command: 'echo user' }] };
  const karuraHook = { matcher: 'Write', hooks: [{ type: 'command', command: 'echo karura' }] };
  const existing = { model: 'opus', permissions: { allow: ['A'], deny: ['X'] }, hooks: { PostToolUse: [userHook] } };
  const additions = {
    model: 'sonnet',
    permissions: { allow: ['A', 'B'] },
    hooks: { PostToolUse: [karuraHook], Stop: [karuraHook] },
  };
  assert.deepEqual(addMissing(existing, additions), {
    model: 'opus',
    permissions: { allow: ['A', 'B'], deny: ['X'] },
    hooks: { PostToolUse: [userHook, karuraHook], Stop: [karuraHook] },
  });
});

test('既存の settings.json は、導入先の設定を残したまま KARURA の設定を足す', () => {
  const dir = makeTempDir();
  const existingSettings = { model: 'opus', permissions: { deny: ['Bash(rm:*)'] } };
  writeFile(dir, '.claude/settings.json', JSON.stringify(existingSettings));
  const result = runKarura('init', dir);
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /統合\t\.claude\/settings\.json/);
  assert.deepEqual(readSettings(dir), addMissing(existingSettings, KARURA_SETTINGS));
});

test('KARURA の設定をすでに含む settings.json は書き換えない', () => {
  const dir = makeTempDir();
  const existingText = `${JSON.stringify({ ...KARURA_SETTINGS, model: 'opus' })}\n`;
  writeFile(dir, '.claude/settings.json', existingText);
  assert.equal(runKarura('init', dir).status, 0);
  assert.equal(readFile(dir, '.claude/settings.json').toString('utf8'), existingText);
});

test('JSON として読めない settings.json は、--force を付けても上書きしない', () => {
  const dir = makeTempDir();
  writeFile(dir, '.claude/settings.json', '{ invalid');
  for (const extraArgs of [[], ['--force']]) {
    const result = runKarura('init', dir, ...extraArgs);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /settings\.json\(JSON として読めません\)/);
  }
  assert.equal(readFile(dir, '.claude/settings.json').toString('utf8'), '{ invalid');
});

test('先頭に BOM がある settings.json も読んで統合する', () => {
  const dir = makeTempDir();
  const existingSettings = { permissions: { deny: ['Bash(rm:*)'] } };
  writeFile(dir, '.claude/settings.json', `\uFEFF${JSON.stringify(existingSettings)}`);
  const result = runKarura('init', dir);
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(readSettings(dir), addMissing(existingSettings, KARURA_SETTINGS));
});

test('ハードリンクのファイルは、--force を付けても書き込まずに止まる', () => {
  const root = makeTempDir();
  const dir = path.join(root, 'project');
  const outsideFile = path.join(root, 'important.txt');
  fs.mkdirSync(dir);
  fs.writeFileSync(outsideFile, '大事なファイル\n');
  fs.linkSync(outsideFile, path.join(dir, 'CLAUDE.md'));

  const result = runKarura('init', dir, '--force');
  assert.equal(result.status, 1);
  assert.match(result.stderr, /CLAUDE\.md\(別の場所のファイルとハードリンクでつながっています\)/);
  assert.equal(fs.readFileSync(outsideFile, 'utf8'), '大事なファイル\n');
});

test('上書きしたスクリプトの実行権限は、読める人にだけ付ける', skipOnWindows, () => {
  const dir = makeTempDir();
  writeFile(dir, 'scripts/check-markers.sh', 'echo old\n');
  fs.chmodSync(path.join(dir, 'scripts/check-markers.sh'), 0o600);
  const result = runKarura('init', dir, '--force');
  assert.equal(result.status, 0, result.stderr);
  assert.equal(fs.statSync(path.join(dir, 'scripts/check-markers.sh')).mode & 0o777, 0o700);
});

test('書き込む権限のないフォルダがあると、何も書き込まずに止まる', skipOnWindowsOrRoot, () => {
  const dir = makeTempDir();
  const readOnlyDir = path.join(dir, 'scripts');
  fs.mkdirSync(readOnlyDir, { mode: 0o555 });
  try {
    const result = runKarura('init', dir);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /scripts\/check-markers\.sh\(scripts に書き込む権限がありません\)/);
    assert.deepEqual(fs.readdirSync(dir), ['scripts']);
  } finally {
    fs.chmodSync(readOnlyDir, 0o755);
  }
});

test('ホームフォルダには導入しない', () => {
  const homeDir = makeTempDir();
  const env = { ...process.env, HOME: homeDir, USERPROFILE: homeDir };
  for (const [spawnOptions, args] of [[{ env }, ['init', homeDir]], [{ env, cwd: homeDir }, ['init']]]) {
    const result = runKaruraWith(spawnOptions, ...args);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /ホームフォルダには導入できません/);
  }
  assert.deepEqual(fs.readdirSync(homeDir), []);
});

test('--version はパッケージのバージョンを表示する', () => {
  const result = runKarura('--version');
  assert.equal(result.status, 0);
  assert.equal(result.stdout.trim(), VERSION);
});

test('引数なしではヘルプを表示する', () => {
  const result = runKarura();
  assert.equal(result.status, 0);
  assert.match(result.stdout, /karura init \[dir\]/);
});

test('不明なコマンド・オプションは終了コード 2 で止まる', () => {
  assert.equal(runKarura('deploy').status, 2);
  assert.equal(runKarura('init', '--bogus').status, 2);
  assert.equal(runKarura('init', 'a', 'b').status, 2);
});
