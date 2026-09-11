const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

function deploymentFileFor(networkName) {
  return path.resolve(__dirname, `../deployments/${networkName}.json`);
}

async function verifyOne(address, constructorArguments, contract) {
  try {
    await hre.run("verify:verify", {
      address,
      constructorArguments,
      contract,
    });
    return { ok: true, address, contract };
  } catch (error) {
    const message = String(error.message || error);
    if (message.includes("Already Verified") || message.includes("already verified")) {
      return { ok: true, address, contract, alreadyVerified: true };
    }
    return { ok: false, address, contract, error: message };
  }
}

async function main() {
  const networkName = hre.network.name;
  if (networkName !== "sepolia") {
    throw new Error(`Verification is intended for sepolia, got ${networkName}`);
  }
  if (!process.env.ETHERSCAN_API_KEY) {
    throw new Error("Missing ETHERSCAN_API_KEY");
  }

  const deploymentFile = deploymentFileFor(networkName);
  if (!fs.existsSync(deploymentFile)) {
    throw new Error(`Deployment file not found: ${deploymentFile}`);
  }
  const deployment = JSON.parse(fs.readFileSync(deploymentFile, "utf8"));
  const results = [];

  results.push(
    await verifyOne(
      deployment.contracts.verifier,
      deployment.constructorArgs.MockTEEVerifier,
      "contracts/MockTEEVerifier.sol:MockTEEVerifier"
    )
  );
  results.push(
    await verifyOne(
      deployment.contracts.daRegistry,
      deployment.constructorArgs.MockDARegistry,
      "contracts/MockDARegistry.sol:MockDARegistry"
    )
  );
  results.push(
    await verifyOne(
      deployment.contracts.rollup,
      deployment.constructorArgs.HybridTEERollup,
      "contracts/HybridTEERollup.sol:HybridTEERollup"
    )
  );

  console.log(JSON.stringify({ network: networkName, results }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
