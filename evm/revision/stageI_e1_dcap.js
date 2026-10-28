// E1: verify the real SGX quotes with Automata DCAP on Sepolia, then run the same quotes through
// AutomataQuoteVerifier and AttestedTaskRollup on a pinned Sepolia fork.
//
// Part A uses eth_call against the live Sepolia contract (no transaction is sent).
// Part B deploys the adapter and rollup on a local fork of the same block.
//
// Run:
//   cd evm; REVISION_RUN=<abs> SEPOLIA_FORK_URL=<rpc> SEPOLIA_FORK_BLOCK=<n> \
//     node node_modules/hardhat/internal/cli/cli.js run --config revision/hardhat.fork.config.js revision/stageI_e1_dcap.js

const fs = require("fs");
const path = require("path");
const assert = require("assert");
const hre = require("hardhat");
const { ethers } = hre;
const { STRICT_POLICY, MRENCLAVE } = require("./attested_common");

const REVISION_RUN = process.env.REVISION_RUN;
assert.ok(REVISION_RUN && path.isAbsolute(REVISION_RUN), "REVISION_RUN must be absolute");
const AUTOMATA = "0x27188ABA3a26CBb806eF4C67de9b05D7d792EC10";
const QUOTE_DIR = path.resolve(__dirname, "../../outputs/stageH_20261017T104800Z");
const TCB_NAMES = [
  "OK", "SW_HARDENING_NEEDED", "CONFIGURATION_AND_SW_HARDENING_NEEDED", "CONFIGURATION_NEEDED",
  "OUT_OF_DATE", "OUT_OF_DATE_CONFIGURATION_NEEDED", "REVOKED", "UNRECOGNIZED",
];
const ACTION_NAMES = ["REJECT", "LONG", "SHORT"];

function sha256(buf) {
  return require("crypto").createHash("sha256").update(buf).digest("hex");
}

function parseOutput(out) {
  const b = Buffer.from(out.slice(2), "hex");
  const body = b.subarray(11, 11 + 384);
  return {
    quoteVersion: b.readUInt16BE(0),
    quoteBodyType: b.readUInt16BE(2),
    tcbStatus: b[4],
    tcbStatusName: TCB_NAMES[b[4]] || "UNKNOWN",
    fmspc: "0x" + b.subarray(5, 11).toString("hex"),
    mrEnclave: "0x" + body.subarray(64, 96).toString("hex"),
    reportData32: "0x" + body.subarray(320, 352).toString("hex"),
    advisoryBytes: b.length - 11 - 384,
  };
}

function loadQuotes() {
  const names = ["quote_steps4.dat", "quote_steps128.dat", "quote_bound.dat", "quote_bad.dat"];
  const quotes = names.map((n) => ({ label: n, bytes: fs.readFileSync(path.join(QUOTE_DIR, n)) }));
  const tampered = Buffer.from(quotes[0].bytes);
  tampered[48 + 320] ^= 0x01; // flip one report_data bit; the QE signature no longer matches
  quotes.push({ label: "quote_steps4_tampered.dat", bytes: tampered });
  return quotes;
}

