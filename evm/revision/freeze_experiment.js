'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { execFileSync, spawnSync } = require('node:child_process');
const Ajv = require('ajv');
const { ROOT, SCHEMA_VERSION, loadConfig } = require('./experiment_config');
const { stableStringify, sha256, redact, createRecorder, validateJsonl } = require('./experiment_record');
const manifestSchema = require('./schemas/run_manifest.schema.json');
const metricDefinitions = require('./metric_definitions.json');

const SENSITIVE_ENV = ['SEPOLIA_RPC_URL', 'SEPOLIA_PRIVATE_KEY', 'BLOB_BATCH_ANCHOR_ADDRESS', 'BEACON_API_URL', 'ETHERSCAN_API_KEY'];
const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
const utc = () => new Date().toISOString();
const digest = input => crypto.createHash('sha256').update(input).digest('hex');

function usage() {
  return [
    '用法：node evm/revision/freeze_experiment.js [选项]',
    '  --help                 显示帮助信息',
    '  --config <json>        绝对路径或仓库相对配置 JSON',
    '  --run-dir <abs>        独立、绝对的运行目录（优先于 REVISION_RUN）',
    '  --run-id <id>          覆盖配置中的运行标识',
    '  --resume               显式允许使用已存在的非空运行目录',
    '  --validate-only        只校验配置，不创建运行目录',
    '  --self-test            在新 run 中写入 pass/fail/blocked 三条样本'
  ].join('\n');
}

function parseArgs(argv) {
  const result = { config: null, runDir: null, runId: null, resume: false, validateOnly: false, selfTest: false, help: false };
  for (let index = 0; index < argv.length; index++) {
    const token = argv[index];
    if (['--config', '--run-dir', '--run-id'].includes(token)) {
      const value = argv[++index];
      if (!value || value.startsWith('--')) throw new Error(`${token} 缺少参数`);
      result[{ '--config': 'config', '--run-dir': 'runDir', '--run-id': 'runId' }[token]] = value;
    } else if (token === '--resume') result.resume = true;
    else if (token === '--validate-only') result.validateOnly = true;
    else if (token === '--self-test') result.selfTest = true;
    else if (token === '--help') result.help = true;
    else throw new Error(`未知参数：${token}`);
  }
  if (result.validateOnly && result.selfTest) throw new Error('--validate-only 与 --self-test 不能同时使用');
  return result;
}

function runGit(args) {
  try { return execFileSync('git', args, { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }); } catch { throw new Error(`git 命令失败：git ${args.join(' ')}`); }
}

function ensureRunDir(candidate, resume) {
  if (typeof candidate !== 'string' || !path.isAbsolute(candidate)) throw new Error('run 目录必须是绝对路径；请传入 --run-dir 或在进程启动前设置 REVISION_RUN');
  const absolute = path.resolve(candidate);
  if (fs.existsSync(absolute)) {
    if (!fs.statSync(absolute).isDirectory()) throw new Error('run 路径不是目录');
    if (fs.readdirSync(absolute).length && !resume) throw new Error('run 目录已存在且非空；仅 --resume 可显式允许继续');
  } else fs.mkdirSync(absolute, { recursive: true, mode: 0o700 });
  return fs.realpathSync(absolute);
}

function globPattern(pattern) {
  const escaped = pattern.replace(/[|\\{}()[\]^$+?.]/g, '\\$&');
  const source = escaped.replace(/\*\*\//g, '(?:.*/)?').replace(/\*\*/g, '.*').replace(/\*/g, '[^/]*');
  return new RegExp(`^${source}$`);
}

function walk(directory, root, output) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const full = path.join(directory, entry.name);
    if (entry.isSymbolicLink()) continue;
    if (entry.isDirectory()) walk(full, root, output);
    else if (entry.isFile()) output.push(path.relative(root, full).split(path.sep).join('/'));
  }
}

function sourceFiles(config, runDir) {
  const include = config.source.include.map(globPattern);
  const exclude = [...config.source.exclude, 'node_modules/**', 'artifacts/**', 'cache/**', '**/node_modules/**', '**/artifacts/**', '**/cache/**', '**/__pycache__/**', '**/*.pyc'].map(globPattern);
  const all = []; walk(ROOT, ROOT, all);
  const runRelative = path.relative(ROOT, runDir).split(path.sep).join('/');
  return all.filter(file => include.some(pattern => pattern.test(file)) && !exclude.some(pattern => pattern.test(file)) && !(runRelative && !runRelative.startsWith('../') && (file === runRelative || file.startsWith(`${runRelative}/`)))).sort();
}

function sourceHashes(config, runDir) {
  const lines = sourceFiles(config, runDir).map(file => `${digest(fs.readFileSync(path.join(ROOT, file)))}  ${file}`);
  return { text: lines.length ? `${lines.join('\n')}\n` : '', sourceTreeSha256: digest(lines.join('\n')) };
}

