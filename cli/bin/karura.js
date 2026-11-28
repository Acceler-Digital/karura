#!/usr/bin/env node
import path from 'node:path';
import { parseArgs } from 'node:util';
import { MANIFEST_FILE, VERSION, applyPlan, isHomeDirectory, planInit } from '../lib/init.js';

const EXIT_CODE = { SUCCESS: 0, FAILURE: 1, USAGE_ERROR: 2 };

const HELP_TEXT = `KARURA v${VERSION}

使い方:
  karura init [dir]   KARURA のスキル・規約一式を dir(既定: カレントディレクトリ)に導入する

オプション:
  --dry-run           書き込まずに、行う操作の一覧だけを表示する
  --force             内容が異なる既存ファイルを上書きする
  -h, --help          このヘルプを表示する
  -v, --version       バージョンを表示する
`;

const ACTION_LABELS = {
  create: '作成',
  overwrite: '上書き',
  merge: '統合',
  skip: '変更なし',
  conflict: '衝突',
};

class UsageError extends Error {}

const formatStep = (step) => `${step.relativePath}${step.reason ? `(${step.reason})` : ''}`;

function printPlan(steps, targetDir) {
  for (const step of steps) console.log(`${ACTION_LABELS[step.action]}\t${formatStep(step)}`);
  console.log(`\n書き込みは行っていません(--dry-run)。導入先: ${targetDir}`);
}

function printConflicts(conflicts) {
  console.error('次のファイルに書き込めないため、何も変更せずに終了しました。');
  for (const step of conflicts) console.error(`  ${formatStep(step)}`);
  if (conflicts.every((step) => step.forceable)) {
    console.error('\n上書きしてよい場合は --force を付けて再実行してください。');
  } else {
    console.error('\n--force を付けても書き込まないものがあります。該当するものを直すか取り除いてから、再実行してください。');
  }
}

function printSummary(steps, targetDir) {
  // 既存のファイルに手を入れた操作だけは、1 件ずつ示す
  for (const step of steps) {
    if (step.action === 'overwrite' || step.action === 'merge') {
      console.log(`${ACTION_LABELS[step.action]}\t${step.relativePath}`);
    }
  }
  const counts = ['create', 'overwrite', 'merge', 'skip']
    .map((action) => [action, steps.filter((step) => step.action === action).length])
    .filter(([, count]) => count > 0)
    .map(([action, count]) => `${ACTION_LABELS[action]} ${count}`)
    .join('、');
  console.log(`KARURA v${VERSION} を ${targetDir} に導入しました(${counts})。`);
  console.log(`${MANIFEST_FILE} は今後の更新で使う導入記録です。リポジトリにコミットしてください。`);
  console.log('\n次の手順: 導入先で Claude Code を起動し、/d1-business-requirement-document を実行してください。');
}

function runInit(dir, { force, dryRun }) {
  const targetDir = path.resolve(dir);
  if (isHomeDirectory(targetDir)) {
    console.error('ホームフォルダには導入できません。ここに入れると、すべてのプロジェクトの Claude Code の設定が変わるためです。');
    console.error('プロジェクトのフォルダで実行するか、karura init <プロジェクトのフォルダ> のように指定してください。');
    return EXIT_CODE.FAILURE;
  }
  const steps = planInit(targetDir, { force });
  const conflicts = steps.filter((step) => step.action === 'conflict');
  const hasConflicts = conflicts.length > 0;

  if (dryRun) {
    printPlan(steps, targetDir);
    // 本番で衝突するなら、dry-run でも失敗として返す
    return hasConflicts ? EXIT_CODE.FAILURE : EXIT_CODE.SUCCESS;
  }
  if (hasConflicts) {
    printConflicts(conflicts);
    return EXIT_CODE.FAILURE;
  }
  applyPlan(steps);
  printSummary(steps, targetDir);
  return EXIT_CODE.SUCCESS;
}

function parseCommandLine(argv) {
  try {
    return parseArgs({
      args: argv,
      allowPositionals: true,
      options: {
        force: { type: 'boolean', default: false },
        'dry-run': { type: 'boolean', default: false },
        help: { type: 'boolean', short: 'h', default: false },
        version: { type: 'boolean', short: 'v', default: false },
      },
    });
  } catch (error) {
    throw new UsageError(error.message);
  }
}

function main(argv) {
  const { values: options, positionals } = parseCommandLine(argv);
  const [command, ...commandArgs] = positionals;

  if (options.version) {
    console.log(VERSION);
    return EXIT_CODE.SUCCESS;
  }
  if (options.help || command === undefined) {
    console.log(HELP_TEXT);
    return EXIT_CODE.SUCCESS;
  }
  if (command === 'init') {
    if (commandArgs.length > 1) throw new UsageError('init に渡せるディレクトリは 1 つだけです。');
    const [dir = '.'] = commandArgs;
    return runInit(dir, { force: options.force, dryRun: options['dry-run'] });
  }
  throw new UsageError(`不明なコマンドです: ${command}`);
}

try {
  process.exitCode = main(process.argv.slice(2));
} catch (error) {
  console.error(`エラー: ${error.message}`);
  if (error instanceof UsageError) {
    console.error('\n使い方は --help を付けて実行すると確認できます。');
    process.exitCode = EXIT_CODE.USAGE_ERROR;
  } else {
    process.exitCode = EXIT_CODE.FAILURE;
  }
}
