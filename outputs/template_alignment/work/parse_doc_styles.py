# -*- coding: utf-8 -*-
"""直接解析 Word97 (.doc) 的样式表 (STSH) —— 不依赖任何转换工具。
参考 MS-DOC 2.4.x / 2.7.x：Fib -> fcStshfOrig/fcStshf -> Stshif -> STD 数组。
"""
import olefile, struct, sys, re, json

path = "/Users/shanse/Documents/ChatGPT/Hybrid TEE-Rollup/投稿模版.doc"
f = olefile.OleFileIO(path)
wd = f.openstream('WordDocument').read()
tbl = f.openstream('1Table').read() if f.exists('1Table') else f.openstream('0Table').read()

# ---- FIB ----
base = wd[:32]
wIdent, nFib = struct.unpack('<HH', wd[0:4])
fcMin = struct.unpack('<I', wd[0x18:0x1C])[0]
# 找出 FibRgFcLcb97 中 StshfOrig 的偏移
# Fib base 32 bytes; csw=14 (WORD) -> fibRgW 28 bytes -> cslw=22 LONG
# 实际：offset of fcStshfOrig in FibRgFcLcb97 = 0 (rgFcLcb97 起始) 之后的若干项
# 直接用 FIB 长度推导
# fibRgFcLcb97 布局（前若干项）:
#  0 fcStshfOrig(4) lcb(4) = 8
#  1 fcStshf      -> 8
#  2 fcPlcffndRef -> 16
#  3 fcPlcffndTxt -> 24
#  4 fcPlcfandRef -> 32
#  5 fcPlcfandTxt -> 40
#  6 fcPlcfsed    -> 48
#  7 fcPlcpad     -> 56
#  8 fcPlcfphe    -> 64
FC_STSH_ORIG = 0x00A2  # 常用值，稍后校验
# 更稳妥：从 fcMin 开始按 rgFcLcb97 顺序，先取 fcStshfOrig 与 lcbStshf
# Fib base(32) + csw(2)+14*2(28) + cslw(2)+22*4(88) = 32+30+90 = 152
rg = 152
fcStshfOrig, lcbStshfOrig = struct.unpack('<II', wd[rg+0:rg+8])
fcStshf, lcbStshf = struct.unpack('<II', wd[rg+8:rg+16])
print(f"fcStshfOrig=0x{fcStshfOrig:x}({fcStshfOrig}) lcb={lcbStshfOrig}  fcStshf=0x{fcStshf:x} lcb={lcbStshf}")
# fcStshf 通常指向 0Table/1Table；WordDocument 的流用 fc 判断高位
def read_fc(fc, lcb):
    if fc & 0x40000000:      # 在 Table 流
        off = fc & 0x3FFFFFFF
        return tbl[off:off+lcb]
    return wd[fc:fc+lcb]

stsh = read_fc(fcStshf, lcbStshf) or read_fc(fcStshfOrig, lcbStshfOrig)
print("stsh len:", len(stsh), "head:", stsh[:16].hex())

# ---- Stshif ----
cstd, cbSTDBaseInFile, flags = struct.unpack('<HHH', stsh[0:6])
assert (flags & 0x00FF) == 0x01, hex(flags)
stiMaxWhenSaved, istdMaxFixedWhenSaved, nVerBuiltInNamesWhenSaved, rgftcStandardChpStsh = struct.unpack('<hhhh', stsh[6:14])
print("cstd", cstd, "cbSTDBaseInFile", cbSTDBaseInFile, "rgftcStandardChpStsh", rgftcStandardChpStsh)
pos = 14
# 扩展 Stshi（若 rgftcStandardChpStsh==0x0FFF -> 16 项 ftc，否则 3 项）
n_ftc = 3
if stsh[10:12] == b'\xff\x0f':
    n_ftc = 16
    pos = 14 - 2  # 已在 6..14 读了 4 个 short，其中第4个是 0x0FFF 标记
    # 重新定位：Stshi = 2+2+2+2+2+2+ 2*n_ftc
    pos = 12
    pos += 2 * n_ftc
    # 之后是 ftcAsci/cv? 简化：继续
print("pos", pos, "n_ftc", n_ftc)

