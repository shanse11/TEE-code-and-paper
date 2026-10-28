'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');
const Ajv = require('ajv');
const api = require('./experiment_record');
const { stableStringify, sha256, assertPublic, redact, validateRecord, validateEvent, validateJsonl, makeSample, createRecorder } = api;
const START = '2026-09-12T08:00:00.000Z';
const END = '2026-09-12T08:00:01.000Z';
function fixture() {
  const config = {
    schemaVersion: 'hybrid-tee-rollup.stageA.v1', runId: 'stageA-record-test',
    chain: { backend: 'hardhat', chainId: 31337, hardfork: 'cancun' },
    workload: { batchSize: [8, 32], payloadKiBPerTask: [1, 8], concurrency: [4, 16], stepCount: null },
    backends: { tee: 'simulated-only', da: 'local-mock-or-offline-only', blobMode: 'offline-only' }
  };
  const manifest = { runId: config.runId, gitHead: 'a'.repeat(40), configSha256: sha256(stableStringify(config)), chain: config.chain };
  return { config, manifest };
}
function sample(partial = {}) {
  const { config, manifest } = fixture();
  return makeSample(config, manifest, { startedAtUtc: START, endedAtUtc: END, ...partial });
}
function run(t) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'stageA-record-test-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  fs.mkdirSync(path.join(dir, 'manifest'));
  const { config, manifest } = fixture();
  fs.writeFileSync(path.join(dir, 'manifest/config.resolved.json'), stableStringify(config), 'utf8');
  fs.writeFileSync(path.join(dir, 'manifest/run_manifest.json'), stableStringify(manifest), 'utf8');
  return { dir, file: kind => path.join(dir, 'raw', kind), recorder: createRecorder(dir) };
}
function set(record, field, value) {
  const keys = field.split('.');
  let obj = record;
  for (const key of keys.slice(0, -1)) obj = obj[key];
  obj[keys.at(-1)] = value;
  if (value !== null) delete record.notApplicableReason[field];
}
function invalid(field, value) {
  const r = sample(); set(r, field, value);
  assert.ok(validateRecord(r).some(e => e.field === field), `应拒绝字段 ${field}`);
}

