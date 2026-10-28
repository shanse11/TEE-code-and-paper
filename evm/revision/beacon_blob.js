// Shared live-blob retrieval for the Sepolia experiment.
// Pinax returns Beacon API data as hex strings. Some clients return objects
// with blob / kzg_commitment / kzg_proof. Both are accepted.
// The beacon block id is a slot, not an execution-layer block number.

const SEPOLIA_BEACON_GENESIS = 1655733600;
const SECONDS_PER_SLOT = 12;

function beaconSlotFromTimestamp(timestamp) {
  const ts = Number(timestamp);
  const delta = ts - SEPOLIA_BEACON_GENESIS;
  if (delta < 0) throw new Error("timestamp is before Sepolia beacon genesis");
  return Math.floor(delta / SECONDS_PER_SLOT);
}

function blobHex(entry) {
  if (typeof entry === "string") return entry;
  if (entry && typeof entry.blob === "string") return entry.blob;
  throw new Error("beacon blob entry has neither a hex string nor a blob field");
}

async function beaconRootForSlot(slot) {
  const headerBase = (process.env.BEACON_HEADER_URL || "https://lodestar-sepolia.chainsafe.io").replace(/\/+$/, "");
  const resp = await fetch(`${headerBase}/eth/v1/beacon/headers/${slot}`, { headers: { Accept: "application/json" } });
  const txt = await resp.text();
  if (!resp.ok) throw new Error(`beacon header ${resp.status}: ${txt.slice(0, 200)}`);
  const json = JSON.parse(txt);
  const root = json.data && json.data.root;
  if (!root) throw new Error("beacon header response has no block root");
  return { root, headerBase, slot: Number(slot) };
}

async function fetchLiveBlob(beaconBase, blockId, versionedHash) {
  const beacon = beaconBase.replace(/\/+$/, "");
  const url = `${beacon}/eth/v1/beacon/blobs/${blockId}?versioned_hashes=${versionedHash}`;
  const resp = await fetch(url, { headers: { Accept: "application/json" } });
  const txt = await resp.text();
  if (!resp.ok) {
    const err = new Error(`beacon ${resp.status}: ${txt.slice(0, 200)}`);
    err.status = resp.status;
    throw err;
  }
  const json = JSON.parse(txt);
  const entry = json.data && json.data[0];
  if (entry == null) throw new Error("beacon returned no blob for the versioned hash");
  const hex = blobHex(entry);
  const blob = Buffer.from(hex.replace(/^0x/, ""), "hex");
  const commitmentHex = entry && typeof entry === "object" ? entry.kzg_commitment : null;
  const proofHex = entry && typeof entry === "object" ? entry.kzg_proof : null;
  return {
    blob,
    commitment: commitmentHex ? Buffer.from(commitmentHex.replace(/^0x/, ""), "hex") : null,
    proof: proofHex ? Buffer.from(proofHex.replace(/^0x/, ""), "hex") : null,
    commitmentSource: commitmentHex ? "beacon-response" : "recomputed-from-retrieved-bytes",
    index: entry && typeof entry === "object" ? entry.index : null,
  };
}

async function fetchBlobForPublish(beaconBase, slot, versionedHash) {
  try {
    const live = await fetchLiveBlob(beaconBase, slot, versionedHash);
    return { ...live, queriedBlockId: String(slot), querySource: "slot" };
  } catch (slotErr) {
    if (slotErr.status !== 404) throw slotErr;
    const header = await beaconRootForSlot(slot);
    const live = await fetchLiveBlob(beaconBase, header.root, versionedHash);
    return { ...live, queriedBlockId: header.root, querySource: "beacon-block-root", headerBase: header.headerBase, slot: header.slot };
  }
}

module.exports = { SEPOLIA_BEACON_GENESIS, beaconSlotFromTimestamp, beaconRootForSlot, fetchLiveBlob, fetchBlobForPublish };
