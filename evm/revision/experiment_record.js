'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { TextDecoder } = require('node:util');
const Ajv = require('ajv');
const sampleSchema = require('./schemas/experiment_record.schema.json');
const eventSchema = require('./schemas/experiment_event.schema.json');
const ajv = new Ajv({ allErrors: true, strict: false, ownProperties: true });
const checkSample = ajv.compile(sampleSchema);
const checkEvent = ajv.compile(eventSchema);
const own = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key);
const SECRET_KEY = /(?:secret|password|passwd|authorization|credential|mnemonic|seedphrase|privatekey|apikey|accesstoken|authtoken|rpctoken|refreshtoken|bearertoken|dotenv)/i;
const normalizeKey = key => key.replace(/[^a-z0-9]/gi, '');
const TIMELINE = Object.keys(sampleSchema.properties.timeline.properties);
const COST = Object.keys(sampleSchema.properties.cost.properties).filter(k => !['feeStatus', 'feeSource'].includes(k));
const THROUGHPUT = Object.keys(sampleSchema.properties.throughput.properties);
const RATE_FIELDS = ['value', 'numerator', 'denominator', 'start', 'end', 'failure', 'retry'];

function unsafeText(text) {
  return /(?:authorization\s*[:=]|\bbearer\s+\S+|\bbasic\s+[A-Za-z0-9+/=]+|private[\s_-]*key\b|secret[\s_-]*(?:key|token)\b|(?:api[\s_-]*key|access[\s_-]*token|rpc[\s_-]*token|password|mnemonic|seed[\s_-]*phrase)\s*[:=]|-----BEGIN [^-]*PRIVATE KEY-----)/i.test(text)
    || /(?:^|[\r\n])\s*(?:export\s+)?[A-Z_][A-Z0-9_]*\s*=\s*\S/m.test(text)
    || /\b[a-z][a-z0-9+.-]*:\/\/[^\s]*[?#][^\s]+/i.test(text)
    || /\b[a-z][a-z0-9+.-]*:\/\/[^\s/]*@/i.test(text)
    || /(?:^|\s)(?:[a-z]+[ \t]+){11,23}[a-z]+(?:$|[\r\n])/.test(text)
    || /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(text);
}

function assertPublic(value) {
  const seen = new Set();
  function visit(item, depth) {
    if (depth > 60) throw new Error('公开数据嵌套过深');
    if (typeof item === 'string') {
      if (unsafeText(item)) throw new Error('公开数据含敏感内容');
      return;
    }
    if (item === null || typeof item === 'boolean') return;
    if (typeof item === 'number' && Number.isFinite(item)) return;
    if (typeof item !== 'object' || seen.has(item)) throw new Error('公开数据必须为无循环的 JSON');
    const prototype = Object.getPrototypeOf(item);
    if (!Array.isArray(item) && prototype !== Object.prototype && prototype !== null) throw new Error('公开数据仅允许普通 JSON 对象');
    seen.add(item);
    for (const key of Reflect.ownKeys(item)) {
      if (Array.isArray(item) && key === 'length') continue;
      if (typeof key !== 'string' || SECRET_KEY.test(normalizeKey(key)) || /^(?:token|seed|env)$/i.test(key)
          || ['__proto__', 'constructor', 'prototype'].includes(key) || unsafeText(key)) throw new Error('公开数据含禁止字段');
      const descriptor = Object.getOwnPropertyDescriptor(item, key);
      if (!descriptor.enumerable || !own(descriptor, 'value')) throw new Error('公开数据禁止访问器或隐藏字段');
      visit(descriptor.value, depth + 1);
    }
    if (Array.isArray(item) && Object.keys(item).length !== item.length) throw new Error('公开数据禁止稀疏或扩展数组');
    seen.delete(item);
  }
  visit(value, 0);
  return true;
}

function redact(text) {
  if (typeof text !== 'string') return '[REDACTED]';
  if (unsafeText(text) || SECRET_KEY.test(normalizeKey(text)) || /[?&](?:token|key|sig|auth)[^\s]*=/i.test(text)) return '[REDACTED]';
  return text;
}

function stableStringify(obj) {
  // 手工排序避免 JSON.stringify 对整数字符串键重新排序；保留原数组顺序。
  const seen = new Set();
  function encode(value) {
    if (value === null || typeof value === 'string' || typeof value === 'boolean') return JSON.stringify(value);
    if (typeof value === 'number' && Number.isFinite(value)) return JSON.stringify(value);
    if (!value || typeof value !== 'object' || seen.has(value)) throw new Error('无法序列化非 JSON 数据');
    if (!Array.isArray(value) && ![Object.prototype, null].includes(Object.getPrototypeOf(value))) throw new Error('无法序列化非普通对象');
    seen.add(value);
    const keys = Object.keys(value);
    for (const key of keys) if (!own(Object.getOwnPropertyDescriptor(value, key), 'value')) throw new Error('禁止序列化访问器');
    if (Array.isArray(value) && (keys.length !== value.length || keys.some((k, i) => k !== String(i)))) throw new Error('禁止序列化稀疏或扩展数组');
    const result = Array.isArray(value) ? `[${value.map(encode).join(',')}]` : `{${keys.sort().map(k => `${JSON.stringify(k)}:${encode(value[k])}`).join(',')}}`;
    seen.delete(value);
    return result;
  }
  return `${encode(obj)}\n`;
}

function sha256(bytes) {
  return crypto.createHash('sha256').update(bytes).digest('hex');
}

function isUtc(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(value)) return false;
  const ms = Date.parse(value);
  return Number.isFinite(ms) && new Date(ms).toISOString() === value;
}