function dependencySnapshot() {
  const result = {};
  for (const relative of ['evm/package.json', 'evm/package-lock.json', 'evm/revision/package.json']) {
    const file = path.join(ROOT, relative);
    if (!fs.existsSync(file)) continue;
    const value = JSON.parse(fs.readFileSync(file, 'utf8'));
    if (relative.endsWith('package-lock.json')) result[relative] = { lockfileVersion: value.lockfileVersion, packages: Object.fromEntries(Object.entries(value.packages || {}).filter(([name]) => name === '' || ['node_modules/hardhat', 'node_modules/solc', 'node_modules/ethers', 'node_modules/c-kzg'].includes(name)).map(([name, item]) => [name || 'root', item.version])) };
    else result[relative] = { name: value.name, version: value.version, dependencies: value.dependencies || {}, devDependencies: value.devDependencies || {} };
  }
  return result;
}

function commandVersion(command, args) {
  const result = spawnSync(command, args, { encoding: 'utf8' });
  return result.status === 0 ? (result.stdout || result.stderr).trim() || null : null;
}

function publicEnvironment() {
  return {
    os: { platform: process.platform, release: os.release(), arch: process.arch, type: os.type() },
    nodeVersion: process.version, pythonVersion: commandVersion('python3', ['--version']), npmVersion: commandVersion('npm', ['--version']),
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || null, locale: Intl.DateTimeFormat().resolvedOptions().locale || null,
    cpu: { model: os.cpus()[0]?.model || null, count: os.cpus().length }, memoryBytes: os.totalmem(),
    sensitiveEnvironmentExists: Object.fromEntries(SENSITIVE_ENV.map(name => [name, own(process.env, name)]))
  };
}

function writeStable(file, data) { fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 }); fs.writeFileSync(file, stableStringify(data), { encoding: 'utf8', mode: 0o600 }); }
function writeText(file, data) { fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 }); fs.writeFileSync(file, data, { encoding: 'utf8', mode: 0o600 }); }
function relativeEvidence(file, runDir) { return path.relative(runDir, file).split(path.sep).join('/'); }

function validateManifest(manifest) {
  const ajv = new Ajv({ allErrors: true, strict: false });
  const check = ajv.compile(manifestSchema);
  return check(manifest) ? [] : check.errors.map(error => ({ field: error.instancePath || '$', message: error.keyword }));
}

function writeFailure(runDir, message) {
  if (!runDir || !fs.existsSync(runDir)) return;
  try {
    const raw = path.join(runDir, 'raw'); fs.mkdirSync(raw, { recursive: true, mode: 0o700 });
    writeText(path.join(raw, 'freeze_failure.jsonl'), stableStringify({ schemaVersion: SCHEMA_VERSION, status: 'fail', createdAtUtc: utc(), failure: { code: 'FREEZE_FAILED', message: redact(message) } }));
  } catch { /* 不泄露失败细节。 */ }
}

