#!/usr/bin/env node
// Two follow-up Sepolia checks:
// 1) On-chain rejection of a reused blob versioned hash, and of an already
//    anchored payloadHash carried by a different blob.
// 2) A BoundedTaskRollup task whose daRef is that versioned hash.
// The contract still does not evaluate blob bytes, and this does not create
// a slash loop between the anchor and the task.

const fs = require("fs");
const path = require("path");
const { ethers } = require("ethers");
const { requireRun, readState, preflightOrFail } = require("./revision_env.js");
const kzg = require("./kzg.js");
const codec = require("./blobcodec.js");

const run = requireRun();
const publish = readState("blob_publish");
preflightOrFail(publish && publish.anchorId != null, "missing confirmed blob_publish state");

const anchorAddr = process.env.BLOB_BATCH_ANCHOR_ADDRESS;
const provider = new ethers.JsonRpcProvider(process.env.SEPOLIA_RPC_URL);
const wallet = new ethers.Wallet(process.env.SEPOLIA_PRIVATE_KEY, provider);

const anchorIface = new ethers.Interface([
  "function anchorBlobBatch(bytes32 payloadHash, uint256 taskCount, uint256 blobIndex) returns (uint256)",
  "function getAnchor(uint256 id) view returns (tuple(bytes32 payloadHash, uint256 taskCount, bytes32 blobVersionedHash, uint64 blockNumber, address submitter))",
  "error BlobHashReused(bytes32 blobVersionedHash)",
  "error PayloadAlreadyAnchored(bytes32 payloadHash)",
  "error BlobhashEmpty()",
]);

function loadBlob(target) {
  const dir = path.join(run, "artifacts", "blob_offline", target);
  const meta = JSON.parse(fs.readFileSync(path.join(dir, "meta.json"), "utf8"));
  const blob = Buffer.from(fs.readFileSync(path.join(dir, "blob.hex"), "utf8"), "hex");
  const commitment = Buffer.from(fs.readFileSync(path.join(dir, "commitment.hex"), "utf8"), "hex");
  return { meta, blob, commitment };
}

function revertName(error) {
  const data = error?.data || error?.error?.data || error?.info?.error?.data;
  if (typeof data === "string" && data.startsWith("0x")) {
    try {
      const parsed = anchorIface.parseError(data);
      return parsed ? parsed.name : data.slice(0, 10);
    } catch (_e) {
      return data.slice(0, 10);
    }
  }
  const message = `${error?.shortMessage || ""} ${error?.message || ""}`;
  if (message.includes("BlobHashReused")) return "BlobHashReused";
  if (message.includes("PayloadAlreadyAnchored")) return "PayloadAlreadyAnchored";
  return null;
}

async function sendBlob(label, { blob, commitment, payloadHash, taskCount }) {
  const fee = await provider.getFeeData();
  const txReq = {
    type: 3,
    to: anchorAddr,
    data: anchorIface.encodeFunctionData("anchorBlobBatch", [payloadHash, BigInt(taskCount), 0n]),
    blobVersionedHashes: [kzg.versionedHash(commitment)],
    blobWrapperVersion: 1,
    blobs: [{ data: blob, commitment, proof: kzg.computeCellProof(blob) }],
    maxFeePerBlobGas: fee.maxFeePerBlobGas || ethers.parseUnits("10", "gwei"),
    maxFeePerGas: fee.maxFeePerGas,
    maxPriorityFeePerGas: fee.maxPriorityFeePerGas,
    gasLimit: 500000n,
  };
  let callRevert = null;
  try {
    await provider.call({ ...txReq, from: wallet.address });
  } catch (error) {
    callRevert = revertName(error);
  }
  if (callRevert == null) throw new Error(`${label}: eth_call did not revert`);
  let sent;
  try {
    sent = await wallet.sendTransaction(txReq);
  } catch (error) {
    const name = revertName(error);
    if (!name) throw error;
    return { label, callRevert, mined: false, revert: name, txHash: null, status: null, gasUsed: null };
  }
  const receipt = await provider.waitForTransaction(sent.hash, 1);
  return {
    label,
    callRevert,
    mined: true,
    revert: callRevert,
    txHash: receipt.hash,
    status: Number(receipt.status),
    blockNumber: Number(receipt.blockNumber),
    gasUsed: receipt.gasUsed.toString(),
    blobGasUsed: receipt.blobGasUsed ? receipt.blobGasUsed.toString() : null,
  };
}

