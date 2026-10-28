// Sepolia fork for E1. Reads the public RPC from SEPOLIA_FORK_URL; nothing is broadcast.
const base = require("./hardhat.config.js");

const url = process.env.SEPOLIA_FORK_URL;
if (!url) throw new Error("SEPOLIA_FORK_URL must point to a Sepolia RPC");
const blockNumber = process.env.SEPOLIA_FORK_BLOCK ? Number(process.env.SEPOLIA_FORK_BLOCK) : undefined;

module.exports = {
  ...base,
  networks: {
    hardhat: {
      ...base.networks.hardhat,
      chainId: 11155111,
      hardfork: "cancun",
      // Sepolia exposes the P-256 precompile at 0x100, which Automata uses for quote signatures.
      enableRip7212: true,
      forking: { url, ...(blockNumber ? { blockNumber } : {}) },
      chains: { 11155111: { hardforkHistory: { cancun: 0 } } },
    },
  },
  mocha: { timeout: 600000 },
};
