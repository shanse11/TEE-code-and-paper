from __future__ import annotations

import copy
import re
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


BASE = Path(__file__).resolve().parent
SRC = BASE / "Hybrid_TEE_Rollup_修订版.docx"
OUT = BASE / "Hybrid_TEE_Rollup_参考文献格式修订版.docx"

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W = NS["w"]
ET.register_namespace("w", W)


REFS = [
    "[1] WEN X, FENG Q, LYU H, et al. TEEROLLUP: efficient Rollup design using heterogeneous TEE[EB/OL]. arXiv:2409.14647, 2024 [2026-06-15]. https://arxiv.org/abs/2409.14647.",
    "[2] BUTERIN V. An incomplete guide to Rollups[EB/OL]. 2021 [2026-06-15]. https://vitalik.ca/general/2021/01/05/rollup.html.",
    "[3] ETHEREUM FOUNDATION. Optimistic Rollups[EB/OL]. 2024 [2026-06-15]. https://ethereum.org/en/developers/docs/scaling/optimistic-rollups/.",
    "[4] ARBITRUM FOUNDATION. Arbitrum Nitro technical documentation[EB/OL]. 2024 [2026-06-15]. https://docs.arbitrum.io/.",
    "[5] OP LABS. Optimism documentation: fault proofs and dispute games[EB/OL]. 2024 [2026-06-15]. https://docs.optimism.io/.",
    "[6] PICCO G, FORTUGNO A. Dynamic fraud proof[EB/OL]. arXiv:2502.10321, 2025 [2026-06-15]. https://arxiv.org/abs/2502.10321.",
    "[7] AL-BASSAM M. LazyLedger: a distributed data availability ledger with client-side smart contracts[EB/OL]. arXiv:1905.09274, 2019 [2026-06-15]. https://arxiv.org/abs/1905.09274.",
    "[8] TAS E N, TSE D, YANG L, et al. Light clients for lazy blockchains[EB/OL]. arXiv:2203.15968, 2022 [2026-06-15]. https://arxiv.org/abs/2203.15968.",
    "[9] EIGENLABS. EigenDA documentation[EB/OL]. 2024 [2026-06-15]. https://docs.eigencloud.xyz/products/eigenda/.",
    "[10] CELESTIA. Celestia: modular blockchain network[EB/OL]. 2024 [2026-06-15]. https://docs.celestia.org/.",
    "[11] INTEL CORPORATION. Intel Software Guard Extensions developer guide[EB/OL]. 2024 [2026-06-15]. https://www.intel.com/content/www/us/en/developer/tools/software-guard-extensions/overview.html.",
    "[12] ETHEREUM FOUNDATION. EIP-4844: shard blob transactions[EB/OL]. 2024 [2026-06-15]. https://eips.ethereum.org/EIPS/eip-4844.",
]


def qn(tag: str) -> str:
    return f"{{{W}}}{tag}"


def text_of(p: ET.Element) -> str:
    return "".join(t.text or "" for t in p.findall(".//w:t", NS))


def ensure_child(parent: ET.Element, tag: str) -> ET.Element:
    child = parent.find(f"w:{tag}", NS)
    if child is None:
        child = ET.SubElement(parent, qn(tag))
    return child


def set_val(el: ET.Element, value: str) -> None:
    el.set(qn("val"), value)


def clear_text_runs(p: ET.Element) -> tuple[ET.Element | None, ET.Element | None]:
    ppr = p.find("w:pPr", NS)
    base_rpr = None
    for r in p.findall("w:r", NS):
        rpr = r.find("w:rPr", NS)
        if rpr is not None:
            base_rpr = copy.deepcopy(rpr)
            break
    for child in list(p):
        if child.tag != qn("pPr"):
            p.remove(child)
    return ppr, base_rpr


def make_run(text: str, base_rpr: ET.Element | None = None, superscript: bool = False) -> ET.Element:
    r = ET.Element(qn("r"))
    rpr = copy.deepcopy(base_rpr) if base_rpr is not None else ET.Element(qn("rPr"))
    if superscript:
        for old in rpr.findall("w:vertAlign", NS):
            rpr.remove(old)
        va = ET.SubElement(rpr, qn("vertAlign"))
        set_val(va, "superscript")
    if len(rpr):
        r.append(rpr)
    t = ET.SubElement(r, qn("t"))
    if text[:1].isspace() or text[-1:].isspace():
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    return r


