# Sepolia Blob 实验

网络：Sepolia，chainId 11155111。发布账户 `0xdcC6310Ab8D4621626b945119c2784a1Ae582F10`。锚定合约 `BlobBatchAnchor`：`0x083e9280AC8b5933060C55Dd189A52A3981248c9`。

## 发布

成功交易 `0x3ad90ecfdf5930c1bf611223af76196e54fbc74af0f9c9924de9dc523681d340`，区块 11932953，信标 slot 11374267。锚点 id 为 1。批次是 8 个任务、每任务 8 KiB。

- versioned hash：`0x010a35506f6b45b2d022aac9ecca1c4e2631ca12d6b0c07f6cb3d195c3985493`
- payloadHash：`0xfceefa8dd818691b3ca45ed14cd3f0a076f1e773669773dda277384738015fa7`
- 执行 gas：692029，有效 gas 价格 16 wei，执行费 11072464 wei
- blob gas：131072，blob gas 价格 1 wei，blob 费 131072 wei

这是 Osaka 之后的 type-3 交易，sidecar 使用 wrapper version 1 和 128 条 cell proof。更早的一笔 `0x641a778678461adec091c361fd4a174b15ebf688b38bd6f1f508b334022cbd5d` 因为 gas 上限 300000 耗尽而回滚，没有写入锚点。

## 独立取回与核对

从 `https://sepolia.blobs.pinax.network` 按 slot 11374267 和 versioned hash 取回 131072 字节。取回的内容解码后 payloadHash 与任务数都和链上锚点一致。用取回字节重新计算的 KZG commitment 得到同一个 versioned hash，`kzgVerify=true`。

Pinax 这次没有返回 commitment 字段，commitment 是从取回的 Blob 字节重算的，不是从本地发布文件抄来的。

## 链上拒绝

两笔 type-3 交易都被打进区块，状态为失败，收款合约都是锚定合约。

| 场景 | 交易 | 区块 | 链上结果 |
| --- | --- | --- | --- |
| 同一 Blob、另一份 payloadHash | `0x1550b2348e4cb1137fb065fb694a6bfd5e92f48cef42f9a9683c20f7ba86ef30` | 11933019 | `BlobHashReused` |
| 另一份 Blob、已经锚定过的 payloadHash | `0x68bcc0ab27713d96824839ad383550c114d44666912eb133ccd2f383e3adce5e` | 11933020 | `PayloadAlreadyAnchored` |

合约比较的是已登记的 Blob 哈希和 payloadHash，并不读取 Blob 正文。一份全新的 Blob 配上一个从未登记的 payloadHash，即使正文对不上，链上也不会拒绝。

## 任务与 Blob 的对应

`BoundedTaskRollup` 部署在 `0xbda16351d1c7F88f85Aa3FD398b9b6dd136C5eaf`。任务 `0x0df33d783bfb6f353d73eb68d11a4001ae82730aa3b7926d76fdbd98a76c43c2` 的 `daRef` 和 `dataHash` 分别等于锚点 1 的 versioned hash 与 payloadHash。`bindDa` 交易是 `0xdfdd3bf6aa19963f668b66ce43e117589899533ec17873f928b1682c2a052e24`，披露原像的交易是 `0x350953b87cc2000c81eab395bde74786b21e33b82be5f0c392c989029d9f64ff`。任务合约没有调用点值预编译，也没有读取 Blob 字节。

## 没有形成罚没闭环

`BlobBatchAnchor` 没有 challenge 或 settle 入口，也没有和 `BoundedTaskRollup` 绑定。链上读回的锚点与离线派生值一致，但 `challengeSettle` 仍是 `NOT_IMPLEMENTED`，`closedLoopClaimed=false`。