function structural(value, check) {
  try { assertPublic(value); } catch { return [{ field: '$', message: '数据含禁止字段、敏感内容或非 JSON 类型' }]; }
  if (check(value)) return [];
  return check.errors.map(error => ({
    field: (error.instancePath || '').split('/').filter(Boolean).join('.') + (error.keyword === 'required' ? `${error.instancePath ? '.' : ''}${error.params.missingProperty}` : '') || '$',
    message: `字段不符合 schema（${error.keyword}）`
  }));
}

function validateRecord(record) {
  const errors = structural(record, checkSample);
  if (errors.length) return errors;
  const add = (field, message) => errors.push({ field, message });
  const w = record.workload;
  const c = record.cost;
  const reasons = record.notApplicableReason;
  function dates(obj, prefix) {
    for (const [key, value] of Object.entries(obj)) if (value !== null && !isUtc(value)) add(`${prefix}${key}`, '必须为真实有效的 UTC ISO 毫秒 Z 时间');
  }
  dates({ startedAtUtc: record.startedAtUtc, endedAtUtc: record.endedAtUtc }, '');
  dates(record.timeline, 'timeline.');
  const elapsed = Date.parse(record.endedAtUtc) - Date.parse(record.startedAtUtc);
  if (elapsed < 0) add('endedAtUtc', '结束时间不能早于开始时间');
  if (Math.abs(record.durationMs - elapsed) > 1) add('durationMs', '必须与起止时间差一致，容差 1ms');
  function equal(field, actual, expected) {
    if (!Number.isSafeInteger(expected) || actual !== expected) add(field, '派生关系不一致或超出安全整数范围');
  }
  equal('workload.taskCount', w.taskCount, w.batchSize);
  equal('workload.payloadBytesPerTask', w.payloadBytesPerTask, w.payloadKiBPerTask * 1024);
  equal('workload.batchPayloadBytes', w.batchPayloadBytes, w.batchSize * w.payloadBytesPerTask);
  if (w.actualInFlight !== null && w.actualInFlight > w.configuredConcurrency) add('workload.actualInFlight', '实际在途量不能超过配置并发');
  if (w.actualInFlight !== null && w.actualInFlight < w.configuredConcurrency && !record.statusReason && !record.failure) add('statusReason', '实际并发未达目标必须说明原因');
  const encodedFields = ['frameBytes', 'encodedBytes', 'blobCount', 'paddingBytes', 'fieldPaddingBytes'];
  if (encodedFields.some(k => w[k] !== null)) {
    for (const key of encodedFields) if (w[key] === null) add(`workload.${key}`, '编码测量必须完整记录');
    if (w.frameBytes !== null) {
      if (w.frameBytes < w.batchPayloadBytes) add('workload.frameBytes', '编码帧不能小于整批原始载荷');
      equal('workload.encodedBytes', w.encodedBytes, Math.ceil(w.frameBytes / 31) * 32);
      equal('workload.fieldPaddingBytes', w.fieldPaddingBytes, Math.ceil(w.frameBytes / 31) * 31 - w.frameBytes);
    }
    if (w.encodedBytes !== null) {
      equal('workload.blobCount', w.blobCount, Math.ceil(w.encodedBytes / w.blobBytes));
      equal('workload.paddingBytes', w.paddingBytes, Math.ceil(w.encodedBytes / w.blobBytes) * w.blobBytes - w.encodedBytes);
      if (w.blobCount > w.encoderMaxBlobs && record.status !== 'blocked') add('status', '当前单 Blob 编码器超容量必须 blocked');
    }
  }
  let previous = null;
  for (const key of TIMELINE) {
    const value = record.timeline[key];
    if (value !== null) {
      const current = Date.parse(value);
      if (current < Date.parse(record.startedAtUtc) || current > Date.parse(record.endedAtUtc)) add(`timeline.${key}`, '时间点必须位于样本窗口内');
      if (previous !== null && current < previous) add(`timeline.${key}`, '时间线不能逆序');
      previous = current;
    }
  }
  function missing(obj, prefix) {
    for (const [key, value] of Object.entries(obj)) {
      const field = `${prefix}${key}`;
      if (value === null && !own(reasons, field)) add(field, 'null 必须在 notApplicableReason 中逐项解释');
    }
  }
  missing(w, 'workload.'); missing(c, 'cost.'); missing(record.timeline, 'timeline.');
  for (const name of THROUGHPUT) {
    const rate = record.throughput[name];
    const prefix = `throughput.${name}.`;
    missing(rate, prefix);
    dates({ start: rate.start, end: rate.end }, prefix);
    if (RATE_FIELDS.some(k => rate[k] !== null)) {
      for (const key of RATE_FIELDS.filter(k => k !== 'value')) if (rate[key] === null) add(prefix + key, '吞吐测量必须完整记录分子、分母、窗口和失败重试次数');
      if (rate.start !== null && rate.end !== null && rate.denominator !== null) {
        const seconds = (Date.parse(rate.end) - Date.parse(rate.start)) / 1000;
        if (seconds < 0 || Math.abs(seconds - rate.denominator) > 0.001) add(prefix + 'denominator', '分母必须为窗口秒数，容差 1ms');
        if (Date.parse(rate.start) < Date.parse(record.startedAtUtc) || Date.parse(rate.end) > Date.parse(record.endedAtUtc)) add(prefix + 'start', '吞吐窗口必须位于样本窗口内');
      }
      if (rate.denominator === 0 && rate.value !== null) add(prefix + 'value', '分母为零时吞吐值必须 null 并解释');
      if (rate.denominator > 0 && (rate.value === null || Math.abs(rate.value - rate.numerator / rate.denominator) > 1e-9 * Math.max(1, rate.numerator / rate.denominator))) add(prefix + 'value', '吞吐必须等于分子除以分母');
      if (rate.numerator > w.taskCount) add(prefix + 'numerator', '当前样本任务计数不能超过一个逻辑批次的任务数');
    }
  }
  for (const [name, count] of [['acceptedThroughput', 'acceptedTasks'], ['finalizedThroughput', 'finalizedTasks']]) {
    const n = record.throughput[name].numerator;
    if (n !== null && c[count] !== null && n !== c[count]) add(`cost.${count}`, '费用分母必须与对应吞吐任务计数一致');
  }
  for (const key of ['acceptedTasks', 'finalizedTasks']) if (c[key] !== null && c[key] > w.taskCount) add(`cost.${key}`, '任务计数超过批次任务数');
  if (c.submittedBatches !== null && c.submittedBatches > 1) add('cost.submittedBatches', '每样本仅一个逻辑批次，重试不能重复计入分母');
  if (c.acceptedTasks !== null && c.finalizedTasks !== null && c.finalizedTasks > c.acceptedTasks) add('cost.finalizedTasks', '最终任务数不能超过已接受任务数');
  if (c.gasUsed !== null && c.l1ExecutionGas !== null && c.gasUsed !== c.l1ExecutionGas) add('cost.gasUsed', 'gasUsed 为 l1ExecutionGas 的兼容别名，值必须一致');
  for (const field of Object.keys(reasons)) {
    const value = field.split('.').reduce((obj, key) => obj && obj[key], record);
    if (value !== null) add(`notApplicableReason.${field}`, '缺失原因仅适用于 null 字段');
  }
  return errors;
}

