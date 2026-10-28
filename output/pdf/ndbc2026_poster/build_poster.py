"""Build the NDBC poster from existing paper data, without changing evidence."""
from pathlib import Path
import json, math, hashlib
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import CMYKColor
from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
TMP = ROOT / 'tmp/pdfs/ndbc2026_poster'
MM = 72 / 25.4
S = json.loads((ROOT / 'paper_outputs/summary.json').read_text())
G = json.loads((ROOT / 'paper_outputs/evm_gas/measured_gas_summary.json').read_text())
pdfmetrics.registerFont(TTFont('CN', '/System/Library/Fonts/STHeiti Light.ttc', subfontIndex=1))
pdfmetrics.registerFont(TTFont('CNB', '/System/Library/Fonts/STHeiti Medium.ttc', subfontIndex=1))
pdfmetrics.registerFont(TTFont('EN', '/System/Library/Fonts/Supplemental/Arial.ttf'))
pdfmetrics.registerFont(TTFont('ENB', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'))

# Process CMYK throughout; vector text and illustrations remain resolution independent.
NAVY = CMYKColor(.94, .73, .40, .40)
INK = CMYKColor(.83, .65, .40, .35)
TEAL = CMYKColor(.86, .22, .48, .08)
BLUE = CMYKColor(.78, .43, .02, .05)
AMBER = CMYKColor(.02, .48, .88, .03)
MUTED = CMYKColor(.48, .30, .23, .28)
LIGHT = CMYKColor(.05, .025, .018, 0)
PALE = CMYKColor(.085, .005, .045, 0)
RULE = CMYKColor(.16, .07, .055, .015)
WHITE = CMYKColor(0, 0, 0, 0)
TEXT_LOG = []

def make(bleed):
    global C, B, H, TEXT_LOG
    B = bleed; H = 1189 + 2 * B; TEXT_LOG = []
    path = TMP / ('poster_bleed_raw.pdf' if B else 'poster_a0_raw.pdf')
    C = canvas.Canvas(str(path), pagesize=((841+2*B)*MM, H*MM), pageCompression=1,
                      enforceColorSpace='CMYK', initialFontName='CN', initialFontSize=29)
    C.setTitle('P00145 | 面向高频 DApp 的 Hybrid TEE-Rollup 可恢复挑战协议与轻量 DA 成本评估')
    C.setAuthor('杨帆 | 华东师范大学')
    C.setSubject('NDBC 2026 Poster Paper; A0 portrait; vector CMYK; embedded fonts')
    draw()
    C.showPage(); C.save()
    reader = PdfReader(path); writer = PdfWriter(); writer.clone_document_from_reader(reader)
    page = writer.pages[0]
    page.trimbox = RectangleObject([B*MM, B*MM, (841+B)*MM, (1189+B)*MM])
    page.bleedbox = RectangleObject([0,0,(841+2*B)*MM,H*MM])
    page.cropbox = page.mediabox
    filename = 'P00145_NDBC2026_海报_3mm出血印刷版.pdf' if B else 'P00145_NDBC2026_海报_A0成品版.pdf'
    target = OUT / filename
    with target.open('wb') as f: writer.write(f)
    return target, list(TEXT_LOG)

def xy(x, y): return ((x+B)*MM, (H-y-B)*MM)
def box(x,y,w,h,fill=WHITE,stroke=None,r=0):
    C.setFillColor(fill)
    C.setStrokeColor(stroke or fill)
    C.setLineWidth(.6*MM)
    px,py=xy(x,y+h)
    if r: C.roundRect(px,py,w*MM,h*MM,r*MM,fill=1,stroke=int(stroke is not None))
    else: C.rect(px,py,w*MM,h*MM,fill=1,stroke=int(stroke is not None))
def line(x1,y1,x2,y2,color=RULE,width=.55,dash=None):
    C.setStrokeColor(color); C.setLineWidth(width*MM); C.setDash(dash or [])
    C.line(*xy(x1,y1),*xy(x2,y2)); C.setDash([])
def arrow(points,color=TEAL,dash=False):
    for p,q in zip(points,points[1:]): line(*p,*q,color,.75,[4,3] if dash else None)
    p,q=points[-2:]; a=math.atan2(q[1]-p[1],q[0]-p[0]); L=3.3
    path=C.beginPath();path.moveTo(*xy(*q))
    path.lineTo(*xy(q[0]-L*math.cos(a-.48),q[1]-L*math.sin(a-.48)))
    path.lineTo(*xy(q[0]-L*math.cos(a+.48),q[1]-L*math.sin(a+.48)))
    path.close();C.setFillColor(color);C.drawPath(path,fill=1,stroke=0)
def text(s,x,y,size=29,font='CN',color=INK,align='left'):
    C.setFont(font,size);C.setFillColor(color)
    w=pdfmetrics.stringWidth(s,font,size)/MM
    if align=='center': x-=w/2
    elif align=='right': x-=w
    C.drawString(*xy(x,y),s)
    TEXT_LOG.append({'text':s,'x_mm':x,'baseline_y_mm':y,'width_mm':w,'font_pt':size})
    return w
def wrap(s,w,size=29,font='CN'):
    lines=[];curr=''
    for ch in s:
        if ch=='\n':lines.append(curr);curr='';continue
        if curr and pdfmetrics.stringWidth(curr+ch,font,size)>w*MM:
            lines.append(curr);curr=ch
        else:curr+=ch
    if curr:lines.append(curr)
    return lines
def para(s,x,y,w,size=29,leading=13,font='CN',color=INK):
    for st in wrap(s,w,size,font):text(st,x,y,size,font,color);y+=leading
    return y
def panel(x,y,w,h,n,title,subtitle):
    box(x,y,w,h,WHITE,RULE,3)
    box(x+10,y+10,16,16,TEAL,r=2)
    text(n,x+18,y+21,29,'ENB',WHITE,'center')
    text(title,x+33,y+22,35,'CNB')
    text(subtitle,x+11,y+39,22,color=MUTED)
def node(x,y,w,h,title,sub,color=PALE,title_size=30):
    box(x,y,w,h,color,r=3)
    text(title,x+w/2,y+16,title_size,'CNB',align='center')
    for j,s in enumerate(sub):text(s,x+w/2,y+29+j*11,24,align='center')

def draw():
    box(-B,-B,841+2*B,1189+2*B,LIGHT)
    box(-B,-B,841+2*B,157+B,NAVY)
    box(-B,153,841+2*B,4,TEAL)
    text('NDBC 2026  /  第43届 CCF 中国数据库学术会议',26,25,29,'CNB',WHITE)
    text('POSTER PAPER  ·  P00145',815,25,25,'ENB',WHITE,'right')
    text('面向高频 DApp 的 Hybrid TEE-Rollup',26,61,64,'CNB',WHITE)
    text('可恢复挑战协议与轻量 DA 成本评估',26,91,64,'CNB',WHITE)
    text('杨帆（第一作者、通讯作者）  |  华东师范大学',26,120,34,'CNB',WHITE)
    text('2026.10.16-18  ·  上海',815,141,25,'CN',WHITE,'right')
    text('Recoverable Challenges  /  Evidence-bound Commitments  /  DA Cost Modeling',26,142,24,'EN',WHITE)

    # A short research question supplies context before the result cards.
    text('高频 DApp 的关键问题',26,179,34,'CNB',TEAL)
    text('如何让链上提交保持轻量，同时让超时后的争议继续进入重放与结算？',26,201,38,'CNB')
    cards=[(26,'406 B','提交结构平均大小','规范 JSON 序列化；保留证据关联',TEAL),
           (295,'0% → 100%','超时场景挑战完成率','合成原型；每条对比路径 100 个样本',BLUE),
           (564,'96.33%','指定配置下平均模型降幅','相对全量 calldata；非公网费用实测',TEAL)]
    for x,big,label,detail,col in cards:
        box(x,217,251,76,WHITE,RULE,3)
        box(x,217,251,2.4,col)
        text(big,x+12,250,65,'ENB' if '→' not in big else 'CNB',col)
        text(label,x+12,269,29,'CNB')
        text(detail,x+12,283,21,color=MUTED)

    panel(26,309,789,184,'01','系统架构：轻量提交与异常仲裁共享证据','TEE：可信执行环境（本实验为模拟环境）；DA：数据可用性。')
    node(40,362,134,54,'高频 DApp',['连续请求','示例：AI 推理服务'])
    node(215,362,167,54,'链下执行层',['模拟 TEE','响应 + 模拟远程证明'])
    node(444,362,167,54,'链上紧凑提交',['五项绑定字段','链上保留最小证据入口'])
    node(658,362,143,54,'验证与仲裁',['挑战 · 恢复','重放 · 结算'])
    arrow([(174,389),(215,389)]);text('请求',194,383,22,align='center')
    arrow([(382,389),(444,389)]);text('摘要',413,383,22,align='center')
    arrow([(611,389),(658,389)]);text('争议',634,383,22,align='center')
    node(215,440,396,40,'可验证 DA 注册表',['完整提示 / 响应 / 证明 + 字段级 Merkle 证据'],title_size=29)
    arrow([(299,416),(299,440)]);text('发布负载',310,433,22)
    arrow([(527,440),(527,416)],BLUE,dash=True)
    text('根与指针绑定',540,433,22,color=BLUE)
    arrow([(729,416),(729,460),(611,460)],TEAL,dash=True)
    text('争议时取回并检查证据',724,477,22,color=TEAL,align='center')

    panel(26,509,383,211,'02','可恢复挑战机制','恢复流程推进能力；正确性仍由后续重放判断。')
    # Three horizontally aligned steps in each of two rows.
    node(39,563,104,38,'打开挑战',['open'],title_size=28)
    node(166,563,104,38,'响应争议',['respond'],title_size=28)
    node(293,563,103,38,'二分定位',['step'],title_size=28)
    arrow([(143,583),(166,583)]);arrow([(270,583),(293,583)])
    node(39,628,104,38,'会话超时',['timeout'],color=CMYKColor(.005,.06,.12,0),title_size=28)
    node(166,628,104,38,'恢复推进',['recover'],title_size=28)
    node(293,628,103,38,'重放与结算',['replay / resolve'],title_size=28)
    arrow([(344,601),(344,614),(91,614),(91,628)],AMBER,dash=True)
    arrow([(143,647),(166,647)],AMBER);arrow([(270,647),(293,647)])
    text('继续定位',228,624,21,color=TEAL)
    arrow([(218,628),(218,611),(281,611),(281,583),(293,583)],TEAL,dash=True)
    arrow([(396,583),(401,583),(401,647),(396,647)],TEAL)
    text('Facts(before) = Facts(after)',39,686,29,'ENB',TEAL)
    text('状态根、DA 根、负载哈希、轨迹与争议证据不因恢复而改写。',39,703,22)

    panel(432,509,383,211,'03','紧凑提交隔离负载增长','规范 JSON 字节数；提示长度 64；各配置 100 个样本。')
    # Vector bar chart. Serialised payload sizes, never ABI bytes or real Blob costs.
    rows=[next(v for v in S['cost_summary'] if v['payload_size']==p and v['prompt_length']==64 and v['batch_size']==1) for p in [128,512,2048,8192]]
    labels=['128','512','2048','8192'];x0=479; x1=794; y0=658; yt=575
    text('平均提交字节数（kB，十进制）',445,563,23,color=MUTED)
    for val in [0,25,50]:
        yy=y0-val/55000*1000*(y0-yt)
        line(x0,yy,x1,yy);text(str(val),474,yy+2,21,'EN',MUTED,'right')
    for i,(r,lab) in enumerate(zip(rows,labels)):
        xx=509+i*77
        h=r['avg_full_bytes']/55000*(y0-yt)
        box(xx-16,y0-h,21,h,BLUE)
        h2=r['avg_compact_bytes']/55000*(y0-yt)
        box(xx+8,y0-h2,21,max(h2,.9),TEAL)
        text(f"{r['avg_full_bytes']/1000:.2f}",xx-5,y0-h-3,22,'ENB',BLUE,'center')
        text(lab,xx+3,671,22,'EN',align='center')
    text('合成响应长度（字符）',639,685,22,color=MUTED,align='center')
    box(447,694,5,5,BLUE);text('完整负载',457,699,23)
    box(550,694,5,5,TEAL);text('紧凑提交：406 B',560,699,23)
    text('五项绑定：状态根 / 输出哈希 / 证明哈希 / DA 指针 / DA 根',445,714,21,color=MUTED)

    panel(26,736,383,244,'04','恢复带来的仲裁连续性','超时设为 2 秒；合成异常场景，每条路径 100 个样本。')
    text('超时后挑战完成率',40,793,29,'CNB')
    text('无恢复',40,817,27)
    box(110,805,235,14,LIGHT);line(110,804,110,820,AMBER,1.2)
    text('0%',386,817,30,'ENB',AMBER,'right')
    text('有恢复',40,842,27)
    box(110,830,235,14,TEAL)
    text('100%',396,842,30,'ENB',TEAL,'right')
    text('两条路径的超时检测率均为 100%；检测不等于完成仲裁。',40,861,22,color=MUTED)
    line(40,874,395,874)
    text('定位轮次与 log2(n) 一致',40,890,28,'CNB')
    # Tiny line chart communicates scaling without an extra dense table.
    xs=[72+i*58 for i in range(6)]; ys=[939-(r['avg_bisection_rounds']-2)*6.8 for r in S['challenge_summary']]
    line(65,942,375,942)
    for i,(xx,yy,r) in enumerate(zip(xs,ys,S['challenge_summary'])):
        if i:line(xs[i-1],ys[i-1],xx,yy,BLUE,1.1)
        C.setFillColor(BLUE);C.circle(*xy(xx,yy),1.6*MM,fill=1,stroke=0)
        text(str(int(r['avg_bisection_rounds'])),xx,yy-5,23,'ENB',BLUE,'center')
        text(str(r['trace_steps']),xx,955,22,'EN',align='center')
    text('轨迹步数 n（各配置 100 次，共 600 次）',216,970,22,color=MUTED,align='center')

    panel(432,736,383,244,'05','DA 路径与成本摊销模型','模型估算；响应长度 8192，提示长度 64；各配置 100 个样本。')
    r=next(v for v in S['cost_summary'] if v['payload_size']==8192 and v['prompt_length']==64 and v['batch_size']==1)
    text('批大小 = 1 的平均模型成本（gas 等价值）',446,794,25,'CNB')
    profiles=[('全量 calldata','avg_full_onchain_calldata_amortized_gas',BLUE),
              ('紧凑 + 外部 DA','avg_compact_external_da_amortized_gas',MUTED),
              ('紧凑 + 类 EIP-4844','avg_compact_eip4844_like_amortized_gas',AMBER),
              ('紧凑 + 模块化采样','avg_compact_modular_da_sampling_amortized_gas',TEAL)]
    for i,(name,key,col) in enumerate(profiles):
        yy=812+i*20
        text(name,446,yy+8,23)
        box(610,yy,125*r[key]/r[profiles[0][1]],10,col)
        text(f'{r[key]:,.0f}',798,yy+8,24,'ENB',col,'right')
    text('批大小 1000：801.10 → 29.03（全量 → 模块化采样）',446,900,23,'CNB',TEAL)
    line(446,910,801,910)
    text('C_total = C_commit + C_DA + p_challenge × C_challenge',446,926,23,'EN')
    text('C_amortized = C_total / batch_size',446,941,25,'ENB',TEAL)
    para('DA 单价设为 2.2 / 0.9 / 0.45 gas 等价值/字节。脚本将固定总负载成本除以批大小；该趋势不证明固定单笔负载下的真实批处理收益。',446,957,352,21,10,color=MUTED)

    # Evidence table and limits are visible parts of the poster, rather than hidden disclaimers.
    box(26,996,789,166,WHITE,RULE,3)
    text('故障分类与验证边界',40,1021,34,'CNB')
    text('8 类故障场景，共 800 个合成样本；每类 100 个。',40,1038,23,color=MUTED)
    tablex=[40,256,319,402,480]
    box(40,1046,460,14,PALE)
    for s,x in zip(['场景','检测率','挑战完成','SLASHED*'],tablex):text(s,x+2,1056,22,'CNB')
    table=[('正常路径','0%','0%','0%'),('证明无效 / DA 缺失 / DA 证明损坏','100%','0%','0%'),
           ('响应篡改 / 轨迹长度不匹配','100%','100%','100%'),
           ('超时，无恢复','100%','0%','0%'),('超时，有恢复','100%','100%','100%')]
    for i,row in enumerate(table):
        yy=1073+i*14
        if i%2==0:box(40,yy-10,460,14,LIGHT)
        for s,x in zip(row,tablex):text(s,x+2,yy,21,'CN' if x==40 else 'EN')
    text('* 原型罚没状态标记，未证明实际资金罚没；正常样本为 PENDING。',40,1150,20,color=MUTED)
    line(518,1012,518,1151)
    text('本地 EVM 实测',535,1023,29,'CNB',TEAL)
    text('step  93,807  |  recover  156,891 gas',535,1042,24,'ENB')
    text('恢复 / 单轮步骤 ≈ 1.67；3 组负载实测。',535,1058,23)
    text('Sepolia：Chain ID 11155111',535,1075,23)
    text('部署区块 10825904（已有部署记录）。',535,1090,23)
    para('当前证据：模拟 TEE、可验证 DA 注册表、合成负载与本地 EVM。尚未验证真实 TEE / DA、公网费用及生产吞吐。',535,1110,263,23,12,color=MUTED)
    text('结论：轻量提交保留证据入口，可恢复路径让超时争议继续推进。',26,1171,27,'CNB',TEAL)
    text('依据：论文 §3-5；既有成本、挑战、故障与 EVM 实验记录。',815,1171,18,color=MUTED,align='right')

if __name__ == '__main__':
    OUT.mkdir(parents=True,exist_ok=True);TMP.mkdir(parents=True,exist_ok=True)
    results=[]
    for bleed in [0,3]:
        file,log=make(bleed)
        # Header/footer annotations are also checked against the 15 mm trim safety zone.
        unsafe=[t for t in log if t['x_mm']<15 or t['x_mm']+t['width_mm']>826 or t['baseline_y_mm']>1174]
        results.append({'file':str(file),'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
                        'canvas_mm':[841+2*bleed,1189+2*bleed],'trim_mm':[841,1189],
                        'font_min_pt':min(t['font_pt'] for t in log),'unsafe_text':unsafe})
    (OUT/'qa_checks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print(json.dumps(results,ensure_ascii=False,indent=2))
