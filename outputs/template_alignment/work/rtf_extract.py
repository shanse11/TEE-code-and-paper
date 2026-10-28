# -*- coding: utf-8 -*-
"""从模板 RTF 提取各模板元素的真实排版参数（字体、字号、粗斜、行距、段前段后、对齐、缩进、分栏、页边距）。"""
import re, json
P='/Users/shanse/Documents/ChatGPT/Hybrid TEE-Rollup/outputs/template_alignment/work/template.rtf'
raw=open(P, encoding='utf-8', errors='replace').read()
def gbk_sub(m):
    bs=bytes(int(x,16) for x in re.findall(r"\\'([0-9a-fA-F]{2})", m.group(0)))
    try: return bs.decode('gb18030')
    except Exception: return m.group(0)
txt=re.sub(r"(?:\\'[0-9a-fA-F]{2})+", gbk_sub, raw)
txt=re.sub(r"\\uc0", "", txt)
txt=re.sub(r"\\u(-?\d+)\?? ?", lambda m: chr(int(m.group(1)) & 0xFFFF), txt)
open('/Users/shanse/Documents/ChatGPT/Hybrid TEE-Rollup/outputs/template_alignment/work/template_decoded.txt','w',encoding='utf-8').write(txt)

# 段落：以 \pard 起始；同时记录 \sect 级与页边距/分栏
chunks=re.split(r'\\pard', txt)
FMT=r"\\(f\d+|fs\d+|b\d*|i\d*|sa\d+|sb\d+|sl\d+|li\d+|fi\d+|ri\d+|qc|qj|ql|qr|slmult\d+)"
paras=[]
for seg in chunks:
    fmts=re.findall(FMT, seg)
    plain=re.sub(r"\\[a-zA-Z]+-?\d* ?",'',seg).replace('{','').replace('}','').replace('\n','')
    plain=re.sub(r'\s+',' ',plain).strip()
    if plain: paras.append((fmts, plain))

def report(label, key, n=1):
    hits=[(f,p) for f,p in paras if key in p]
    print(f'--- {label} [{key}] hits={len(hits)}')
    for f,p in hits[:n]:
        print('    fmt:', ' '.join(f))
        print('    txt:', p[:90])

for label,key in [
 ('DOI/首页','doi:10.11772'),('文题(中文)','文  题'),('作者名(中文)','第1作者'),
 ('单位(中文)','一级单位全称'),('通信作者邮箱','通信作者电子邮箱'),
 ('摘要(中文)','摘要用于提示'),('关键词(中文)','5个中文关键词'),('中图分类号','中图分类号'),
 ('文题(英文)','Title'),('作者名(英文)','NAME Name1'),('单位(英文)','College of'),
 ('摘要(英文)','与中文的内容一致'),('关键词(英文)','keyword; keyword'),
 ('引言','引言'),('一级标题','一级标题'),('二级标题','二级标题'),('三级标题','三级标题'),
 ('正文','正文内容'),('参考文献','参考文献'),('图表名称(图)','三种网络的消息交付率比较'),
 ('图表名称(表)','实验中使用的UCI数据集'),('文献列表','文献列表'),
 ('基金项目','基金项目'),('作者简介','作者简介'),('定义定理','定理'),('结论证明','证明'),
]:
    report(label,key)

print()
print('=== 全文档级别：页边距/分栏/纸张 ===')
for k in ['\\margl','\\margr','\\margt','\\margb','\\cols','\\sectd','\\paperw','\\paperh','\\headery','\\footery']:
    vals=re.findall(re.escape(k)+r'(-?\d+)', txt)
    from collections import Counter
    print(k, Counter(vals).most_common(6))
print()
print('=== 分节标记 \sect 出现次数:', txt.count('\\sect'))
