import sys, docx, zipfile, re
from docx.oxml.ns import qn
from docx.shared import Pt
p = sys.argv[1]
d = docx.Document(p)
print("=== SECTIONS ===")
for i,s in enumerate(d.sections):
    def cm(v): return round(v/360000,3) if v is not None else None
    print(f"sec{i}: W={cm(s.page_width)} H={cm(s.page_height)} L={cm(s.left_margin)} R={cm(s.right_margin)} T={cm(s.top_margin)} B={cm(s.bottom_margin)} hd={cm(s.header_distance)} ft={cm(s.footer_distance)} cols?")
    cols = s._sectPr.find(qn('w:cols'))
    if cols is not None:
        print("   cols num=", cols.get(qn('w:num')), "space=", cols.get(qn('w:space')), "equalWidth=", cols.get(qn('w:equalWidth')))
        for c in cols.findall(qn('w:col')):
            print("    col w=",c.get(qn('w:w')), "space=",c.get(qn('w:space')))
    else:
        print("   cols: single (no w:cols)")
    print("   type=", s._sectPr.find(qn('w:type')) is not None and s._sectPr.find(qn('w:type')).get(qn('w:val')))
print()
print("=== STYLES DEFINED ===")
for st in d.styles:
    try:
        f=st.font
        print(f"{st.name!r:28s} type={st.type} font={f.name} ea={f.element.rPr.find(qn('w:rFonts')).get(qn('w:eastAsia')) if f.element.rPr is not None and f.element.rPr.find(qn('w:rFonts')) is not None else None} size={f.size.pt if f.size else None} bold={f.bold} italic={f.italic}")
    except Exception as e:
        print(f"{st.name!r:28s} err {e}")
print()
print("=== STYLE DEFS RAW (paragraphMark + spacing) ===")
for st in d.styles:
    if st.type is None: continue
    el=st.element
    pPr = el.find(qn('w:pPr'))
    if pPr is None: continue
    sp = pPr.find(qn('w:spacing'))
    op = pPr.find(qn('w:outlineLvl'))
    np = pPr.find(qn('w:numPr'))
    indp = pPr.find(qn('w:ind'))
    if sp is None and op is None and np is None: continue
    info=[]
    if sp is not None:
        info.append(" ".join(f"{k}={v}" for k,v in sp.attrib.items()))
    if op is not None: info.append("outlineLvl="+op.get(qn('w:val')))
    if np is not None:
        il=np.find(qn('w:ilvl')); npi=np.find(qn('w:numId'))
        info.append(f"numPr ilvl={il.get(qn('w:val')) if il is not None else None} numId={npi.get(qn('w:numId')) if npi is not None else None}")
    if indp is not None: info.append("ind "+" ".join(f"{k}={v}" for k,v in indp.attrib.items()))
    print(f"{st.name!r:24s} {' | '.join(info)}")
