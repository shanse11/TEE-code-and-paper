# -*- coding: utf-8 -*-
"""把模板 RTF 解码为「段落文本 + 段落/字符格式」，用于提取模板真实排版参数。"""
import re, sys, json

P = "/Users/shanse/Documents/ChatGPT/Hybrid TEE-Rollup/outputs/template_alignment/work/template.rtf"
raw = open(P, encoding="utf-8", errors="replace").read()

# --- 解码 \uN (uc0) 与 \'xx ---
def decode(s):
    out = []
    i = 0
    while i < len(s):
        if s[i] == '\\':
            m = re.match(r"\\u(-?\d+)\??", s[i:])
            if m:
                out.append(chr(int(m.group(1)) & 0xFFFF)); i += m.end(); continue
            m = re.match(r"\\'([0-9a-fA-F]{2})", s[i:])
            if m:
                out.append(bytes([int(m.group(1), 16)]).decode('cp1252', 'replace')); i += m.end(); continue
            m = re.match(r"\\[a-zA-Z]+-?\d* ?", s[i:])
            if m:
                out.append(m.group(0)); i += m.end(); continue
            out.append(s[i]); i += 1
        else:
            out.append(s[i]); i += 1
    return ''.join(out)

txt = decode(raw)
open("/Users/shanse/Documents/ChatGPT/Hybrid TEE-Rollup/outputs/template_alignment/work/template_decoded.txt", "w", encoding="utf-8").write(txt)
print("decoded len", len(txt))

# --- 按段落切分，记录格式 ---
GEN = re.compile(r"\\(f|fs|b|i|sa|sb|sl|li|fi|ri|qc|qj|ql|qr|cols|sbys|tx|pard|par|sect|margl|margr|margt|margb|slmult|outlinelevel|ls|ilvl|pn|deftab|ri)\b")
paras = []
# 以 \pard 作为段落开始
parts = re.split(r"\\pard", txt)
for seg in parts:
    fmts = re.findall(r"\\(f\d+|fs\d+|b\d*|i\d*|sa\d+|sb\d+|sl\d+|li\d+|fi\d+|ri\d+|qc|qj|ql|qr|cols\d+|slmult\d+|ls\d+|ilvl\d+)", seg)
    # 取文本（去掉控制字）
    plain = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", seg)
    plain = plain.replace("{", "").replace("}", "").strip()
    if plain:
        paras.append((fmts, plain[:60]))
targets = ['文  题','第1作者','一级单位全称','摘要用于提示','5个中文关键词','中图分类号',
           'Title','NAME Name1','keyword; keyword','引言','一级标题','二级标题','三级标题',
           '正文内容','参考文献','三种网络的消息交付率比较','实验中使用的UCI数据集','基金项目','作者简介']
for t in targets:
    hit = [(f, p) for f, p in paras if t in p]
    print("=" * 60)
    print("TARGET:", t, "hits:", len(hit))
    for f, p in hit[:2]:
        print("   fmt:", f)
        print("   txt:", p)