# FFN 表：附加字体名（在样式数据之后），先跳过
# STD 数组从 pos 开始（Stshi 之后）
# 标准 Stshi 长度 = 2(cstd)+2(cbSTDBaseInFile)+2(flags)+2(stiMax)+2(istdMaxFixed)+2(nVerBuiltInNames)+2*3(ftc)=18
pos = 18 if n_ftc == 3 else 12 + 2*n_ftc + 2
print("STD start pos:", pos)

def parse_prm(prm, base_len_names, is_chp=False):
    return prm

results = []
p = pos
for i in range(cstd):
    if p + 4 > len(stsh): break
    cbStd = struct.unpack('<H', stsh[p:p+2])[0]
    if cbStd == 0:
        p += 2; continue
    std = stsh[p:p+2+cbStd]
    p += 2 + cbStd
    if len(std) < 4: continue
    # STD: cbStd(2) + fFixedIndex(2, bitfield: fStdStyl|sti) + fMask(2) + stk/based...
    # 实际 STD 结构: cbStd(2) | (fStdStyle:1, sti:11, fScratch:1, fInvalHeight:1, fHasUpe:1, fMassCopy:1)=2 | fMask(2) | ...
    # MS-DOC STD: cbStd(2), fixedIndex(2), mask(2) 之后是 6 字节的 STSHI? 不准确。
    # 采用更稳的做法：STD 内 upx 之后是名字
    fixed = struct.unpack('<H', std[2:4])[0]
    mask  = struct.unpack('<H', std[4:6])[0]
    sti   = fixed & 0x0FFF
    # STD 变体判定：(fixed & 0xF000)>>12 ... 实际 STD: cbStd(2), then
    #  WORD 1: fStdStyle(1) sti(11) fScratch(1) fInvalHeight(1) fHasUpe(1) fMassCopy(1)
    #  WORD 2: fHasSdt? 实际是 stk(4 bits) + istdBase(12 bits)  -> 0x0FFF mask
    w2 = struct.unpack('<H', std[6:8])[0]
    stk = (w2 >> 12) & 0xF
    istdBase = w2 & 0x0FFF
    # WORD 3: cupx(4 bits) istdNext(12)
    w3 = struct.unpack('<H', std[8:10])[0]
    cupx = (w3 >> 12) & 0xF
    istdNext = w3 & 0x0FFF
    # WORD 4: bchUpe
    # 之后 cupx 个 UPX：每个 WORD cbUPX 后跟 cbUPX 字节
    off = 12
    upxs = []
    for k in range(cupx):
        if off+2 > len(std): break
        cb = struct.unpack('<H', std[off:off+2])[0]
        off += 2
        upxs.append(std[off:off+cb])
        off += cb
    # 名字：Pascal string (1 byte len) or Unicode?  STD 名字存为 xstz：2字节 cch, 之后 cch*2 字节 UTF-16 (若 fCompressed?)
    # 对新建样式通常为 Unicode xstz
    rest = std[off:]
    name = ''
    try:
        # xstz: cch(2 bytes LE) then chars (1 byte each if fCompressed... 通常2字节)
        cch = struct.unpack('<H', rest[0:2])[0]
        if 0 < cch < 200:
            if len(rest) >= 2 + cch*2:
                nm = rest[2:2+cch*2].decode('utf-16-le')
                if nm.isprintable() or True:
                    name = nm
            if not name and len(rest) >= 2 + cch:
                name = rest[2:2+cch].decode('latin1')
    except Exception as e:
        pass
    results.append(dict(idx=i, sti=sti, stk=stk, base=istdBase, next=istdNext, cupx=cupx,
                        upx_sizes=[len(u) for u in upxs], name=name, raw=std.hex()))

for r in results:
    if r['name']:
        print(f"#{r['idx']:3d} sti=0x{r['sti']:03x} stk={r['stk']} base={r['base']:3d} cupx={r['cupx']} upx={r['upx_sizes']}  name={r['name']!r}")
json.dump(results, open('/Users/shanse/Documents/ChatGPT/Hybrid TEE-Rollup/outputs/template_alignment/work/doc_styles.json','w'), ensure_ascii=False, indent=1)
