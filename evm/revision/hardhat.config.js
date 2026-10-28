const path = require("path");
const { subtask } = require("hardhat/config");
const { TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD } = require("hardhat/builtin-tasks/task-names");
require("@nomicfoundation/hardhat-ethers");
const root = path.resolve(__dirname, "../..");
const run = process.env.REVISION_RUN;
if (!run || !path.isAbsolute(run)) throw new Error("REVISION_RUN must be an absolute, independent output directory");
subtask(TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD).setAction(async ({ solcVersion }) => {
  if (solcVersion !== "0.8.26") throw new Error("Unexpected compiler");
  return { compilerPath: require.resolve("solc/soljson.js"), isSolcJs: true, version: solcVersion, longVersion: require("solc").version() };
});
module.exports = {
  solidity: { version: "0.8.26", settings: { optimizer: { enabled: true, runs: 200 }, viaIR: true, evmVersion: "cancun" } },
  paths: { root: path.join(root, "evm"), sources: path.join(root, "evm/contracts"), tests: __dirname, artifacts: path.join(run, "artifacts"), cache: path.join(run, "cache") },
  networks: { hardhat: { accounts: { count: 40 }, chainId: 31337, hardfork: "cancun", blockGasLimit: 60000000, initialBaseFeePerGas: 1000000000 } },
  mocha: { timeout: 120000 }
};
