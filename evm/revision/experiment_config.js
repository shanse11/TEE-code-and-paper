'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { assertPublic, stableStringify, sha256 } = require('./experiment_record');

const SCHEMA_VERSION = 'hybrid-tee-rollup.stageA.v1';
const ROOT = path.resolve(__dirname, '..', '..');
const DEFAULT_CONFIG = path.join(__dirname, 'config', 'stageA.local.json');
const PLACEHOLDER = /<[^>]+>/;
const POSITIVE = value => Number.isSafeInteger(value) && value > 0;
const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

function readJson(file) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch (error) {
    throw new Error(`无法读取配置 JSON：${path.basename(file)}`);
  }
}

function resolveConfigPath(input) {
  const candidate = input || DEFAULT_CONFIG;
  const absolute = path.isAbsolute(candidate) ? candidate : path.resolve(ROOT, candidate);
  if (!fs.existsSync(absolute) || !fs.statSync(absolute).isFile()) throw new Error('配置文件不存在');
  return absolute;
}

function hasPlaceholder(value) {
  if (typeof value === 'string') return PLACEHOLDER.test(value);
  if (Array.isArray(value)) return value.some(hasPlaceholder);
  return value && typeof value === 'object' && Object.values(value).some(hasPlaceholder);
}

function configPathForEvidence(absolute) {
  const relative = path.relative(ROOT, absolute).split(path.sep).join('/');
  return relative && !relative.startsWith('../') ? relative : absolute;
}