function validateEvent(event) {
  const errors = structural(event, checkEvent);
  if (!errors.length && !isUtc(event.timestampUtc)) errors.push({ field: 'timestampUtc', message: '必须为真实有效的 UTC ISO 毫秒 Z 时间' });
  return errors;
}

function readUtf8(file) {
  return new TextDecoder('utf-8', { fatal: true }).decode(fs.readFileSync(file));
}

const sampleKey = sample => JSON.stringify([sample.runId, sample.experimentId, sample.sampleId]);
function scanJsonl(file, kind) {
  const result = { pass: true, total: 0, counts: { pass: 0, fail: 0, blocked: 0, skipped: 0 }, errors: [] };
  const records = [];
  const seen = new Set();
  if (!['sample', 'event', 'failure'].includes(kind)) return { ...result, pass: false, errors: [{ line: 0, field: 'kind', message: '未知 JSONL 类型' }], records };
  let text;
  try { text = readUtf8(file); } catch { return { ...result, pass: false, errors: [{ line: 0, field: '$', message: '无法读取 UTF-8 JSONL 文件' }], records }; }
  const lines = text.split('\n');
  if (lines.at(-1) === '') lines.pop();
  for (let i = 0; i < lines.length; i++) {
    const line = i + 1;
    result.total++;
    let record;
    try { record = JSON.parse(lines[i]); } catch {
      result.errors.push({ line, field: '$', message: '该行不是完整 JSON 对象' }); continue;
    }
    const errors = kind === 'event' ? validateEvent(record) : validateRecord(record);
    if (!errors.length && kind === 'failure' && !['fail', 'blocked'].includes(record.status)) errors.push({ field: 'status', message: 'failures 仅允许 fail/blocked 样本' });
    result.errors.push(...errors.map(error => ({ line, ...error })));
    if (errors.length) continue;
    const key = kind === 'event' ? record.eventId : sampleKey(record);
    if (seen.has(key)) result.errors.push({ line, field: kind === 'event' ? 'eventId' : 'sampleId', message: '重复记录身份' });
    seen.add(key);
    result.counts[record.status]++;
    records.push(record);
  }
  result.pass = result.errors.length === 0;
  return { ...result, records };
}

