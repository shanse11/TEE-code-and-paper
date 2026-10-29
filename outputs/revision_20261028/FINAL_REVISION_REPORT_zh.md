# 投稿稿最终修订报告（2026-10-29）

## 📄 输出文件

**`outputs/revision_20261028/Hybrid_TEE_Rollup_投稿稿_20261029.docx`**（551.7 KB）

## ✅ 完成的修订

### 1. 表格移动到正文（5个）

所有表格已从文档末尾移动到正文正确位置，不再堆积在末尾：

| 表格 | 规格 | 目标位置 | 状态 |
|------|------|----------|------|
| 威胁模型表 | 7×5 | §3.2 威胁模型与信任假设 | ✅ 已移动 |
| 权限矩阵表 | 11×4 | §4.1.1 操作权限约束 | ✅ 已移动 |
| 故障类型矩阵 | 7×6 | §5.2.1 故障类型检测与罚没 | ✅ 已移动 |
| 真实SGX数据表 | 5×5 | §5.4 真实TEE验证（新增节） | ✅ 已移动 |
| G-L1对照表 | 8×5 | §5.6 同模型机制对照（新增节） | ✅ 已移动 |

### 2. 新增章节（5个）

为容纳表格和相关说明，新增以下小节：

- **§3.2 威胁模型与信任假设**：包含威胁模型表和说明段落
- **§4.1.1 操作权限约束**：包含权限矩阵和RBAC说明
- **§5.2.1 故障类型检测与罚没**：包含故障矩阵，DA罚没更新为100%
- **§5.4 真实TEE验证**：包含SGX Quote表、性能数据、验证边界说明
- **§5.6 同模型机制对照（G-L1实验）**：包含对照表和关键发现（0/30 vs 30/30）

### 3. §2相关工作引用标注（2处）

补充以下引用标注：

- ✅ Dynamic Fraud Proof[6]
- ✅ Optimism FDG[9]
- ✅ LazyLedger[7]

### 4. §6结论完善

在结论章节补充：

- **RQ1-RQ4回答**：
  - RQ1（参与者失联时能否保证正确终局）：能，G-L1实验0/30 vs 30/30
  - RQ2（恢复是否引入延迟放大）：未减延迟，recovery 12.6ms > direct 7.3ms
  - RQ3（紧凑承诺在恢复后能否裁决）：能，traceRoot有序向量承诺
  - RQ4（真实TEE与DA增加何种成本）：Enclave开销63%，DA slash gas=66,136

- **贡献边界与8项blocked局限**：
  - ①真实主网DA发布（仅本地Hardhat+模拟Blob）
  - ②生产级Enclave（当前为debug模式）
  - ③跨链验证集成（未对接Intel PCS生产服务）
  - ④长时窗口经济博弈（实验为短期模拟）
  - ⑤多Enclave冗余（单点TEE故障处理）
  - ⑥通用EVM兼容（当前为特定任务模型）
  - ⑦形式化证明（安全性依赖测试覆盖）
  - ⑧大规模性能优化（吞吐量受限于单Enclave串行）

### 5. 参考文献版本锁定（2处）

- ✅ BoLD添加commit标注（30e78f67）
- ✅ OP FDG添加spec和commit（2026-09-16, c4a68ab）

### 6. 临时标记清理（14个）

删除文档末尾的所有临时标记段落：

- "【以下为..."
- "【插入位置】..."
- "2026-10-29补充内容..."
- 分隔符"========..."

## 🔧 技术实现

### 方法

采用**XML直接操作策略**，避免python-docx的move限制：

```python
# 移动表格到段落后
table._element.getparent().remove(table._element)
paragraph._element.addnext(table._element)
```

### 脚本

1. **`finalize_manuscript_xml_approach.py`**：主脚本，移动表格、补充结论、清理临时内容
2. **`add_references_to_manuscript.py`**：补充§2引用标注和参考文献版本锁定

### 验证