async function main() {
  const url = process.env.SEPOLIA_FORK_URL;
  const live = new ethers.JsonRpcProvider(url, 11155111, { staticNetwork: true });
  const forkBlock = Number(process.env.SEPOLIA_FORK_BLOCK);
  const iface = new ethers.Interface(["function verifyAndAttestOnChain(bytes) payable returns (bool,bytes)"]);
  const quotes = loadQuotes();

  const partA = [];
  for (const q of quotes) {
    const data = iface.encodeFunctionData("verifyAndAttestOnChain", [q.bytes]);
    const row = { quote: q.label, sha256: sha256(q.bytes), bytes: q.bytes.length };
    try {
      const raw = await live.call({ to: AUTOMATA, data, blockTag: forkBlock });
      const [ok, out] = iface.decodeFunctionResult("verifyAndAttestOnChain", raw);
      const gas = await live.estimateGas({ to: AUTOMATA, data, blockTag: forkBlock }).catch(() => null);
      row.ok = ok;
      row.estimateGas = gas ? gas.toString() : null;
      if (ok) Object.assign(row, parseOutput(out));
      else row.reason = ethers.toUtf8String(out);
    } catch (err) {
      row.ok = false;
      row.reverted = true;
      row.reason = err.shortMessage || "execution reverted";
    }
    partA.push(row);
    console.log("A", q.label, row.ok, row.tcbStatusName || row.reason, row.estimateGas || "");
  }

  const [deployer] = await ethers.getSigners();
  const Adapter = await ethers.getContractFactory("AutomataQuoteVerifier");
  const adapter = await Adapter.deploy(AUTOMATA);
  await adapter.waitForDeployment();
  const Rollup = await ethers.getContractFactory("AttestedTaskRollup");
  const policies = {
    strict: STRICT_POLICY,
    rejectStale: STRICT_POLICY.map((a, i) => (i >= 1 && i <= 7 ? 0 : a)),
  };
  const partB = [];
  const record = {
    schemaVersion: "hybrid-tee-rollup.stageI.e1.v1",
    network: "sepolia",
    chainId: 11155111,
    automata: AUTOMATA,
    automataRelease: "v1.1.0 AutomataDcapAttestationFee",
    forkBlock,
    rpcHost: new URL(url).host,
    partA_liveEthCall: partA,
    partB_forkRegisterInstance: partB,
    partB_forkDirectAutomata: null,
    notes: [
      "Part A is eth_call against the live Sepolia contract at forkBlock; nothing was broadcast.",
      "Part B runs on a local fork of the same block. gasUsed includes the adapter and the rollup.",
      "These quotes bind task digests, not instance keys, so the derived instance address is not a usable signing key.",
      "MRENCLAVE pinned to the hash-chain enclave 1967faaa...; quote_bound/quote_bad come from the sample enclave and therefore fail the MRENCLAVE check.",
    ],
  };
  const dest = path.join(REVISION_RUN, "e1_dcap.json");
  const flush = () => fs.writeFileSync(dest, JSON.stringify(record, null, 2));
  flush();

  const direct = await (await deployer.sendTransaction({
    to: AUTOMATA, data: iface.encodeFunctionData("verifyAndAttestOnChain", [quotes[0].bytes]), gasLimit: 15000000,
  })).wait();
  record.partB_forkDirectAutomata = { quote: quotes[0].label, gasUsed: direct.gasUsed.toString(), status: direct.status };
  flush();
  console.log("B direct automata", direct.gasUsed.toString());

  const plan = {
    strict: [quotes[0], quotes[4], quotes[2]],
    rejectStale: [quotes[0]],
  };
  for (const [policyName, policy] of Object.entries(policies)) {
    for (const mr of [{ name: "computeEnclave", value: MRENCLAVE }]) {
      const rollup = await Rollup.deploy(await adapter.getAddress(), mr.value, ethers.parseEther("1"), 600, 7 * 24 * 3600, 30 * 24 * 3600, false, policy);
      await rollup.waitForDeployment();
      for (const q of plan[policyName]) {
        const row = { policy: policyName, mrEnclavePinned: mr.name, quote: q.label };
        try {
          const rc = await (await rollup.connect(deployer).registerInstance(q.bytes, { gasLimit: 15000000 })).wait();
          const ev = rc.logs.map((l) => { try { return rollup.interface.parseLog(l); } catch { return null; } }).find((e) => e && e.name === "InstanceRegistered");
          row.outcome = "registered";
          row.instance = ev.args.instance;
          row.tcbStatus = Number(ev.args.tcbStatus);
          row.action = ACTION_NAMES[Number(ev.args.action)];
          row.gasUsed = rc.gasUsed.toString();
        } catch (err) {
          row.outcome = "reverted";
          row.reason = (err.shortMessage || err.message).split("\n")[0];
        }
        partB.push(row);
        flush();
        console.log("B", policyName, q.label, row.outcome, row.action || row.reason, row.tcbStatus, row.gasUsed || "");
      }
    }
  }

  flush();
  console.log("wrote", dest);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