def replace_para_text(p: ET.Element, text: str, base_rpr: ET.Element | None = None) -> None:
    _, old_rpr = clear_text_runs(p)
    p.append(make_run(text, base_rpr or old_rpr))


def set_font_size(rpr: ET.Element, half_points: str) -> None:
    for tag in ("sz", "szCs"):
        el = ensure_child(rpr, tag)
        set_val(el, half_points)


def set_fonts(rpr: ET.Element, east_asia: str, latin: str) -> None:
    fonts = ensure_child(rpr, "rFonts")
    fonts.set(qn("eastAsia"), east_asia)
    fonts.set(qn("ascii"), latin)
    fonts.set(qn("hAnsi"), latin)
    fonts.set(qn("cs"), latin)


def reference_rpr() -> ET.Element:
    rpr = ET.Element(qn("rPr"))
    set_fonts(rpr, "宋体", "Times New Roman")
    set_font_size(rpr, "18")
    return rpr


def format_reference_para(p: ET.Element) -> None:
    ppr = ensure_child(p, "pPr")
    spacing = ensure_child(ppr, "spacing")
    spacing.set(qn("before"), "0")
    spacing.set(qn("after"), "0")
    spacing.set(qn("line"), "220")
    spacing.set(qn("lineRule"), "auto")
    ind = ensure_child(ppr, "ind")
    ind.set(qn("left"), "360")
    ind.set(qn("hanging"), "360")
    jc = ensure_child(ppr, "jc")
    set_val(jc, "left")


def format_ref_heading(p: ET.Element) -> None:
    ppr = ensure_child(p, "pPr")
    spacing = ensure_child(ppr, "spacing")
    spacing.set(qn("before"), "0")
    spacing.set(qn("after"), "0")
    _, old = clear_text_runs(p)
    rpr = copy.deepcopy(old) if old is not None else ET.Element(qn("rPr"))
    set_fonts(rpr, "黑体", "Times New Roman")
    set_font_size(rpr, "21")
    ensure_child(rpr, "b")
    p.append(make_run("参考文献：", rpr))


def normalize_citation_spacing(s: str) -> str:
    s = re.sub(r"\]\s+\[", "][", s)
    s = re.sub(r"[\uFFFE\u00AD]", "", s)
    return s


def superscript_citations(p: ET.Element) -> None:
    original = text_of(p)
    normalized = normalize_citation_spacing(original)
    if not re.search(r"\[\d+\]", normalized):
        if normalized != original:
            replace_para_text(p, normalized)
        return
    _, base_rpr = clear_text_runs(p)
    parts = re.split(r"(\[\d+\])", normalized)
    for part in parts:
        if not part:
            continue
        p.append(make_run(part, base_rpr, superscript=bool(re.fullmatch(r"\[\d+\]", part))))


def main() -> None:
    if not SRC.exists():
        raise FileNotFoundError(SRC)
    if OUT.exists():
        OUT.unlink()
    tmp = OUT.with_suffix(".tmp.docx")
    if tmp.exists():
        tmp.unlink()
    shutil.copy2(SRC, tmp)

    with zipfile.ZipFile(tmp, "r") as zf:
        xml = zf.read("word/document.xml")
        root = ET.fromstring(xml)
        body = root.find("w:body", NS)
        assert body is not None
        paras = body.findall("w:p", NS)

        ref_heading_idx = None
        for i, p in enumerate(paras):
            if text_of(p).strip().replace(" ", "") in {"参考文献", "参考文献："}:
                ref_heading_idx = i
                break
        if ref_heading_idx is None:
            raise RuntimeError("Reference heading not found")

        format_ref_heading(paras[ref_heading_idx])

        ref_paras = []
        for p in paras[ref_heading_idx + 1 :]:
            if re.match(r"^\[\d+\]", text_of(p).strip()):
                ref_paras.append(p)
        if len(ref_paras) != len(REFS):
            raise RuntimeError(f"Expected {len(REFS)} reference paragraphs, found {len(ref_paras)}")

        for p, ref_text in zip(ref_paras, REFS):
            replace_para_text(p, ref_text, reference_rpr())
            format_reference_para(p)

        # Only body text before the bibliography is touched, and only citation markers are split out.
        for p in paras[:ref_heading_idx]:
            superscript_citations(p)

        out_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)

        with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as out_zf:
            for item in zf.infolist():
                if item.filename == "word/document.xml":
                    out_zf.writestr(item, out_xml)
                else:
                    out_zf.writestr(item, zf.read(item.filename))

    tmp.unlink()

    print(OUT)


if __name__ == "__main__":
    main()