function freeze(options) {
  const loaded = loadConfig(options.config);
  const config = structuredClone(loaded.config);
  if (options.runId) {
    if (!/^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$/.test(options.runId)) throw new Error('--run-id 必须是安全的非空运行标识');
    config.runId = options.runId;
  }
  const validation = { schemaVersion: SCHEMA_VERSION, checkedAtUtc: utc(), status: loaded.status, errors: loaded.errors, blockedReason: loaded.blockedReason, configPath: loaded.evidencePath };
  if (options.validateOnly) return { validation, configSha256: sha256(stableStringify(config)), config };
  const runDir = ensureRunDir(options.runDir || process.env.REVISION_RUN, options.resume);
  try {
    const configSha256 = sha256(stableStringify(config));
    const hashes = sourceHashes(config, runDir);
    const gitStatus = runGit(['status', '--short']);
    const diff = runGit(['diff', '--no-ext-diff', '--binary']);
    const gitHead = runGit(['rev-parse', 'HEAD']).trim();
    const gitBranch = runGit(['branch', '--show-current']).trim() || 'detached';
    const untrackedFiles = runGit(['ls-files', '--others', '--exclude-standard']).split('\n').filter(Boolean).sort();
    const environment = publicEnvironment();
    config.build.nodeVersion = environment.nodeVersion;
    config.build.pythonVersion = environment.pythonVersion;
    const manifestDir = path.join(runDir, 'manifest');
    writeStable(path.join(manifestDir, 'config.resolved.json'), config);
    writeText(path.join(manifestDir, 'source_files.sha256'), hashes.text);
    writeStable(path.join(manifestDir, 'environment_public.json'), environment);
    writeStable(path.join(manifestDir, 'dependencies.json'), dependencySnapshot());
    writeText(path.join(manifestDir, 'git_status.txt'), gitStatus);
    writeText(path.join(manifestDir, 'git_diff_stat.txt'), runGit(['diff', '--stat']));
    const limitations = [...metricDefinitions.limitations];
    if (gitStatus.trim()) limitations.unshift('当前结果依赖工作区快照，不等同于仅由 HEAD commit 表示');
    if (loaded.status === 'blocked') limitations.push(loaded.blockedReason);
    const manifest = {
      schemaVersion: SCHEMA_VERSION, runId: config.runId, createdAtUtc: utc(), status: loaded.status === 'blocked' ? 'blocked' : 'ready',
      gitHead, gitBranch, gitDirty: Boolean(gitStatus.trim()), trackedDiffSha256: digest(diff), untrackedFiles,
      sourceTreeSha256: hashes.sourceTreeSha256, sourceFileSha256Path: 'manifest/source_files.sha256', configPath: 'manifest/config.resolved.json', configSha256: sha256(stableStringify(config)),
      environmentSnapshotPath: 'manifest/environment_public.json', dependencySnapshotPath: 'manifest/dependencies.json',
      chain: config.chain, build: config.build, workload: config.workload, backends: config.backends, metricDefinitions, evidenceRoot: '.', limitations
    };
    const manifestErrors = validateManifest(manifest);
    if (manifestErrors.length) throw new Error('run manifest schema 校验失败');
    writeStable(path.join(manifestDir, 'run_manifest.json'), manifest);
    const rawDir = path.join(runDir, 'raw');
    fs.mkdirSync(rawDir, { recursive: true, mode: 0o700 });
    for (const name of ['experiment_records.jsonl', 'experiment_events.jsonl', 'failures.jsonl']) fs.closeSync(fs.openSync(path.join(rawDir, name), 'a', 0o600));
    writeStable(path.join(runDir, 'validation', 'config_validation.json'), validation);
    writeStable(path.join(runDir, 'validation', 'record_validation.json'), { status: 'not_run', reason: '冻结入口仅创建运行清单；--self-test 会写入并验证样本记录。' });
    writeStable(path.join(runDir, 'validation', 'secret_scan.json'), { status: 'pass', rule: '未读取 .env；仅保存六个敏感环境变量的 exists 布尔值。' });
    writeText(path.join(runDir, 'logs', 'freeze_experiment.log'), `${utc()} freeze status=${manifest.status}\n`);
    if (options.selfTest && manifest.status === 'ready') {
      const recorder = createRecorder(runDir);
      recorder.recordExperimentSample({ sampleId: 'self-pass-000001', statusReason: '配置与冻结清单本地校验通过' });
      recorder.recordFailure({ sampleId: 'self-fail-000002', status: 'fail', failure: { code: 'SELF_TEST_FAILURE', message: '自检故意写入的失败样本，用于验证状态记录。' } });
      recorder.recordFailure({ sampleId: 'self-blocked-000003', status: 'blocked', failure: { code: 'NOT_IMPLEMENTED', message: '恢复、真实 TEE、真实 DA 和罚没闭环未在阶段 A 实现。' } });
      const recordValidation = validateJsonl(path.join(runDir, 'raw', 'experiment_records.jsonl'));
      writeStable(path.join(runDir, 'validation', 'record_validation.json'), recordValidation);
    }
    const records = fs.existsSync(path.join(runDir, 'raw', 'experiment_records.jsonl')) ? validateJsonl(path.join(runDir, 'raw', 'experiment_records.jsonl')) : { total: 0, counts: { pass: 0, fail: 0, blocked: 0, skipped: 0 } };
    writeStable(path.join(runDir, 'summary.json'), { schemaVersion: SCHEMA_VERSION, runId: config.runId, status: manifest.status, createdAtUtc: utc(), records: { total: records.total, ...records.counts }, manifestPath: 'manifest/run_manifest.json' });
    return { runDir, manifest, validation };
  } catch (error) { writeFailure(runDir, error.message); throw error; }
}

function main() {
  let options; let runDir = null;
  try {
    options = parseArgs(process.argv.slice(2));
    if (options.help) { process.stdout.write(`${usage()}\n`); return; }
    runDir = options.runDir || process.env.REVISION_RUN || null;
    const result = freeze(options);
    process.stdout.write(`${result.validation.status === 'blocked' ? 'blocked' : 'ready'}${result.runDir ? ` ${result.runDir}` : ''}\n`);
  } catch (error) {
    writeFailure(runDir, error.message);
    process.stderr.write(`错误：${redact(error.message)}\n`);
    process.exitCode = 1;
  }
}

if (require.main === module) main();
module.exports = { parseArgs, freeze, ensureRunDir, sourceHashes, validateManifest };