function validateJsonl(file, { kind = 'sample' } = {}) {
  const { records, ...result } = scanJsonl(file, kind);
  return result;
}

function enforce(errors) {
  if (errors.length) {
    const error = new Error('实验记录校验失败');
    error.errors = errors;
    throw error;
  }
}

function makeSample(config, manifest, partial = {}) {
  assertPublic(config); assertPublic(manifest); assertPublic(partial);
  const first = value => Array.isArray(value) ? value[0] : value;
  const cw = config.workload || {};
  const pw = partial.workload || {};
  const batchSize = pw.batchSize ?? first(cw.batchSize);
  const kib = pw.payloadKiBPerTask ?? first(cw.payloadKiBPerTask);
  const started = partial.startedAtUtc ?? new Date().toISOString();
  const ended = partial.endedAtUtc ?? started;
  const sample = {
    schemaVersion: 'hybrid-tee-rollup.sample.v1', runId: manifest.runId,
    experimentId: 'stageA-self-test', caseId: 'local-config-validation', sampleId: crypto.randomUUID(),
    status: 'pass', statusReason: null, startedAtUtc: started, endedAtUtc: ended,
    durationMs: Date.parse(ended) - Date.parse(started), gitHead: manifest.gitHead, configSha256: manifest.configSha256,
    chain: { ...config.chain }, backend: { ...config.backends },
    failure: null, evidence: [], ...partial,
    workload: {
      batchSize, taskCount: batchSize, dispatchGroupSize: null,
      payloadKiBPerTask: kib, payloadBytesPerTask: kib * 1024, batchPayloadBytes: batchSize * kib * 1024,
      frameBytes: null, encodedBytes: null, blobCount: null, blobBytes: 131072, paddingBytes: null, fieldPaddingBytes: null,
      encoderMaxBlobs: 1, stepCount: cw.stepCount ?? null,
      configuredConcurrency: first(cw.concurrency ?? cw.configuredConcurrency), actualInFlight: null,
      concurrencyUnit: cw.concurrencyUnit ?? 'inflight_batches', ...pw
    },
    timeline: { ...Object.fromEntries(TIMELINE.map(k => [k, null])), ...partial.timeline },
    cost: { ...Object.fromEntries(COST.map(k => [k, null])), feeStatus: 'not_measured', feeSource: 'local-gas-only', ...partial.cost },
    throughput: Object.fromEntries(THROUGHPUT.map(k => [k, { ...Object.fromEntries(RATE_FIELDS.map(f => [f, null])), ...partial.throughput?.[k] }])),
    notApplicableReason: { ...partial.notApplicableReason }
  };
  // 不丢弃未知吞吐字段，否则注入字段会被默认值合并掩盖。
  for (const key of Object.keys(partial.throughput || {})) if (!THROUGHPUT.includes(key)) sample.throughput[key] = partial.throughput[key];
  if (sample.workload.frameBytes !== null) {
    const w = sample.workload;
    const encoded = Math.ceil(w.frameBytes / 31) * 32;
    if (!own(pw, 'encodedBytes')) w.encodedBytes = encoded;
    if (!own(pw, 'blobCount')) w.blobCount = Math.ceil(encoded / 131072);
    if (!own(pw, 'paddingBytes')) w.paddingBytes = w.blobCount * 131072 - encoded;
    if (!own(pw, 'fieldPaddingBytes')) w.fieldPaddingBytes = Math.ceil(w.frameBytes / 31) * 31 - w.frameBytes;
    if (w.blobCount > 1 && !own(partial, 'status')) {
      sample.status = 'blocked'; sample.failure = { code: 'SINGLE_BLOB_CAPACITY_EXCEEDED', message: '当前实际编码器仅支持单 Blob；未执行超容量编码' };
    }
  }
  const fill = (obj, prefix) => {
    for (const [key, value] of Object.entries(obj)) if (value === null && !own(sample.notApplicableReason, prefix + key)) {
      sample.notApplicableReason[prefix + key] = prefix.startsWith('timeline.') ? '阶段 A 仅冻结定义；未测量此恢复或结算时间点' : prefix.startsWith('cost.') ? '本地仅允许 gas 计量；此费用或分母未测量' : '本样本未测量此字段';
    }
  };
  fill(sample.workload, 'workload.'); fill(sample.timeline, 'timeline.'); fill(sample.cost, 'cost.');
  for (const key of THROUGHPUT) fill(sample.throughput[key], `throughput.${key}.`);
  enforce(validateRecord(sample));
  for (const key of ['runId', 'gitHead', 'configSha256']) if (sample[key] !== manifest[key]) throw new Error('样本身份与 manifest 不一致');
  if (config.runId !== manifest.runId || stableStringify(sample.chain) !== stableStringify(config.chain) || stableStringify(sample.backend) !== stableStringify(config.backends)) throw new Error('样本链或后端身份与配置不一致');
  if (manifest.chain && stableStringify(manifest.chain) !== stableStringify(config.chain)) throw new Error('manifest 链与配置不一致');
  return sample;
}