function staticBuildConfig() {
  const file = path.join(__dirname, 'hardhat.config.js');
  const text = fs.readFileSync(file, 'utf8');
  const version = text.match(/version:\s*["']([^"']+)["']/)?.[1];
  const runs = Number(text.match(/runs:\s*(\d+)/)?.[1]);
  const accounts = Number(text.match(/accounts:\s*\{\s*count:\s*(\d+)/)?.[1]);
  const chainId = Number(text.match(/chainId:\s*(\d+)/)?.[1]);
  const hardfork = text.match(/hardfork:\s*["']([^"']+)["']/)?.[1];
  if (version !== '0.8.26' || !text.includes('enabled: true') || runs !== 200 || !text.includes('viaIR: true') || hardfork !== 'cancun' || accounts !== 40 || chainId !== 31337) {
    throw new Error('无法从 hardhat.config.js 静态确认阶段 A 编译或链配置');
  }
  return {
    configPath: 'evm/revision/hardhat.config.js', artifactRoot: 'artifacts', cacheRoot: 'cache',
    solidity: version, optimizer: { enabled: true, runs }, viaIR: true, evmVersion: 'cancun', hardhatAccounts: { count: accounts }
  };
}

function normalizeLegacy(config, errors) {
  const workload = config.workload || {};
  if (own(workload, 'payloadKiB')) {
    if (own(workload, 'payloadKiBPerTask')) errors.push({ field: 'workload', message: '不能同时设置 payloadKiB 与 payloadKiBPerTask' });
    else if (workload.payloadScope === 'per-task' || workload.legacyPayloadSemantics === 'per-task') {
      workload.payloadKiBPerTask = Array.isArray(workload.payloadKiB) ? workload.payloadKiB : [workload.payloadKiB];
      workload.legacyPayloadKiB = workload.payloadKiB;
      delete workload.payloadKiB;
    } else errors.push({ field: 'workload.payloadKiB', message: '旧 payloadKiB 必须显式声明 payloadScope=per-task 或 legacyPayloadSemantics=per-task' });
  }
}

function validateConfig(input, { configPath } = {}) {
  let config;
  try { config = structuredClone(input); assertPublic(config); } catch { return { ok: false, status: 'fail', errors: [{ field: '$', message: '配置必须是公开、无敏感字段的 JSON 数据' }] }; }
  const errors = [];
  if (hasPlaceholder(config)) errors.push({ field: '$', message: '配置不能包含尖括号占位符' });
  normalizeLegacy(config, errors);
  if (config.schemaVersion !== SCHEMA_VERSION) errors.push({ field: 'schemaVersion', message: `必须为 ${SCHEMA_VERSION}` });
  if (typeof config.runId !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$/.test(config.runId)) errors.push({ field: 'runId', message: '必须是安全的非空运行标识' });
  const chain = config.chain || {};
  for (const [key, expected] of Object.entries({ backend: 'hardhat', network: 'hardhat-local', chainId: 31337, hardfork: 'cancun', rpcMode: 'in-process', finalityDefinition: 'local-automining-no-consensus-finality' })) {
    if (chain[key] !== expected) errors.push({ field: `chain.${key}`, message: `必须为 ${JSON.stringify(expected)}` });
  }
  const build = config.build || {};
  if (build.solidity !== '0.8.26' || build.viaIR !== true || build.evmVersion !== 'cancun' || build.optimizer?.enabled !== true || build.optimizer?.runs !== 200 || build.hardhatAccounts?.count !== 40) errors.push({ field: 'build', message: '必须匹配静态确认的 Hardhat 编译与账户配置' });
  const workload = config.workload || {};
  for (const key of ['batchSize', 'payloadKiBPerTask', 'concurrency']) {
    if (!Array.isArray(workload[key]) || !workload[key].length || workload[key].some(value => !POSITIVE(value))) errors.push({ field: `workload.${key}`, message: '必须是非空正整数数组' });
  }
  if (workload.taskCount !== null && !POSITIVE(workload.taskCount)) errors.push({ field: 'workload.taskCount', message: '必须为 null 或正整数' });
  if (workload.dispatchGroupSize !== null && !POSITIVE(workload.dispatchGroupSize)) errors.push({ field: 'workload.dispatchGroupSize', message: '必须为 null 或正整数' });
  if (workload.concurrencyUnit !== 'inflight_batches') errors.push({ field: 'workload.concurrencyUnit', message: '必须为 inflight_batches' });
  if (typeof workload.encodingVersion !== 'string' || !workload.encodingVersion || PLACEHOLDER.test(workload.encodingVersion)) errors.push({ field: 'workload.encodingVersion', message: '必须为明确的编码版本' });
  const backends = config.backends || {};
  for (const [key, expected] of Object.entries({ tee: 'simulated-only', da: 'local-mock-or-offline-only', blobMode: 'offline-only' })) {
    if (backends[key] !== expected && !['public', 'remote', 'sepolia'].includes(backends[key])) errors.push({ field: `backends.${key}`, message: '后端值无效' });
  }
  const metrics = config.metrics || {};
  if (metrics.throughputUnit !== 'finalized_tasks_per_second' || metrics.throughputNumerator !== 'finalizedTasks' || metrics.throughputDenominator !== 'measurementWindowSeconds' || metrics.costPrimaryDenominator !== 'finalizedTask' || metrics.includeFailedAttempts !== true) errors.push({ field: 'metrics', message: '吞吐量和费用口径不完整或不符合阶段 A 固定定义' });
  if (!errors.length) {
    const actual = staticBuildConfig();
    if (build.solidity !== actual.solidity || build.optimizer.runs !== actual.optimizer.runs || build.hardhatAccounts.count !== actual.hardhatAccounts.count) errors.push({ field: 'build', message: '配置与 hardhat.config.js 静态解析结果不一致' });
  }
  const publicBackend = Object.entries(backends).find(([key, value]) => ['public', 'remote', 'sepolia'].includes(value));
  const blocked = !errors.length && publicBackend && !(config.resources && config.resources[publicBackend[0]]);
  return {
    ok: errors.length === 0, status: errors.length ? 'fail' : (blocked ? 'blocked' : 'pass'), errors,
    blockedReason: blocked ? `公共后端 ${publicBackend[0]} 未提供公开资源描述；阶段 A 不联网。` : null,
    config: errors.length ? null : config,
    configPath: configPath ? configPathForEvidence(configPath) : null
  };
}

function loadConfig(input) {
  const absolute = resolveConfigPath(input);
  const result = validateConfig(readJson(absolute), { configPath: absolute });
  if (!result.ok) {
    const error = new Error('阶段 A 配置校验失败');
    error.validation = result;
    throw error;
  }
  return { ...result, absolutePath: absolute, evidencePath: configPathForEvidence(absolute), configSha256: sha256(stableStringify(result.config)) };
}

module.exports = { SCHEMA_VERSION, ROOT, DEFAULT_CONFIG, resolveConfigPath, staticBuildConfig, validateConfig, loadConfig };
