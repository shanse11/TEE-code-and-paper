require("dotenv").config();
require("@nomicfoundation/hardhat-ethers");
require("@nomicfoundation/hardhat-verify");

const sepoliaRpcUrl = process.env.SEPOLIA_RPC_URL || "";
const sepoliaPrivateKey = process.env.SEPOLIA_PRIVATE_KEY || "";
const etherscanApiKey = process.env.ETHERSCAN_API_KEY || "";

function normalizePrivateKey(value) {
  if (!value) {
    return "";
  }
  const trimmed = value.trim();
  if (!trimmed || trimmed.includes("your_private_key")) {
    return "";
  }
  const normalized = trimmed.startsWith("0x") ? trimmed : `0x${trimmed}`;
  return /^0x[0-9a-fA-F]{64}$/.test(normalized) ? normalized : "";
}

const normalizedSepoliaPrivateKey = normalizePrivateKey(sepoliaPrivateKey);
const sepoliaAccounts = normalizedSepoliaPrivateKey ? [normalizedSepoliaPrivateKey] : [];

module.exports = {
  solidity: {
    version: "0.8.24",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts",
  },
  networks: {
    hardhat: {
      chainId: 31337,
    },
    sepolia: {
      url: sepoliaRpcUrl,
      chainId: 11155111,
      accounts: sepoliaAccounts,
    },
  },
  etherscan: {
    apiKey: {
      sepolia: etherscanApiKey,
    },
  },
};
