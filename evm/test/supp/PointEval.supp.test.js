// LOCAL Hardhat (cancun) EIP-4844 point-evaluation (0x0a) DA duty. NOT Sepolia.
const { expect } = require("chai"); const { ethers, network } = require("hardhat");
const fs = require("fs"); const path = require("path");
const D = path.join(__dirname, "../../../outputs/experiments_supp_20261030/B_point_eval");
const fx = JSON.parse(fs.readFileSync(path.join(D, "kzg_fixture.json")));
describe("SUPP-B local point-eval DA", () => {
  const out = { label: "LOCAL Hardhat EDR, hardfork per hardhat.config (cancun+), NOT Sepolia", fixture: fx };
  after(() => fs.writeFileSync(path.join(D, "raw_results.json"), JSON.stringify(out, null, 2)));
  it("raw precompile 0x0a accepts real KZG proof and rejects tampered y", async () => {
    const input = ethers.concat([fx.versionedHash, fx.z, fx.y, fx.commitment, fx.proof]);
    const ret = await ethers.provider.call({ to: "0x000000000000000000000000000000000000000a", data: input });
    out.rawPrecompileReturn = ret;
    out.rawPrecompileEstimateGas = (await ethers.provider.estimateGas({ to: "0x000000000000000000000000000000000000000a", data: input })).toString();
    let bad; try { await ethers.provider.call({ to: "0x000000000000000000000000000000000000000a", data: ethers.concat([fx.versionedHash, fx.z, ethers.ZeroHash, fx.commitment, fx.proof]) }); bad = "accepted"; } catch (e) { bad = "rejected"; }
    out.tamperedY = bad; expect(bad).to.equal("rejected");
    expect(BigInt("0x" + ret.slice(66))).to.equal(52435875175126190479447740508185965837690552500527637822603658699938581184513n);
  });
  it("bind -> fulfill(point-eval) and bind -> slash, gas", async () => {
    const [r] = await ethers.getSigners();
    const c = await (await ethers.getContractFactory("PointEvalDaDuty")).deploy();
    const bond = ethers.parseEther("0.01");
    const g = async (tx) => (await (await tx).wait()).gasUsed.toString();
    out.gas_bind = await g(c.bind(ethers.id("a"), fx.versionedHash, fx.z, 60, { value: bond }));
    let rej=false; try { await c.fulfill(ethers.id("a"), ethers.ZeroHash, fx.commitment, fx.proof); } catch (e) { rej=/point-eval/.test(e.message); } expect(rej).to.equal(true);
    out.gas_fulfill_pointEval = await g(c.fulfill(ethers.id("a"), fx.y, fx.commitment, fx.proof));
    out.claimable = ethers.formatEther(await c.claimable(r.address));
    await c.bind(ethers.id("b"), fx.versionedHash, fx.z, 60, { value: bond });
    await network.provider.send("evm_increaseTime", [61]); await network.provider.send("evm_mine");
    out.gas_slash = await g(c.slash(ethers.id("b")));
    out.totalBurned = ethers.formatEther(await c.totalBurned());
    out.fulfillRejectsWrongY = true;
  });
});
