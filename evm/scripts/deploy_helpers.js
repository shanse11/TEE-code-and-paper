const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

function readUintEnv(name, fallback) {
  const raw = process.env[name];
  if (!raw) return fallback;
  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || parsed < 0) {
    throw new Error(`Invalid numeric env ${name}: ${raw}`);
  }
  return parsed;
}

function deploymentParams() {
  return {
    disputeWindowSeconds: readUintEnv("DISPUTE_WINDOW_SECONDS", 60),
    challengeTimeoutSeconds: readUintEnv("CHALLENGE_TIMEOUT_SECONDS", 2),
    maxBisectionRounds: readUintEnv("MAX_BISECTION_ROUNDS", 16),
  };
}

function usableAddress(value) {
  if (!value) {
    return null;
  }
  const trimmed = String(value).trim();
  if (!trimmed || trimmed.includes("your_tee_signer_address")) {
    return null;
  }
  return /^0x[0-9a-fA-F]{40}$/.test(trimmed) ? trimmed : null;
}

function deploymentOutputDir() {
  return path.resolve(__dirname, "../deployments");
}

function abiOutputDir(networkName) {
  return path.join(deploymentOutputDir(), `${networkName}_abis`);
}

function contractArtifact(contractName) {
  return hre.artifacts.readArtifactSync(contractName);
}

function exportAbisAndIndex(networkName, payload) {
  const outputDir = abiOutputDir(networkName);
  fs.mkdirSync(outputDir, { recursive: true });
  const contractEntries = Object.entries(payload.contracts);
  const abiIndex = {
    network: networkName,
    chainId: payload.chainId,
    exportedAtBlock: payload.deployedAtBlock,
    contracts: {},
  };

  for (const [key, address] of contractEntries) {
    let contractName;
    if (key === "verifier") contractName = "MockTEEVerifier";
    else if (key === "daRegistry") contractName = "MockDARegistry";
    else if (key === "rollup") contractName = "HybridTEERollup";
    else continue;

    const artifact = contractArtifact(contractName);
    const target = path.join(outputDir, `${contractName}.abi.json`);
    fs.writeFileSync(target, JSON.stringify(artifact.abi, null, 2), "utf8");
    abiIndex.contracts[contractName] = {
      alias: key,
      address,
      abiFile: target,
      sourceName: artifact.sourceName,
      contractName: artifact.contractName,
    };
  }

  const indexPath = path.join(outputDir, "address_index.json");
  fs.writeFileSync(indexPath, JSON.stringify(abiIndex, null, 2), "utf8");
  return { abiDir: outputDir, indexPath };
}

function recordDeployment(networkName, payload) {
  const outputDir = deploymentOutputDir();
  fs.mkdirSync(outputDir, { recursive: true });
  const target = path.join(outputDir, `${networkName}.json`);
  fs.writeFileSync(target, JSON.stringify(payload, null, 2), "utf8");
  return target;
}

async function deployAll(options = {}) {
  const [deployer, fallbackTeeSigner] = await hre.ethers.getSigners();
  const networkName = hre.network.name;
  const params = deploymentParams();

  const teeSignerAddress =
    usableAddress(options.teeSignerAddress) ||
    usableAddress(process.env.TEE_SIGNER_ADDRESS) ||
    fallbackTeeSigner?.address ||
    deployer.address;

  const verifierFactory = await hre.ethers.getContractFactory("MockTEEVerifier");
  const verifier = await verifierFactory.deploy(teeSignerAddress);
  await verifier.waitForDeployment();

  const daFactory = await hre.ethers.getContractFactory("MockDARegistry");
  const daRegistry = await daFactory.deploy();
  await daRegistry.waitForDeployment();

  const rollupFactory = await hre.ethers.getContractFactory("HybridTEERollup");
  const rollup = await rollupFactory.deploy(
    await verifier.getAddress(),
    await daRegistry.getAddress(),
    params.disputeWindowSeconds,
    params.challengeTimeoutSeconds,
    params.maxBisectionRounds
  );
  await rollup.waitForDeployment();

  const block = await hre.ethers.provider.getBlock("latest");
  const payload = {
    network: networkName,
    chainId: Number(hre.network.config.chainId || 0),
    deployedAtBlock: block?.number ?? null,
    deployedAtTimestamp: block?.timestamp ?? null,
    deployer: deployer.address,
    teeSignerAddress,
    parameters: params,
    contracts: {
      verifier: await verifier.getAddress(),
      daRegistry: await daRegistry.getAddress(),
      rollup: await rollup.getAddress(),
    },
    constructorArgs: {
      MockTEEVerifier: [teeSignerAddress],
      MockDARegistry: [],
      HybridTEERollup: [
        await verifier.getAddress(),
        await daRegistry.getAddress(),
        params.disputeWindowSeconds,
        params.challengeTimeoutSeconds,
        params.maxBisectionRounds,
      ],
    },
  };
  const outputPath = recordDeployment(networkName, payload);
  const exported = exportAbisAndIndex(networkName, payload);
  return { payload, outputPath, ...exported };
}

module.exports = {
  deployAll,
  deploymentParams,
  deploymentOutputDir,
  exportAbisAndIndex,
  usableAddress,
};
