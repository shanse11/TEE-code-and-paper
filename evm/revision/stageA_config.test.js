'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { ROOT, DEFAULT_CONFIG, loadConfig, validateConfig } = require('./experiment_config');
const { freeze } = require('./freeze_experiment');

function config() { return JSON.parse(fs.readFileSync(DEFAULT_CONFIG, 'utf8')); }
function temporary(t, prefix) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  return directory;
}

test('默认阶段 A 配置可加载且不含占位符', () => {
  const loaded = loadConfig();
  assert.equal(loaded.status, 'pass');
  assert.equal(loaded.config.workload.concurrencyUnit, 'inflight_batches');
  assert.deepEqual(loaded.config.workload.batchSize, [1, 8, 32]);
  assert.deepEqual(loaded.config.workload.payloadKiBPerTask, [1, 8, 32]);
  assert.deepEqual(loaded.config.workload.concurrency, [1, 4, 16]);
  assert.equal(loaded.config.build.solidity, '0.8.26');
  assert.equal(loaded.config.build.hardhatAccounts.count, 40);
});

test('配置拒绝必填版本、错误类型、非正载荷和并发及模糊旧字段', () => {
  for (const change of [
    value => delete value.schemaVersion,
    value => value.chain.chainId = '31337',
    value => value.workload.payloadKiBPerTask = [0],
    value => value.workload.concurrency = [0],
    value => { value.workload.payloadKiB = 8; delete value.workload.payloadKiBPerTask; },
    value => value.build.solidity = '<read-from-config>'
  ]) {
    const value = config(); change(value);
    assert.equal(validateConfig(value).ok, false);
  }
  const legacy = config(); delete legacy.workload.payloadKiBPerTask; legacy.workload.payloadKiB = 8; legacy.workload.payloadScope = 'per-task';
  const normalized = validateConfig(legacy);
  assert.equal(normalized.ok, true);
  assert.deepEqual(normalized.config.workload.payloadKiBPerTask, [8]);
});

test('validate-only 不创建 run，且公共后端缺资源被明确阻塞', t => {
  const root = temporary(t, 'stageA-validate-');
  const runDir = path.join(root, 'not-created');
  const result = freeze({ config: null, runDir, runId: null, resume: false, validateOnly: true, selfTest: false });
  assert.equal(result.validation.status, 'pass');
  assert.equal(fs.existsSync(runDir), false);
  const publicConfig = config(); publicConfig.backends.da = 'public';
  const blocked = validateConfig(publicConfig);
  assert.equal(blocked.ok, true); assert.equal(blocked.status, 'blocked');
});

test('冻结创建完整清单，默认不覆盖非空目录，self-test 写入三种状态', t => {
  const root = temporary(t, 'stageA-freeze-');
  const runDir = path.join(root, 'run');
  const result = freeze({ config: null, runDir, runId: 'stageA-test-run', resume: false, validateOnly: false, selfTest: true });
  assert.equal(result.manifest.status, 'ready');
  for (const relative of ['manifest/run_manifest.json', 'manifest/config.resolved.json', 'manifest/source_files.sha256', 'manifest/environment_public.json', 'manifest/dependencies.json', 'manifest/git_status.txt', 'manifest/git_diff_stat.txt', 'raw/experiment_records.jsonl', 'raw/experiment_events.jsonl', 'raw/failures.jsonl', 'validation/config_validation.json', 'validation/record_validation.json', 'validation/secret_scan.json', 'logs/freeze_experiment.log', 'summary.json']) assert.equal(fs.existsSync(path.join(runDir, relative)), true, relative);
  const manifest = JSON.parse(fs.readFileSync(path.join(runDir, 'manifest/run_manifest.json'), 'utf8'));
  assert.equal(manifest.runId, 'stageA-test-run'); assert.equal(manifest.gitHead, '615bb3e9f1ae3b88b87f488decc61854cd555e16');
  assert.equal(manifest.sourceFileSha256Path, 'manifest/source_files.sha256');
  const sourceHashes = fs.readFileSync(path.join(runDir, 'manifest/source_files.sha256'), 'utf8');
  assert.match(sourceHashes, /evm\/revision\/experiment_config\.js/);
  assert.doesNotMatch(sourceHashes, /stageA-freeze-selftest/);
  const env = JSON.parse(fs.readFileSync(path.join(runDir, 'manifest/environment_public.json'), 'utf8'));
  assert.deepEqual(Object.keys(env.sensitiveEnvironmentExists).sort(), ['BEACON_API_URL', 'BLOB_BATCH_ANCHOR_ADDRESS', 'ETHERSCAN_API_KEY', 'SEPOLIA_PRIVATE_KEY', 'SEPOLIA_RPC_URL']);
  const summary = JSON.parse(fs.readFileSync(path.join(runDir, 'summary.json'), 'utf8'));
  assert.deepEqual(summary.records, { total: 3, pass: 1, fail: 1, blocked: 1, skipped: 0 });
  assert.throws(() => freeze({ config: null, runDir, runId: null, resume: false, validateOnly: false, selfTest: false }), /非空/);
  assert.doesNotThrow(() => freeze({ config: null, runDir, runId: null, resume: true, validateOnly: false, selfTest: false }));
});

test('CLI 帮助、相对 run 拒绝和仓库相对 config', t => {
  const script = path.join(ROOT, 'evm/revision/freeze_experiment.js');
  const help = spawnSync(process.execPath, [script, '--help'], { cwd: ROOT, encoding: 'utf8' });
  assert.equal(help.status, 0); assert.match(help.stdout, /--validate-only/);
  const bad = spawnSync(process.execPath, [script, '--run-dir', 'relative'], { cwd: ROOT, encoding: 'utf8' });
  assert.notEqual(bad.status, 0);
  const root = temporary(t, 'stageA-cli-');
  const ok = spawnSync(process.execPath, [script, '--config', 'evm/revision/config/stageA.local.json', '--run-dir', path.join(root, 'run')], { cwd: ROOT, encoding: 'utf8' });
  assert.equal(ok.status, 0, ok.stderr);
});
