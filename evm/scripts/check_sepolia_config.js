const hre = require("hardhat");
const { deploymentParams } = require("./deploy_helpers");

function hasUsableRpcUrl(value) {
  if (!value) {
    return false;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 && !trimmed.includes("YOUR_KEY");
}

function hasUsablePrivateKey(value) {
  if (!value) {
    return false;
  }
  const trimmed = value.trim();
  if (!trimmed || trimmed.includes("your_private_key")) {
    return false;
  }
  const normalized = trimmed.startsWith("0x") ? trimmed : `0x${trimmed}`;
  return /^0x[0-9a-fA-F]{64}$/.test(normalized);
}

async function main() {
  const rpc = process.env.SEPOLIA_RPC_URL || "";
  const privateKey = process.env.SEPOLIA_PRIVATE_KEY || "";
  const params = deploymentParams();
  const hasRpcUrl = hasUsableRpcUrl(rpc);
  const hasPrivateKey = hasUsablePrivateKey(privateKey);
  const report = {
    networkTarget: "sepolia",
    currentNetwork: hre.network.name,
    hasRpcUrl,
    hasPrivateKey,
    teeSignerAddress: process.env.TEE_SIGNER_ADDRESS || null,
    parameters: params,
  };
  console.log(JSON.stringify(report, null, 2));
  if (!hasRpcUrl || !hasPrivateKey) {
    console.log("Sepolia deployment is not ready: missing SEPOLIA_RPC_URL or SEPOLIA_PRIVATE_KEY.");
  } else {
    console.log("Sepolia deployment config looks ready.");
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