async function main() {
  const network = await provider.getNetwork();
  if (network.chainId !== 11155111n) throw new Error(`unexpected chain ${network.chainId}`);
  const same = loadBlob("8_8KiB");
  const other = loadBlob("1_1KiB");
  if (same.meta.versionedHash.toLowerCase() !== publish.blobVersionedHashes[0].toLowerCase()) {
    throw new Error("offline 8_8KiB artifact does not match the published versioned hash");
  }

  const reused = await sendBlob("reuse-versioned-hash", {
    blob: same.blob,
    commitment: same.commitment,
    payloadHash: ethers.keccak256(ethers.toUtf8Bytes("different-payload-claim")),
    taskCount: same.meta.taskCount,
  });
  if (reused.callRevert !== "BlobHashReused" || reused.status !== 0) {
    throw new Error(`reuse case did not revert on-chain as BlobHashReused: ${JSON.stringify(reused)}`);
  }

  const duplicatePayload = await sendBlob("duplicate-payload-hash", {
    blob: other.blob,
    commitment: other.commitment,
    payloadHash: publish.payloadHash,
    taskCount: other.meta.taskCount,
  });
  if (duplicatePayload.callRevert !== "PayloadAlreadyAnchored" || duplicatePayload.status !== 0) {
    throw new Error(`duplicate payload case did not revert on-chain: ${JSON.stringify(duplicatePayload)}`);
  }

  const artifact = JSON.parse(fs.readFileSync(path.join(run, "artifacts/contracts/BoundedTaskRollup.sol/BoundedTaskRollup.json"), "utf8"));
  const bond = ethers.parseEther("0.001");
  const rollup = await new ethers.ContractFactory(artifact.abi, artifact.bytecode, wallet).deploy(bond, 3600, 60, 2);
  const deployTx = rollup.deploymentTransaction();
  const deployReceipt = await deployTx.wait();
  const rollupAddr = await rollup.getAddress();

  const decoded = codec.decodeFrame(codec.blobToFrame(same.blob));
  if (decoded.payloadHash.toLowerCase() !== publish.payloadHash.toLowerCase()) {
    throw new Error("decoded blob content hash does not match the anchored payloadHash");
  }
  const initial = ethers.keccak256(ethers.toUtf8Bytes("sepolia-link"));
  const steps = 4;
  const computed = await rollup.compute(initial, steps);
  const taskId = ethers.keccak256(ethers.toUtf8Bytes("sepolia-blob-link"));
  const input = {
    taskId,
    initial,
    steps,
    version: 1,
    output: computed.output,
    traceRoot: computed.root,
    dataHash: publish.payloadHash,
  };
  const digest = await rollup.taskDigest(input);
  const signature = await wallet.signMessage(ethers.getBytes(digest));
  const submitReceipt = await (await rollup.submit(input, signature, { value: bond })).wait();
  const bindReceipt = await (await rollup.bindDa(taskId, publish.blobVersionedHashes[0], { value: bond })).wait();
  const fulfillReceipt = await (await rollup.fulfillDa(taskId, decoded.content)).wait();
  const duty = await rollup.getDaDuty(taskId);
  const anchor = await new ethers.Contract(anchorAddr, anchorIface, provider).getAnchor(publish.anchorId);
  if (duty.daRef.toLowerCase() !== anchor.blobVersionedHash.toLowerCase()) {
    throw new Error("task daRef does not equal the anchored versioned hash");
  }
  if (!duty.fulfilled) throw new Error("DA disclosure was not fulfilled");

  const report = {
    schemaVersion: "hybrid-tee-rollup.sepolia-blob-followup.v1",
    anchor: anchorAddr,
    taskRollup: rollupAddr,
    published: {
      txHash: publish.txHash,
      anchorId: publish.anchorId,
      versionedHash: publish.blobVersionedHashes[0],
      payloadHash: publish.payloadHash,
    },
    rejections: [reused, duplicatePayload],
    link: {
      taskId,
      daRef: duty.daRef,
      dataHash: input.dataHash,
      fulfilled: duty.fulfilled,
      disclosedHash: duty.disclosedHash,
      anchorVersionedHash: anchor.blobVersionedHash,
      daRefEqualsVersionedHash: duty.daRef.toLowerCase() === anchor.blobVersionedHash.toLowerCase(),
      dataHashEqualsAnchoredPayloadHash: input.dataHash.toLowerCase() === anchor.payloadHash.toLowerCase(),
      deployTx: deployReceipt.hash,
      submitTx: submitReceipt.hash,
      bindTx: bindReceipt.hash,
      fulfillTx: fulfillReceipt.hash,
      limitation: "daRef records the versioned hash. The task contract does not read blob bytes or run the point-evaluation precompile. Fulfilling the disclosure only proves the payloadHash preimage was posted. This is not a slash loop.",
    },
  };
  const out = path.join(run, "followup.json");
  fs.writeFileSync(out, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({
    reused: { tx: reused.txHash, status: reused.status, revert: reused.callRevert, block: reused.blockNumber },
    duplicatePayload: { tx: duplicatePayload.txHash, status: duplicatePayload.status, revert: duplicatePayload.callRevert, block: duplicatePayload.blockNumber },
    rollup: rollupAddr,
    daRefEqualsVersionedHash: report.link.daRefEqualsVersionedHash,
    report: out,
  }, null, 2));
}

main().catch((error) => {
  console.error(error.shortMessage || error.message);
  if (error.error) console.error(error.error.shortMessage || error.error.message || error.error);
  process.exit(1);
});