test('固定九个导出，稳定排序、单行和 SHA256', () => {
  assert.deepEqual(Object.keys(api).sort(), ['stableStringify', 'sha256', 'assertPublic', 'redact', 'validateRecord', 'validateEvent', 'validateJsonl', 'makeSample', 'createRecorder'].sort());
  assert.equal(stableStringify({ b: { y: 2, a: 1 }, a: ['甲\n乙', 3] }), '{"a":["甲\\n乙",3],"b":{"a":1,"y":2}}\n');
  assert.equal(stableStringify({ 2: 'b', 10: 'a' }), '{"10":"a","2":"b"}\n');
  assert.equal(sha256('abc'), 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
  assert.throws(() => stableStringify({ value: NaN }));
  assert.throws(() => stableStringify(new Array(1)));
});

test('完整默认值、不钳制并发、UUID 与逐项未测量解释', () => {
  const r = sample();
  assert.deepEqual(validateRecord(r), []);
  assert.equal(r.workload.batchSize, 8); assert.equal(r.workload.taskCount, 8);
  assert.equal(r.workload.configuredConcurrency, 4); assert.equal(r.workload.actualInFlight, null);
  assert.equal(r.workload.batchPayloadBytes, 8192);
  assert.match(r.sampleId, /^[0-9a-f-]{36}$/);
  for (const prefix of ['timeline', 'cost']) for (const [key, value] of Object.entries(r[prefix])) if (value === null) assert.ok(r.notApplicableReason[`${prefix}.${key}`]);
  for (const key of Object.keys(r.throughput)) for (const value of Object.values(r.throughput[key])) assert.equal(value, null);
  for (const [batchSize, concurrency] of [[1, 1], [1, 4], [1, 16], [8, 4], [32, 16]]) {
    const { config, manifest } = fixture(); config.workload.batchSize = [batchSize]; config.workload.concurrency = [concurrency];
    const record = makeSample(config, manifest);
    assert.equal(record.workload.configuredConcurrency, concurrency); assert.equal(record.workload.batchSize, batchSize);
  }
});

test('pass/fail/blocked/skipped 状态与 failure 约束', () => {
  for (const status of ['fail', 'blocked']) {
    assert.deepEqual(validateRecord(sample({ status, failure: { code: 'NOT_IMPLEMENTED', message: '尚未实现，仅记录阻塞' } })), []);
    assert.throws(() => sample({ status }));
  }
  assert.throws(() => sample({ failure: { code: 'ERR', message: '失败' } }));
  assert.throws(() => sample({ status: 'skipped' }));
  assert.deepEqual(validateRecord(sample({ status: 'skipped', statusReason: '本轮不适用' })), []);
  const r = sample(); delete r.notApplicableReason['cost.blobFee'];
  assert.ok(validateRecord(r).some(e => e.field === 'cost.blobFee'));
});

test('UTC 真实日期、闰日、时区、时间顺序及 1ms 容差', () => {
  for (const value of ['2026-02-30T08:00:00.000Z', '2026-02-29T08:00:00.000Z', '2026-09-12T08:00:00Z', '2026-09-12T08:00:00.000+00:00', '2026-09-12T24:00:00.000Z']) invalid('startedAtUtc', value);
  assert.deepEqual(validateRecord(sample({ startedAtUtc: '2024-02-29T08:00:00.000Z', endedAtUtc: '2024-02-29T08:00:00.000Z' })), []);
  invalid('endedAtUtc', '2026-09-12T07:59:59.000Z'); invalid('durationMs', 1002);
  assert.deepEqual(validateRecord(sample({ durationMs: 1001 })), []);
  const r = sample(); set(r, 'timeline.faultInjectedAt', END); set(r, 'timeline.failureDetectedAt', START);
  assert.ok(validateRecord(r).some(e => e.field === 'timeline.failureDetectedAt'));
});

test('负数、零、派生维度、并发关系及身份 schema', () => {
  for (const field of ['workload.batchSize', 'workload.taskCount', 'workload.configuredConcurrency', 'workload.actualInFlight', 'workload.dispatchGroupSize', 'workload.stepCount']) for (const value of [-1, 0, 1.5]) invalid(field, value);
  invalid('workload.actualInFlight', 5); invalid('workload.taskCount', 9);
  invalid('workload.payloadBytesPerTask', 1025); invalid('workload.batchPayloadBytes', 8193);
  invalid('workload.blobBytes', 123); invalid('schemaVersion', 'unknown'); invalid('chain.chainId', 1);
  invalid('gitHead', 'bad'); invalid('configSha256', 'bad'); invalid('sampleId', '../injected');
  assert.throws(() => sample({ workload: { actualInFlight: 1 } }));
  assert.deepEqual(validateRecord(sample({ workload: { actualInFlight: 1 }, statusReason: '实际调度未达到配置并发' })), []);
});

test('Blob 按 frame 编码及两种 padding，实际单 Blob 超容 blocked', () => {
  const r = sample({ workload: { frameBytes: 8192 } });
  assert.equal(r.workload.encodedBytes, Math.ceil(8192 / 31) * 32);
  assert.equal(r.workload.fieldPaddingBytes, Math.ceil(8192 / 31) * 31 - 8192);
  assert.equal(r.workload.paddingBytes, 131072 - r.workload.encodedBytes);
  assert.deepEqual(validateRecord(r), []);
  const large = sample({ workload: { batchSize: 32, payloadKiBPerTask: 8, frameBytes: 262144 } });
  assert.equal(large.status, 'blocked'); assert.equal(large.workload.blobCount, 3);
  assert.ok(large.failure.code); assert.deepEqual(validateRecord(large), []);
  assert.throws(() => sample({ status: 'pass', workload: { frameBytes: 262144 } }));
  set(r, 'workload.paddingBytes', 1); assert.ok(validateRecord(r).some(e => e.field === 'workload.paddingBytes'));
  assert.throws(() => sample({ workload: { frameBytes: 1 } }));
});

test('禁止虚构费用、费用分母关系、gas 别名与除零', () => {
  for (const field of ['blobFee', 'blobGasUsed', 'l1ExecutionFee', 'totalMeasuredCost', 'costPerFinalizedTask', 'teeExecutionCost', 'failedAttemptCost', 'effectiveGasPrice']) invalid(`cost.${field}`, 0);
  invalid('cost.feeStatus', 'measured'); invalid('cost.feeSource', 'sepolia');
  assert.throws(() => sample({ cost: { finalizedTasks: 2, acceptedTasks: 1 } }));
  assert.throws(() => sample({ cost: { submittedBatches: 2 } }));
  assert.throws(() => sample({ cost: { gasUsed: 10, l1ExecutionGas: 11 } }));
  const r = sample({ cost: { finalizedTasks: 0, acceptedTasks: 0, submittedBatches: 0, gasUsed: 21000, l1ExecutionGas: 21000 } });
  assert.equal(r.cost.costPerFinalizedTask, null); assert.deepEqual(validateRecord(r), []);
});

test('吞吐完整窗口、失败重试、分母秒数、费用分母一致与除零', () => {
  const rate = { value: 4, numerator: 4, denominator: 1, start: START, end: END, failure: 1, retry: 2 };
  const r = sample({ throughput: { acceptedThroughput: rate }, cost: { acceptedTasks: 4 } });
  assert.deepEqual(validateRecord(r), []);
  for (const [field, value] of [['value', 5], ['denominator', 1000], ['numerator', 9], ['failure', -1], ['retry', null], ['start', '2026-02-30T08:00:00.000Z']]) {
    const bad = structuredClone(r); set(bad, `throughput.acceptedThroughput.${field}`, value);
    assert.ok(validateRecord(bad).length);
  }
  const mismatch = structuredClone(r); mismatch.cost.acceptedTasks = 3;
  assert.ok(validateRecord(mismatch).some(e => e.field === 'cost.acceptedTasks'));
  const zero = sample({ throughput: { executionThroughput: { ...rate, value: null, denominator: 0, end: START } } });
  assert.deepEqual(validateRecord(zero), []); assert.ok(zero.notApplicableReason['throughput.executionThroughput.value']);
  assert.throws(() => sample({ throughput: { executionThroughput: { ...rate, denominator: 0, end: START } } }));
});

test('secret、Authorization、URL 凭据、私钥上下文、助记词与 dotenv 拒绝且错误不泄值', () => {
  const marker = 'DUMMY_SENSITIVE_VALUE_91';
  const inputs = [
    { secret: marker }, { SEPOLIA_PRIVATE_KEY: marker }, { api_key: marker }, { headers: { Authorization: marker } },
    { token: marker }, { nested: { password: marker } },
    { message: `Authorization: Bearer ${marker}` }, { message: `private-key: ${marker}` },
    { message: `https://example.invalid/?token=${marker}` }, { message: `https://name:${marker}@example.invalid/` },
    { message: `PUBLIC_NAME=${marker}\nANOTHER_NAME=anything` },
    { message: 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about' },
    JSON.parse('{"__proto__":{"polluted":true}}')
  ];
  for (const value of inputs) {
    assert.throws(() => assertPublic(value), error => !error.message.includes(marker));
    const r = sample(); r.extra = value;
    assert.ok(validateRecord(r).length); assert.ok(!JSON.stringify(validateRecord(r)).includes(marker));
  }
  for (const text of [`Authorization: ${marker}`, `private-key=${marker}`, `https://example.invalid/?token=${marker}`, `PASSWORD=${marker}`]) assert.ok(!redact(text).includes(marker));
  assert.equal(assertPublic({ gitHead: 'a'.repeat(40), configSha256: 'b'.repeat(64), transactionHash: '0x' + 'c'.repeat(64) }), true);
  assert.equal(redact('普通错误：已阻塞'), '普通错误：已阻塞');
  let accessed = false;
  const getter = { get data() { accessed = true; return marker; } };
  assert.throws(() => assertPublic(getter)); assert.equal(accessed, false);
});

test('路径注入、额外字段、空白原因与不一致身份拒绝', () => {
  for (const evidence of ['/tmp/result', '../secret', 'raw/../secret', 'raw\\result', 'C:/result', 'raw/%2e%2e/result', 'https://example.invalid/file', './result']) assert.throws(() => sample({ evidence: [evidence] }));
  assert.deepEqual(validateRecord(sample({ evidence: ['raw/result.json'] })), []);
  assert.throws(() => sample({ throughput: { injected: { note: '额外数据' } } }));
  assert.throws(() => sample({ workload: { extra: 1 } }));
  assert.throws(() => sample({ runId: 'another-run' }));
  assert.throws(() => sample({ notApplicableReason: { 'cost.blobFee': '   ' } }));
});

test('独立 Ajv 可编译两个严格 schema 并拒绝未知属性', () => {
  const ajv = new Ajv({ strict: false, allErrors: true });
  const check = ajv.compile(require('./schemas/experiment_record.schema.json'));
  const checkEvent = ajv.compile(require('./schemas/experiment_event.schema.json'));
  assert.equal(check(sample()), true);
  const r = sample(); r.workload.secretData = 'placeholder'; assert.equal(check(r), false);
  assert.equal(checkEvent({ schemaVersion: 'unknown' }), false);
});

test('记录三文件、状态计数、失败对象关联、UUID 事件与跨重启去重', t => {
  const { dir, file, recorder } = run(t);
  const pass = recorder.recordExperimentSample({ sampleId: 'pass-1' });
  const fail = recorder.recordFailure({ sampleId: 'fail-1', failure: { code: 'OFFLINE_ERROR', message: '离线测试失败\n保留换行语义' } });
  recorder.recordFailure({ sampleId: 'blocked-1', status: 'blocked', failure: { code: 'NOT_IMPLEMENTED', message: '尚未实现' } });
  recorder.recordExperimentSample({ status: 'skipped', statusReason: '不适用' });
  const event = recorder.recordExperimentEvent({ sampleId: pass.sampleId });
  recorder.recordExperimentEvent({ sampleId: pass.sampleId, eventType: 'checked' });
  assert.deepEqual(validateEvent(event), []);
  const summary = validateJsonl(file('experiment_records.jsonl'));
  assert.equal(summary.pass, true); assert.equal(summary.total, 4);
  assert.deepEqual(summary.counts, { pass: 1, fail: 1, blocked: 1, skipped: 1 });
  assert.equal(validateJsonl(file('experiment_events.jsonl'), { kind: 'event' }).total, 2);
  assert.equal(validateJsonl(file('failures.jsonl'), { kind: 'failure' }).total, 2);
  assert.deepEqual(JSON.parse(fs.readFileSync(file('failures.jsonl'), 'utf8').split('\n')[0]), fail);
  const restarted = createRecorder(dir);
  assert.throws(() => restarted.recordExperimentSample({ sampleId: pass.sampleId }), /重复/);
  assert.throws(() => restarted.recordExperimentEvent({ sampleId: pass.sampleId, eventId: event.eventId }), /重复/);
  assert.throws(() => restarted.recordFailure({ status: 'pass' }));
  assert.throws(() => restarted.recordExperimentEvent({ sampleId: 'missing' }));
  const child = spawnSync(process.execPath, ['-e', 'const r=require(process.argv[1]).createRecorder(process.argv[2]);try{r.recordExperimentSample({sampleId:"pass-1"});process.exitCode=2}catch(e){if(!e.message.includes("重复"))process.exitCode=3}', path.join(__dirname, 'experiment_record.js'), dir], { encoding: 'utf8' });
  assert.equal(child.status, 0, child.stderr);
});

test('JSONL 非法物理行号、字段、重复及事件多行独立解析', t => {
  const { file } = run(t);
  const r = sample({ sampleId: 'same' });
  const bad = structuredClone(r); bad.durationMs = -1;
  fs.writeFileSync(file('experiment_records.jsonl'), stableStringify(r) + '{bad\n' + stableStringify(bad) + stableStringify(r), 'utf8');
  const result = validateJsonl(file('experiment_records.jsonl'));
  assert.equal(result.pass, false); assert.equal(result.total, 4);
  assert.ok(result.errors.some(e => e.line === 2 && e.field === '$'));
  assert.ok(result.errors.some(e => e.line === 3 && e.field === 'durationMs'));
  assert.ok(result.errors.some(e => e.line === 4 && e.field === 'sampleId'));
  assert.equal(validateJsonl(file('experiment_records.jsonl'), { kind: 'unknown' }).pass, false);
  fs.writeFileSync(file('experiment_records.jsonl'), '\n');
  assert.equal(validateJsonl(file('experiment_records.jsonl')).errors[0].line, 1);
});

test('追加前校验无写入，历史污染/跨文件断裂/身份不符拒绝续写', t => {
  const { dir, file, recorder } = run(t);
  const before = fs.readFileSync(file('experiment_records.jsonl'), 'utf8');
  assert.throws(() => recorder.recordFailure({ failure: { code: 'ERR', message: 'Authorization: DUMMY_VALUE' } }));
  assert.equal(fs.readFileSync(file('experiment_records.jsonl'), 'utf8'), before);
  recorder.recordFailure({ failure: { code: 'ERR', message: '测试失败' } });
  fs.writeFileSync(file('failures.jsonl'), '', 'utf8');
  assert.throws(() => createRecorder(dir), /不一致/);
});

test('哈希不符、符号链接逃逸及锁定拒绝', t => {
  const { dir, recorder } = run(t);
  const outside = fs.mkdtempSync(path.join(os.tmpdir(), 'stageA-outside-'));
  t.after(() => fs.rmSync(outside, { recursive: true, force: true }));
  fs.symlinkSync(outside, path.join(dir, 'escape'));
  assert.throws(() => recorder.recordExperimentSample({ evidence: ['escape/result.json'] }), /符号链接/);
  fs.writeFileSync(path.join(dir, 'raw/.experiment_record.lock'), '');
  assert.throws(() => recorder.recordExperimentSample({}), /锁定/);
  fs.unlinkSync(path.join(dir, 'raw/.experiment_record.lock'));
  const { config } = fixture(); config.workload.batchSize = [32];
  fs.writeFileSync(path.join(dir, 'manifest/config.resolved.json'), stableStringify(config));
  assert.throws(() => createRecorder(dir), /哈希/);
});

test('事件日期、失败状态、UUID、重复 eventId 与失败 JSONL 状态', t => {
  const { file, recorder } = run(t);
  const s = recorder.recordExperimentSample({});
  const e = recorder.recordExperimentEvent({ sampleId: s.sampleId });
  assert.ok(validateEvent({ ...e, timestampUtc: '2026-02-30T08:00:00.000Z' }).some(x => x.field === 'timestampUtc'));
  assert.ok(validateEvent({ ...e, status: 'fail' }).length);
  assert.ok(validateEvent({ ...e, eventId: 'not-a-uuid' }).length);
  fs.appendFileSync(file('experiment_events.jsonl'), stableStringify(e));
  const checked = validateJsonl(file('experiment_events.jsonl'), { kind: 'event' });
  assert.ok(checked.errors.some(x => x.line === 2 && x.field === 'eventId'));
  fs.writeFileSync(file('failures.jsonl'), stableStringify(s));
  assert.equal(validateJsonl(file('failures.jsonl'), { kind: 'failure' }).pass, false);
  assert.match(crypto.randomUUID(), /^[0-9a-f-]{36}$/);
});