function createRecorder(runDir) {
  if (typeof runDir !== 'string' || !path.isAbsolute(runDir)) throw new Error('runDir 必须为绝对路径');
  const root = fs.realpathSync(runDir);
  function safePath(relative) {
    const target = path.resolve(root, relative);
    if (!target.startsWith(root + path.sep)) throw new Error('记录路径必须位于 run 目录内');
    let current = root;
    for (const part of path.relative(root, target).split(path.sep)) {
      current = path.join(current, part);
      if (fs.existsSync(current) && fs.lstatSync(current).isSymbolicLink()) throw new Error('记录和证据路径禁止符号链接');
    }
    return target;
  }
  let manifest, config;
  try {
    manifest = JSON.parse(readUtf8(safePath('manifest/run_manifest.json')));
    config = JSON.parse(readUtf8(safePath('manifest/config.resolved.json')));
  } catch { throw new Error('无法读取 run manifest 或 resolved config'); }
  assertPublic(manifest); assertPublic(config);
  if (manifest.configSha256 !== sha256(stableStringify(config))) throw new Error('resolved config 哈希与 manifest 不一致');
  makeSample(config, manifest);
  const raw = safePath('raw');
  fs.mkdirSync(raw, { recursive: true });
  const files = { sample: 'raw/experiment_records.jsonl', event: 'raw/experiment_events.jsonl', failure: 'raw/failures.jsonl' };
  for (const name of Object.values(files)) fs.closeSync(fs.openSync(safePath(name), 'a'));
  const lockPath = safePath('raw/.experiment_record.lock');
  function identity(record) {
    for (const key of ['runId', 'gitHead', 'configSha256']) if (record[key] !== manifest[key]) throw new Error('已有记录身份与 manifest 不一致');
    if (stableStringify(record.chain) !== stableStringify(config.chain)) throw new Error('记录链与配置不一致');
    for (const evidence of record.evidence) safePath(evidence);
  }
  function load() {
    const state = {};
    for (const [kind, file] of Object.entries(files)) {
      const scanned = scanJsonl(safePath(file), kind);
      enforce(scanned.errors);
      state[kind] = scanned.records;
      for (const record of scanned.records) identity(record);
    }
    const samples = new Map(state.sample.map(s => [sampleKey(s), s]));
    const failures = new Map(state.failure.map(s => [sampleKey(s), s]));
    for (const sample of state.sample) if (['fail', 'blocked'].includes(sample.status) && stableStringify(failures.get(sampleKey(sample)) ?? null) !== stableStringify(sample)) throw new Error('失败样本与 failures 文件不一致');
    for (const failure of state.failure) if (stableStringify(samples.get(sampleKey(failure)) ?? null) !== stableStringify(failure)) throw new Error('failures 存在未关联的失败样本');
    for (const event of state.event) {
      const sample = samples.get(sampleKey(event));
      if (!sample || sample.caseId !== event.caseId) throw new Error('事件未关联已存在的样本');
    }
    return state;
  }
  function locked(action) {
    let lock;
    try { lock = fs.openSync(lockPath, 'wx', 0o600); } catch { throw new Error('记录器已锁定；拒绝并行写入或自动清除遗留锁'); }
    try { return action(); } finally { fs.closeSync(lock); fs.unlinkSync(lockPath); }
  }
  locked(load);
  function append(entries) {
    const opened = [];
    try {
      for (const [kind, value] of entries) {
        const fd = fs.openSync(safePath(files[kind]), 'r+');
        const size = fs.fstatSync(fd).size;
        opened.push({ fd, size });
        let separator = '';
        if (size) { const last = Buffer.alloc(1); fs.readSync(fd, last, 0, 1, size - 1); if (last[0] !== 10) separator = '\n'; }
        const bytes = Buffer.from(separator + stableStringify(value), 'utf8');
        let offset = 0;
        while (offset < bytes.length) offset += fs.writeSync(fd, bytes, offset, bytes.length - offset, size + offset);
        fs.fsyncSync(fd);
      }
    } catch {
      for (const { fd, size } of opened) fs.ftruncateSync(fd, size);
      throw new Error('记录追加失败；本次已打开文件恢复至追加前长度');
    } finally { for (const { fd } of opened) fs.closeSync(fd); }
  }
  function recordExperimentSample(partial = {}) {
    const sample = makeSample(config, manifest, partial);
    return locked(() => {
      const state = load(); identity(sample);
      if (state.sample.some(s => sampleKey(s) === sampleKey(sample))) throw new Error('重复 sampleId');
      const entries = [['sample', sample]];
      if (['fail', 'blocked'].includes(sample.status)) entries.push(['failure', sample]);
      append(entries);
      return sample;
    });
  }
  function recordFailure(partial = {}) {
    assertPublic(partial);
    if (partial.status !== undefined && !['fail', 'blocked'].includes(partial.status)) throw new Error('recordFailure 仅允许 fail/blocked');
    return recordExperimentSample({ ...partial, status: partial.status ?? 'fail' });
  }
  function recordExperimentEvent(partial = {}) {
    assertPublic(partial);
    return locked(() => {
      const state = load();
      const sample = state.sample.find(s => s.sampleId === partial.sampleId && s.experimentId === (partial.experimentId ?? 'stageA-self-test'));
      if (!sample) throw new Error('事件必须关联已存在的 sampleId');
      const event = {
        schemaVersion: 'hybrid-tee-rollup.event.v1', runId: manifest.runId, experimentId: sample.experimentId,
        caseId: sample.caseId, sampleId: sample.sampleId, eventId: crypto.randomUUID(), eventType: 'sample-recorded',
        timestampUtc: new Date().toISOString(), status: sample.status, gitHead: manifest.gitHead, configSha256: manifest.configSha256,
        chain: { ...sample.chain }, failure: sample.failure, message: '记录样本状态事件', evidence: [], ...partial
      };
      enforce(validateEvent(event)); identity(event);
      if (event.caseId !== sample.caseId) throw new Error('事件 caseId 与样本不一致');
      if (state.event.some(e => e.eventId === event.eventId)) throw new Error('重复 eventId');
      append([['event', event]]);
      return event;
    });
  }
  return { recordExperimentSample, recordExperimentEvent, recordFailure };
}

module.exports = { stableStringify, sha256, assertPublic, redact, validateRecord, validateEvent, validateJsonl, makeSample, createRecorder };
