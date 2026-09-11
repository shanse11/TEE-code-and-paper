#!/usr/bin/env python
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent
from zipfile import ZIP_DEFLATED, ZipFile


TITLE = "区块链实验室4月津贴发放清单"
HEADERS = ["序号", "姓名", "硕/博", "学号", "导师", "工作内容", "津贴等级"]
ROW = [
    "2",
    "杨帆",
    "硕士",
    "51285903029",
    "赵春艳",
    (
        "本月围绕“在保证去中心化安全性的前提下提升高频DApp性能”这一目标开展研究："
        "完成 Optimistic + Challenge 机制 Demo 及端到端验证；在此基础上构建执行层（模拟TEE）、"
        "验证层、数据层三层闭环原型，实现 challenge/respond/resolve、二分定位与单步重放验证；"
        "设计轻量化 DA 提交方案并开展成本量化实验，结果显示轻量提交相较全量上链字节平均降幅 53.76%，"
        "Gas 估算降幅 53.76% 至 65.32%；同时系统阅读 OTR、TeeRollup、Dynamic Fraud Proof 等相关论文，"
        "为后续动态挑战期和更真实 DA 方案设计提供理论与工程参考。"
    ),
    "",
]


def col_name(index):
    result = []
    while index:
        index, rem = divmod(index - 1, 26)
        result.append(chr(65 + rem))
    return "".join(reversed(result))


def inline_cell(ref, text, style_id):
    escaped = (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return (
        f'<c r="{ref}" t="inlineStr" s="{style_id}"><is><t xml:space="preserve">'
        f"{escaped}</t></is></c>"
    )


def build_sheet_xml():
    widths = [8, 10, 10, 18, 10, 52, 12]
    cols = []
    for idx, width in enumerate(widths, start=1):
        cols.append(f'<col min="{idx}" max="{idx}" width="{width}" customWidth="1"/>')

    title_cells = inline_cell("A1", TITLE, 1)
    header_cells = "".join(
        inline_cell(f"{col_name(i)}2", header, 2) for i, header in enumerate(HEADERS, start=1)
    )
    row_cells = "".join(
        inline_cell(f"{col_name(i)}3", value, 3 if i == 6 else 4)
        for i, value in enumerate(ROW, start=1)
    )

    return dedent(
        f"""\
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
          <sheetViews>
            <sheetView workbookViewId="0"/>
          </sheetViews>
          <sheetFormatPr defaultRowHeight="18"/>
          <cols>
            {''.join(cols)}
          </cols>
          <sheetData>
            <row r="1" ht="28" customHeight="1">
              {title_cells}
            </row>
            <row r="2" ht="24" customHeight="1">
              {header_cells}
            </row>
            <row r="3" ht="120" customHeight="1">
              {row_cells}
            </row>
          </sheetData>
          <mergeCells count="1">
            <mergeCell ref="A1:G1"/>
          </mergeCells>
          <pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>
        </worksheet>
        """
    ).strip()


def build_styles_xml():
    return dedent(
        """\
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
          <fonts count="3">
            <font>
              <sz val="11"/>
              <name val="宋体"/>
            </font>
            <font>
              <b/>
              <sz val="14"/>
              <name val="宋体"/>
            </font>
            <font>
              <b/>
              <sz val="11"/>
              <name val="宋体"/>
            </font>
          </fonts>
          <fills count="2">
            <fill><patternFill patternType="none"/></fill>
            <fill><patternFill patternType="gray125"/></fill>
          </fills>
          <borders count="2">
            <border>
              <left/><right/><top/><bottom/><diagonal/>
            </border>
            <border>
              <left style="thin"><color auto="1"/></left>
              <right style="thin"><color auto="1"/></right>
              <top style="thin"><color auto="1"/></top>
              <bottom style="thin"><color auto="1"/></bottom>
              <diagonal/>
            </border>
          </borders>
          <cellStyleXfs count="1">
            <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
          </cellStyleXfs>
          <cellXfs count="5">
            <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
            <xf numFmtId="0" fontId="1" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1">
              <alignment horizontal="center" vertical="center"/>
            </xf>
            <xf numFmtId="0" fontId="2" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1">
              <alignment horizontal="center" vertical="center"/>
            </xf>
            <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1">
              <alignment horizontal="left" vertical="center" wrapText="1"/>
            </xf>
            <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1">
              <alignment horizontal="center" vertical="center" wrapText="1"/>
            </xf>
          </cellXfs>
          <cellStyles count="1">
            <cellStyle name="Normal" xfId="0" builtinId="0"/>
          </cellStyles>
        </styleSheet>
        """
    ).strip()


def write_xlsx(output_path):
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    workbook_xml = dedent(
        """\
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
                  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
          <sheets>
            <sheet name="4月津贴清单" sheetId="1" r:id="rId1"/>
          </sheets>
        </workbook>
        """
    ).strip()
    workbook_rels = dedent(
        """\
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
          <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
          <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
        </Relationships>
        """
    ).strip()
    root_rels = dedent(
        """\
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
          <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
          <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
          <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
        </Relationships>
        """
    ).strip()
    content_types = dedent(
        """\
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
          <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
          <Default Extension="xml" ContentType="application/xml"/>
          <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
          <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
          <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
          <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
          <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
        </Types>
        """
    ).strip()
    core_xml = dedent(
        f"""\
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:dcterms="http://purl.org/dc/terms/"
            xmlns:dcmitype="http://purl.org/dc/dcmitype/"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <dc:creator>Codex</dc:creator>
          <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
          <dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>
          <dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified>
          <dc:title>{TITLE}</dc:title>
        </cp:coreProperties>
        """
    ).strip()
    app_xml = dedent(
        """\
        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
                    xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
          <Application>Microsoft Excel</Application>
          <DocSecurity>0</DocSecurity>
          <ScaleCrop>false</ScaleCrop>
          <HeadingPairs>
            <vt:vector size="2" baseType="variant">
              <vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant>
              <vt:variant><vt:i4>1</vt:i4></vt:variant>
            </vt:vector>
          </HeadingPairs>
          <TitlesOfParts>
            <vt:vector size="1" baseType="lpstr">
              <vt:lpstr>4月津贴清单</vt:lpstr>
            </vt:vector>
          </TitlesOfParts>
        </Properties>
        """
    ).strip()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("docProps/core.xml", core_xml)
        zf.writestr("docProps/app.xml", app_xml)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zf.writestr("xl/styles.xml", build_styles_xml())
        zf.writestr("xl/worksheets/sheet1.xml", build_sheet_xml())


def main():
    workspace_root = Path(__file__).resolve().parents[2]
    output = workspace_root / "admin" / "allowance" / "区块链实验室4月津贴发放清单-杨帆.xlsx"
    write_xlsx(output)
    print(output)


if __name__ == "__main__":
    main()
