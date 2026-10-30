const {ethers}=require('ethers');const fs=require('fs');
const p=new ethers.JsonRpcProvider(process.env.SEPOLIA_RPC_URL);
const A='0x27188ABA3a26CBb806eF4C67de9b05D7d792EC10';
const abi=['function verifyAndAttestOnChain(bytes) payable returns (bool,bytes)','function getBp() view returns (uint16)'];
(async()=>{const c=new ethers.Contract(A,abi,p);const q=fs.readFileSync('../outputs/experiments_supp_20261030/sgx_requote/instance_quote.dat');
console.log('qlen',q.length,'code',(await p.getCode(A)).length,'bp',await c.getBp().catch(e=>e.shortMessage));
const from=fs.readFileSync('/home/box/.secrets/sepolia/address.txt','utf8').trim();
console.log('bal',ethers.formatEther(await p.getBalance(from)),'gasPrice',(await p.getFeeData()).gasPrice);
try{const r=await c.verifyAndAttestOnChain.staticCall(q,{from});console.log('ok',r[0],r[1].length, r[0]?r[1].slice(0,80):Buffer.from(r[1].slice(2),'hex').toString());}catch(e){console.log('err',e.shortMessage)}
try{console.log('est',await c.verifyAndAttestOnChain.estimateGas(q,{from}))}catch(e){console.log('esterr',e.shortMessage)}
})();
