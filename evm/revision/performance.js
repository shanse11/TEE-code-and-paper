"use strict";
const fs = require("fs");
const path = require("path");
const assert = require("assert/strict");
const { performance } = require("perf_hooks");
const run = process.env.REVISION_RUN;
assert(run && path.isAbsolute(run), "REVISION_RUN must be absolute");
const read = p => JSON.parse(fs.readFileSync(path.join(run, p), "utf8"));
assert.equal(read("security/security_report.json").pass, true, "Security gate failed");
const random = read("security/random_report.json");
assert(random.pass && random.completed >= 1000, "Random security gate failed");
const { ethers, network } = require("hardhat");
const dir = path.join(run, "performance");
fs.mkdirSync(dir, { recursive: true });
const abi = ethers.AbiCoder.defaultAbiCoder();
const h = s => ethers.keccak256(ethers.toUtf8Bytes(s));
const samples = Number(process.env.PERF_SAMPLES || 5);
assert(samples >= 3, "At least 3 pilot samples per cell");
const BOND = 1000n;
function quantile(xs, q) { if (!xs.length) return null; const a = [...xs].sort((a,b)=>a-b), x=(a.length-1)*q, i=Math.floor(x); return a[i]+(a[Math.min(i+1,a.length-1)]-a[i])*(x-i); }
function stats(xs) { return { n: xs.length, p50: quantile(xs, .5), p95: quantile(xs, .95), min: xs.length ? Math.min(...xs) : null, max: xs.length ? Math.max(...xs) : null }; }
function compute(initial, steps) { const trace = [initial]; for (let i=0;i<steps;i++) trace.push(ethers.keccak256(abi.encode(["uint256","bytes32"],[i,trace[i]]))); return { trace, output:trace[steps], root:ethers.keccak256(abi.encode(["bytes32[]"],[trace])) }; }
function payload(bytes, seed) { const b=Buffer.alloc(bytes); const prefix=ethers.getBytes(h(seed)); for(let i=0;i<bytes;i++) b[i]=(prefix[i%32]+i*31)&255; return b; }
async function deploy(mr=1, timeout=120, window=3600) { const c=await (await ethers.getContractFactory("BoundedTaskRollup")).deploy(BOND,window,timeout,mr); await c.waitForDeployment(); return c; }
async function build(c, signer, seed, steps, data) {
  const initial=h(`initial:${seed}`), t=compute(initial,steps);
  const input=[h(`task:${seed}`), initial, steps, 1, t.output, t.root, ethers.keccak256(data)];
  const digest=ethers.keccak256(abi.encode(["bytes32","uint256","address","tuple(bytes32,bytes32,uint16,uint32,bytes32,bytes32,bytes32)"],[h("HYBRID_BOUNDED_TASK_V1"),31337,await c.getAddress(),input]));
  return {id:input[0], input, trace:t.trace, signature:await signer.signMessage(ethers.getBytes(digest))};
}
async function tx(op, fn) {
  const start=performance.now(); const r=await (await fn()).wait(); assert.equal(r.status,1);
  return {op,hash:r.hash,gas:Number(r.gasUsed),executionFeeWei:(r.gasUsed*r.gasPrice).toString(),wallMs:performance.now()-start,blockNumber:r.blockNumber,blockTimestamp:(await ethers.provider.getBlock(r.blockNumber)).timestamp,ok:true};
}
async function jump(seconds) { await network.provider.send("evm_increaseTime",[seconds]); await network.provider.send("evm_mine"); return {op:"timeJump",seconds,simulated:true}; }
async function main() {
  const secHash = require("crypto").createHash("sha256").update(fs.readFileSync(path.join(__dirname,"../contracts/BoundedTaskRollup.sol"))).digest("hex");
  const signers=await ethers.getSigners(); assert(signers.length>=33);
  const raw={meta:{evidenceLayer:"local_evm",node:process.version,ethers:ethers.version,chainId:31337,hardfork:"cancun",contractSha256:secHash,samplesPerCell:samples,startedAt:new Date().toISOString(),concurrency:[1,4,16],payloadKiB:[1,8,32],batchSize:[1,8,32]},notes:["Pilot measurements on in-process Hardhat automining; not public chain throughput or consensus finality.","payloadKiB is bytes per task. batchSize is a client scheduling group, NOT contract aggregation.","Matrix tasks store dataHash only. DA payload is not onchain in the matrix.","Separate calldata test publishes all batchSize*payloadKiB bytes through a contract hashing the bytes.","Recovery uses EVM time jumps, not real waiting. P95 with five samples is descriptive, not a reliable tail estimate.","No measured real blob fee; do not infer blob savings from calldata alone."],matrix:[],calldata:[],recovery:[],pass:false};
  try {
    const c=await deploy();
    for(const concurrency of [1,4,16]) for(const payloadKiB of [1,8,32]) for(const batchSize of [1,8,32]) {
      const cell={concurrency,payloadKiB,batchSize,samples:[]}; raw.matrix.push(cell);
      for(let sample=0;sample<samples;sample++) {
        const jobs=Array.from({length:batchSize},(_,i)=>i), transactions=[];
        let cursor=0; const start=performance.now();
        async function worker(w) {
          const sub=signers[1+w*2], challenger=signers[2+w*2];
          while(cursor<jobs.length) {
            const i=cursor++,seed=`c${concurrency}p${payloadKiB}b${batchSize}s${sample}i${i}`;
            const data=payload(payloadKiB*1024,seed), built=await build(c,sub,seed,4,data);
            transactions.push(await tx("submit",()=>c.connect(sub).submit(built.input,built.signature,{value:BOND})));
            transactions.push(await tx("challenge",()=>c.connect(challenger).openChallenge(built.id,{value:BOND})));
            transactions.push(await tx("adjudicate",()=>c.connect(sub).adjudicate(built.id)));
            const state=await c.getTask(built.id); assert.equal(state.phase,7n); assert.equal(state.verdict,0n);
          }
        }
        const effectiveConcurrency=Math.min(concurrency,batchSize);
        await Promise.all(Array.from({length:effectiveConcurrency},(_,w)=>worker(w)));
        assert.equal(transactions.length,batchSize*3);
        const wallMs=performance.now()-start;
        cell.samples.push({sample,taskCount:batchSize,effectiveConcurrency,wallMs,tasksPerSecond:batchSize/(wallMs/1000),transactions,failureRate:0});
      }
      console.log(`[performance] matrix c=${concurrency} p=${payloadKiB}KiB b=${batchSize} complete`);
    }
    for(const payloadKiB of [1,8,32]) for(const batchSize of [1,8,32]) {
      const anchor=await (await ethers.getContractFactory("BlobBatchAnchor")).deploy(); await anchor.waitForDeployment();
      const cell={payloadKiB,batchSize,totalPayloadBytes:payloadKiB*1024*batchSize,samples:[]}; raw.calldata.push(cell);
      for(let sample=0;sample<samples;sample++) {
        const data=payload(cell.totalPayloadBytes,`da:${payloadKiB}:${batchSize}:${sample}`);
        const item=await tx("anchorCalldataPayload",()=>anchor.anchorCalldataPayload(data,batchSize,{gasLimit:55000000}));
        const recorded=await anchor.getAnchor(sample+1); assert.equal(recorded.payloadHash,ethers.keccak256(data)); assert.equal(recorded.blobVersionedHash,ethers.ZeroHash);
        cell.samples.push({...item,sample,calldataBytes:ethers.getBytes(anchor.interface.encodeFunctionData("anchorCalldataPayload",[data,batchSize])).length});
      }
      console.log(`[performance] calldata ${cell.totalPayloadBytes} bytes complete`);
    }
    for(const maxRecoveries of [0,1,2]) for(const steps of [4,16,64,128]) for(const scenario of ["direct","timeout","recover","diagnostics"]) {
      const cell={maxRecoveries,steps,scenario,samples:[]}; raw.recovery.push(cell);
      for(let sample=0;sample<samples;sample++) {
        const r=await deploy(maxRecoveries,10,120), sub=signers[1], challenger=signers[2], observer=signers[3];
        const seed=`rec:${maxRecoveries}:${steps}:${scenario}:${sample}`;
        const b=await build(r,sub,seed,steps,payload(1024,seed)), operations=[]; const start=performance.now();
        operations.push(await tx("submit",()=>r.connect(sub).submit(b.input,b.signature,{value:BOND})));
        operations.push(await tx("challenge",()=>r.connect(challenger).openChallenge(b.id,{value:BOND})));
        const opened=await r.getTask(b.id), openedBlock=operations[1].blockTimestamp;
        if(scenario==="timeout") {
          operations.push(await jump(Number(opened.absoluteDeadline)-openedBlock));
          operations.push(await tx("terminate",()=>r.connect(observer).terminate(b.id)));
        } else if(scenario==="direct") operations.push(await tx("adjudicate",()=>r.connect(observer).adjudicate(b.id)));
        else if(scenario==="recover" && maxRecoveries===0) {
          operations.push(await jump(11)); operations.push(await tx("terminate",()=>r.connect(observer).terminate(b.id)));
        } else {
          operations.push(await tx("respond",()=>r.connect(sub).respond(b.id,b.trace)));
          if(scenario==="recover") for(let i=0;i<maxRecoveries;i++) { operations.push(await jump(11)); operations.push(await tx("recover",()=>r.connect(observer).recover(b.id))); }
          while(Number((await r.getTask(b.id)).phase)<5) operations.push(await tx("advance",()=>r.connect(observer).advance(b.id)));
          operations.push(await tx("replay",()=>r.connect(observer).replay(b.id)));
          operations.push(await tx("settle",()=>r.connect(observer).settle(b.id)));
        }
        const final=await r.getTask(b.id); assert.equal(final.phase,7n); assert.equal(final.verdict,0n); assert.equal(final.absoluteDeadline,opened.absoluteDeadline);
        assert.equal(await r.claimable(await sub.getAddress()),2n*BOND);
        const finish=(await ethers.provider.getBlock("latest")).timestamp;
        cell.samples.push({sample,wallMs:performance.now()-start,chainSecondsFromChallenge:finish-openedBlock,absoluteBoundSeconds:Number(opened.absoluteDeadline)-openedBlock,recoveries:Number(final.recoveries),totalGas:operations.reduce((s,t)=>s+(t.gas||0),0),transactions:operations.filter(t=>t.gas).length,operations,failureRate:0});
      }
    }
    raw.pass=true;
  } finally {
    raw.meta.finishedAt=new Date().toISOString(); fs.writeFileSync(path.join(dir,"raw.json"),JSON.stringify(raw,null,2));
    const summary={meta:raw.meta,pass:raw.pass,notes:raw.notes,matrix:raw.matrix.map(c=>({...Object.fromEntries(Object.entries(c).filter(([k])=>k!=="samples")),samples:c.samples.length,wallMs:stats(c.samples.map(s=>s.wallMs)),tasksPerSecond:stats(c.samples.map(s=>s.tasksPerSecond)),failureRate:0,gas:Object.fromEntries(["submit","challenge","adjudicate"].map(op=>[op,stats(c.samples.flatMap(s=>s.transactions.filter(t=>t.op===op).map(t=>t.gas)))]))})),calldata:raw.calldata.map(c=>({payloadKiB:c.payloadKiB,batchSize:c.batchSize,totalPayloadBytes:c.totalPayloadBytes,gas:stats(c.samples.map(s=>s.gas)),wallMs:stats(c.samples.map(s=>s.wallMs)),failureRate:0})),recovery:raw.recovery.map(c=>({maxRecoveries:c.maxRecoveries,steps:c.steps,scenario:c.scenario,gas:stats(c.samples.map(s=>s.totalGas)),wallMs:stats(c.samples.map(s=>s.wallMs)),chainSeconds:stats(c.samples.map(s=>s.chainSecondsFromChallenge)),transactions:stats(c.samples.map(s=>s.transactions)),failureRate:0}))};
    fs.writeFileSync(path.join(dir,"summary.json"),JSON.stringify(summary,null,2));
  }
  console.log(`[performance] passed ${raw.matrix.length} matrix cells, ${raw.calldata.length} calldata cells, ${raw.recovery.length} recovery cells`);
}
main().catch(e=>{console.error(e);process.exitCode=1;});
