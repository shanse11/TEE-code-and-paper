// Stage I: AutomataQuoteVerifier output parsing against a mock entrypoint.
//
// The output bytes are built in the Automata v1.1.0 layout:
// quoteVersion(2) | quoteBodyType(2) | tcbStatus(1) | fmspc(6) | 384-byte SGX report body | advisories.

const assert = require("assert");
const { ethers } = require("hardhat");

function buildOutput({ tcbStatus = 5, debug = false, mrEnclave, reportData, advisories = true }) {
  const body = Buffer.alloc(384);
  body.writeUInt8(debug ? 0x07 : 0x05, 48);
  Buffer.from(mrEnclave.slice(2), "hex").copy(body, 64);
  Buffer.from(reportData.slice(2), "hex").copy(body, 320);
  const head = Buffer.concat([
    Buffer.from([0x00, 0x03, 0x00, 0x01, tcbStatus]),
    Buffer.from("00606a000000", "hex"),
  ]);
  const adv = advisories
    ? Buffer.from(ethers.AbiCoder.defaultAbiCoder().encode(["string[]"], [["INTEL-SA-00657"]]).slice(2), "hex")
    : Buffer.alloc(0);
  return "0x" + Buffer.concat([head, body, adv]).toString("hex");
}

describe("AutomataQuoteVerifier", function () {
  const MR = "0x1967faaa87ab6290f8a9955fc6808899c0be7047541ea4aab82209b3e40d6d37";
  const RD = "0x" + "ab".repeat(20) + "00".repeat(12);
  let mock, adapter;

  beforeEach(async function () {
    mock = await (await ethers.getContractFactory("AutomataMock_Test")).deploy();
    adapter = await (await ethers.getContractFactory("AutomataQuoteVerifier")).deploy(await mock.getAddress());
  });

  async function verify() {
    return adapter.verifyQuote.staticCall("0x1234");
  }

  it("V01 passes through TCB status, MRENCLAVE and report_data", async function () {
    await mock.set(true, buildOutput({ tcbStatus: 5, mrEnclave: MR, reportData: RD }), false);
    const [ok, status, mr, rd] = await verify();
    assert.equal(ok, true);
    assert.equal(Number(status), 5);
    assert.equal(mr, MR);
    assert.equal(rd, RD);
  });

  it("V02 output without advisories parses the same way", async function () {
    await mock.set(true, buildOutput({ tcbStatus: 0, mrEnclave: MR, reportData: RD, advisories: false }), false);
    const [ok, status] = await verify();
    assert.equal(ok, true);
    assert.equal(Number(status), 0);
  });

  it("V03 Automata success=false is a failed quote", async function () {
    await mock.set(false, ethers.toUtf8Bytes("TCBR"), false);
    const [ok, status] = await verify();
    assert.equal(ok, false);
    assert.equal(Number(status), 255);
  });

  it("V04 a reverting entrypoint is a failed quote, not a revert", async function () {
    await mock.set(true, "0x", true);
    const [ok] = await verify();
    assert.equal(ok, false);
  });

  it("V05 debug enclaves are rejected", async function () {
    await mock.set(true, buildOutput({ tcbStatus: 0, debug: true, mrEnclave: MR, reportData: RD }), false);
    const [ok] = await verify();
    assert.equal(ok, false);
  });

  it("V06 truncated output is a failed quote", async function () {
    await mock.set(true, "0x0003000105", false);
    const [ok] = await verify();
    assert.equal(ok, false);
  });
});
