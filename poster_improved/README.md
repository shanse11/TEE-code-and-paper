# NDBC 2026 P00145 海报交付与重新生成

## 使用哪些文件

- `NDBC2026_P00145_Poster_Final_Print.pdf`：最终印刷文件，847 × 1195 mm，A0 裁切 841 × 1189 mm，四边3 mm出血，约0.30 MB。仅需提交这份 PDF。
- `NDBC2026_P00145_Poster_Preview.png`：5002 × 7058 像素屏幕预览，约150 DPI；不要以预览 PNG 替代矢量 PDF 打印。
- `Poster_Improvement_Report.md`：P0/P1/P2 审查、实际改动、论文交叉核查、数值冲突、印前结果与人工确认事项。
- `source/build_poster.py`：独立、可编辑的矢量设计源。所有图形、架构、状态机、公式由代码绘制，无外部位图或 SVG 依赖。
- `source/config.json`：题目、作者、单位、会议、编号、日期与字体路径。
- `source/data/`：既有原始 CSV / JSON 数据快照。3200 行成本、600 行挑战、800 行故障、3 行 EVM gas 与部署/地址记录。
- `source/validate_poster.py`：重算数据、检查尺寸/字体/边距/重叠与原文件哈希。
- `source/render_preview.sh`：Poppler 高清渲染。
- `qa/`：数值冲突、原文件哈希、印刷检查、迭代版本与原新版对比。

## macOS 安装依赖

需要 Python 3.10 或更新版本，以及 Poppler。若尚未安装 Homebrew，请按 Homebrew 官方方式安装；下面命令假定 brew 已可用。

在本目录执行：

```zsh
brew install python poppler
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r source/requirements.txt
```

构建需要 macOS 自带的 STHeiti 字体集合和 Arial / Times New Roman 字体。默认路径在 `source/config.json` 中。生成后字体已经嵌入 PDF，阅读/打印无需接收方安装这些字体。

如果本机没有对应字体，请将 config 中路径改为本机已安装、允许嵌入的 TrueType 中文与西文字体；中文字体若为独立 TTF，设 `chinese_subfont_index` 为0。不要因字体文件名相似就假定其字符支持或字重相同。字体替换可能改变文字宽度，必须重新渲染检查。

## 重新生成

```zsh
python source/build_poster.py --revision 8
zsh source/render_preview.sh
python source/validate_poster.py
```

`--revision` 为保存迭代检查文件的编号；在已交付的最后编号7之后继续编号。代码会重新生成本交付目录中的 Final_Print 与 Preview；不会改动上一级项目中的论文、原海报或实验数据。

本次制作实际使用了 Codex bundled Python，未进行全新 pip 安装。使用该环境重新生成的命令为：

```zsh
/Users/shanse/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 source/build_poster.py --revision 8
zsh source/render_preview.sh
/Users/shanse/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 source/validate_poster.py
```

`pdftoppm` 已加入本次运行 PATH；在普通终端可使用 `brew install poppler` 安装。程序化核查完成后仍应放大预览，逐项检查标题、公式、状态机箭头、各轴标/数字、八行矩阵和底部边距。验证通过不等于印厂 ICC 或实体打样通过。

## 编辑内容

身份、题目、字体路径在 config 中编辑；文字、布局坐标、颜色、数学下标与矢量图形在 build_poster.py 中编辑。坐标以成品左上角为原点，单位 mm，字体单位 pt；源码自动加3 mm出血。

数据来自已有实验。图表优先读取 summary.json，但 validator 会与原始 CSV 重算核对。若改实验数据，必须同步 CSV 与对应汇总，保留证据来源，不能只改图中的数字或 summary 值。

关于代码中颜色：采用过程 CMYK，没有绑定印厂 ICC；普通屏幕 PNG 是渲染预览，不能当成合同色样。需要特定 PDF/X/ICC 时，应交给印厂进行下一步印前处理。

## 提交前留意

海报已明确标记 801.10 与论文801.21差异、96.33%的统计口径、SLASHED 状态限制。待确认清单详见修改报告。没有加入伪造 DOI、网址、二维码或 Logo。

根据用户提供的会议通知，收件人 ndbc2026@126.com，邮件标题采用完整论文题目；截止2026年10月12日24:00（北京时间）。本任务没有发送邮件或替作者注册。