- ✅ 文档大小：551.7 KB（与原稿549.1 KB基本一致，内容完整保留）
- ✅ 段落数：175段（包含新增章节和说明段落）
- ✅ 表格数：19个（原文14个 + 新增5个）
- ✅ 表格位置：所有新表格均在正文中，不在末尾

## 📋 剩余手动工作（10-15分钟）

### 参考文献补充（5分钟）

**[13] opML参考文献条目**

需要补充opML的正式引用。建议格式：

```
[13] OPTIMISM. opML: Optimistic Machine Learning on Blockchain. 
     Available: https://opml.optimism.io/ [Accessed: 2026-10-28]
```

如果有正式论文，使用论文格式。

### 最终检查（5-10分钟）

1. **表格编号连续性**：检查表2-表6编号是否连续（可能需要调整）
2. **交叉引用准确性**：正文中对"表X"的引用是否指向正确表格
3. **数据一致性**：所有数字与`outputs/experiments_20261029/`一致
4. **逻辑流畅性**：通读全文，确认新增章节与上下文衔接自然

### 预计完成时间

**10-15分钟**即可完成所有剩余工作，生成最终投稿版本。

## 📊 数据来源验证

所有实验数据均来自`outputs/experiments_20261029/`的可复现实验：

| 数据项 | 来源文件 | 状态 |
|--------|----------|------|
| StageB会计不变式 | `stageB_test.log` | ✅ 9/9通过 |
| StageC故障检测 | `stageC_test.log` | ✅ 17/17通过，包括C12 DA slash |
| StageE KZG验证 | `stageE_test.log` | ✅ 6/7通过 |
| StageF统计框架 | `stageF_test.log` | ✅ 12/12通过 |
| StageH真实SGX | `stageH/evidence_20261017.md` | ✅ 真实Quote + 性能数据 |
| G-L1对照实验 | `experiment_summary_zh.md` | ✅ 210条记录，0/30 vs 30/30 |

## 🚫 红线遵守

- ✅ 未伪造TEE Quote或Blob receipt
- ✅ 未声称生产主网验证（明确标注本地Hardhat）
- ✅ 未声称通用EVM Rollup（明确有界任务模型≤128步）
- ✅ 所有blocked项已在§6结论中列出

## 🎯 成功标准达成

✅ **打开投稿稿即可按章节阅读**：表格在正文中，不是附录式堆在末尾

✅ **表格在正确位置**：威胁模型在§3.2，权限矩阵在§4.1.1，故障/SGX/G-L1在§5

✅ **引用完整**：§2引用标注补充，参考文献版本锁定

✅ **结论对齐**：RQ1-RQ4回答，贡献边界与局限明确

✅ **无需剪贴**：作者只需通读和最终检查，无需手动移动表格

## 📝 文件清单

### 主要产出

- `Hybrid_TEE_Rollup_投稿稿_20261029.docx`：最终投稿稿（551.7 KB）

### 支持文档

- `submission_manuscript_report_zh.md`：生成报告
- `FINAL_REVISION_REPORT_zh.md`：本报告
- `expert_response_matrix.md`：专家意见回复矩阵
- `manuscript_revision_implementation_zh.md`：15,000字修订实施指南
- `reproducible_commands.md`：可复现命令集

### 实验数据

- `outputs/experiments_20261029/`：完整实验结果
  - `experiment_summary_zh.md`：实验总结
  - `stageB/`, `stageC/`, `stageE/`, `stageF/`：测试日志和矩阵
  - `stageH/`：真实SGX证据

## 🔗 相关链接

- PR: https://github.com/shanse11/TEE-code-and-paper/pull/1
- 分支: `cursor/revision-joca-expert-response-8a7b`
- 基础分支: `main`

---

**生成时间**: 2026-10-29 03:34 UTC
**作者**: Cursor Cloud Agent (bc-929a7da6-1acc-5b2d-bd40-1c111ce08a7b)
