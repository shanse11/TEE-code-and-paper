"""图片插入工具：绕过 python-docx 对 EMF/SVG 的识别限制，手工构建 w:drawing。"""
import hashlib
import os
import re

from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI as PackUri
from docx.oxml.ns import qn
from lxml import etree

WP_EXTENT = '{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}extent'
A_EXT = '{http://schemas.openxmlformats.org/drawingml/2006/main}ext'
R_EMBED = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed'

MIME = {
    '.emf': 'image/x-emf',
    '.wmf': 'image/x-wmf',
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
}

_UNIT_PT = {'pt': 1.0, 'px': 0.75, 'mm': 72.0 / 25.4, 'cm': 72.0 / 2.54, 'in': 72.0, 'pc': 12.0}


def svg_size_emu(path):
    """从 SVG 根元素读取 width/height，返回 (cx, cy) EMU。"""
    head = open(path, 'rb').read(8192).decode('utf-8', 'ignore')
    m = re.search(r'<svg[^>]*>', head, re.S)
    tag = m.group(0) if m else ''
    vb = re.search(r'viewBox\s*=\s*["\']\s*([-\d.eE]+)[\s,]+([-\d.eE]+)[\s,]+([-\d.eE]+)[\s,]+([-\d.eE]+)', tag)
    w = re.search(r'\bwidth\s*=\s*["\']\s*([-\d.eE]+)\s*([a-zA-Z%]*)', tag)
    h = re.search(r'\bheight\s*=\s*["\']\s*([-\d.eE]+)\s*([a-zA-Z%]*)', tag)

    def val(mo, default=None):
        if not mo:
            return None
        num = float(mo.group(1))
        unit = (mo.group(2) or 'px').lower()
        if unit == '%' or unit == '':
            unit = 'px'
        return num * _UNIT_PT.get(unit, 0.75)

    wpt = val(w); hpt = val(h)
    if wpt and hpt:
        pass
    elif vb:
        wpt = float(vb.group(3)); hpt = float(vb.group(4))
    else:
        raise ValueError('cannot read svg size: %s' % path)
    return int(round(wpt * 12700)), int(round(hpt * 12700))


def _next_media_name(package, ext):
    n = 1
    while True:
        pn = PackUri('/word/media/image%d%s' % (n, ext))
        if pn not in [p.partname for p in package.iter_parts()]:
            return pn
        n += 1


def make_drawing(doc, img_path, width_emu, template_drawing=None, name=None,
                 aspect_src=None):
    """返回可附加到 w:r 的 <w:drawing> 元素；图像部件与关系一并建立。"""
    ext = os.path.splitext(img_path)[1].lower()
    blob = open(img_path, 'rb').read()
    package = doc.part.package

    # 去重：相同 sha1 直接复用
    sha1 = hashlib.sha1(blob).hexdigest()
    for rel in doc.part.rels.values():
        if rel.reltype == RT.IMAGE and rel.is_external is False:
            try:
                if hashlib.sha1(rel.target_part.blob).hexdigest() == sha1:
                    rId = rel.rId
                    break
            except Exception:
                pass
    else:
        from docx.opc.part import Part
        pn = _next_media_name(package, ext)
        ipart = Part(pn, MIME[ext], blob, package)
        rId = doc.part.relate_to(ipart, RT.IMAGE)

    if template_drawing is None:
        raise ValueError('template_drawing required')
    el = etree.fromstring(etree.tostring(template_drawing))
    if width_emu:
        if ext == '.svg' or aspect_src:
            # 一律以 SVG 源的固有比例为准：LibreOffice 转出的 EMF 帧比例有 2%~9% 偏差，
            # 按 EMF 头部比例排版会使插图变形。
            cx0, cy0 = svg_size_emu(aspect_src or img_path)
        else:
            cx0, cy0 = _png_like_size(img_path)
        cy = int(round(width_emu * cy0 / float(cx0)))
        for tag in (WP_EXTENT, A_EXT):
            for e in el.iter(tag):
                e.set('cx', str(int(width_emu)))
                e.set('cy', str(cy))
    dp = el.find('.//{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}docPr')
    if dp is not None:
        dp.set('id', str(1000 + int(rId[3:]) if rId[3:].isdigit() else 1000))
        dp.set('name', name or os.path.basename(img_path))
        dp.set('descr', os.path.basename(img_path))
    for b in el.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}blip'):
        b.set(R_EMBED, rId)
    return el


def _png_like_size(path):
    import struct
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.png',):
        data = open(path, 'rb').read(33)
        w, h = struct.unpack('>II', data[16:24])
        return int(w * 9525), int(h * 9525)
    if ext in ('.emf', '.wmf'):
        # 从 0.01mm 单位头读取
        data = open(path, 'rb').read(80)
        if ext == '.emf':
            # EMR_HEADER: bounds(16) frame(16) signature..  rclFrame at offset 8+16=24? 用 header 结构
            # Type(4) Size(4) rclBounds(16) rclFrame(16) -> offset 8+16=24 起为 rclFrame(4x LONG, 0.01mm)
            l, t, r, b = struct.unpack('<iiii', data[24:40])
            w_mm = (r - l) / 100.0
            h_mm = (b - t) / 100.0
        else:
            # WMF placeable header: key(4) hwnd(2) bbox(8) inch(2)
            if data[:4] == b'\xd7\xcd\xc6\x9a':
                x1, y1, x2, y2 = struct.unpack('<hhhh', data[6:14])
                inch = struct.unpack('<H', data[14:16])[0]
                w_mm = (x2 - x1) / 1440.0 * 25.4
                h_mm = (y2 - y1) / 1440.0 * 25.4
            else:
                w_mm = h_mm = 100.0
        return int(w_mm / 25.4 * 914400), int(h_mm / 25.4 * 914400)
    raise ValueError(ext)
