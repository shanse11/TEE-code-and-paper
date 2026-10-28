"""NDBC poster redesign. Uses only packaged data; no experiment/network runs."""
from pathlib import Path
import argparse, json, math, hashlib
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import CMYKColor
from pypdf import PdfReader, PdfWriter
from pypdf.generic import RectangleObject

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
CFG = json.loads((HERE/'config.json').read_text())
DATA = HERE/'data'
SUMMARY = json.loads((DATA/'summary.json').read_text())
GAS = json.loads((DATA/'measured_gas_summary.json').read_text())['averages']
DEPLOY = json.loads((DATA/'sepolia.json').read_text())
MM=72/25.4; B=3; H=1195
for name,path in CFG['fonts'].items():
    pdfmetrics.registerFont(TTFont(name,path,subfontIndex=CFG['chinese_subfont_index'] if name in ['CN','CNB'] else 0))
NAVY=CMYKColor(.94,.73,.4,.40)
INK=CMYKColor(.80,.60,.35,.40)
TEAL=CMYKColor(.92,.28,.55,.14)
BLUE=CMYKColor(.87,.48,.05,.12)
AMBER=CMYKColor(.03,.57,.96,.10)
MUTED=CMYKColor(.45,.32,.25,.45)
LIGHT=CMYKColor(.035,.02,.015,0)
PALE=CMYKColor(.075,.015,.045,0)
BLUEPALE=CMYKColor(.055,.035,0,0)
WARMPALE=CMYKColor(0,.045,.10,0)
RULE=CMYKColor(.18,.09,.07,.04)
WHITE=CMYKColor(0,0,0,0)
TEXT_LOG=[]; PANEL_LOG=[]
C=None

# Adapted from the preserved original build_poster.py vector helpers.
def xy(x,y):return ((x+B)*MM,(H-y-B)*MM)
def box(x,y,w,h,fill=WHITE,stroke=None,r=0):
    C.setFillColor(fill);C.setStrokeColor(stroke or fill);C.setLineWidth(.45*MM)
    p=xy(x,y+h)
    if r:C.roundRect(*p,w*MM,h*MM,r*MM,fill=1,stroke=int(stroke is not None))
    else:C.rect(*p,w*MM,h*MM,fill=1,stroke=int(stroke is not None))
def line(x1,y1,x2,y2,color=RULE,width=.5,dash=None):
    C.setStrokeColor(color);C.setLineWidth(width*MM);C.setDash(dash or [])
    C.line(*xy(x1,y1),*xy(x2,y2));C.setDash([])
def arrow(points,color=BLUE,dash=False):
    for p,q in zip(points,points[1:]):line(*p,*q,color,.85,[5,3] if dash else None)
    p,q=points[-2:];a=math.atan2(q[1]-p[1],q[0]-p[0]);s=3.4
    z=C.beginPath();z.moveTo(*xy(*q))
    z.lineTo(*xy(q[0]-s*math.cos(a-.47),q[1]-s*math.sin(a-.47)))
    z.lineTo(*xy(q[0]-s*math.cos(a+.47),q[1]-s*math.sin(a+.47)))
    z.close();C.setFillColor(color);C.drawPath(z,stroke=0,fill=1)
def text(s,x,y,size=28,font='CN',color=INK,align='left'):
    w=pdfmetrics.stringWidth(s,font,size)/MM
    if align=='center':x-=w/2
    elif align=='right':x-=w
    C.setFont(font,size);C.setFillColor(color);C.drawString(*xy(x,y),s)
    TEXT_LOG.append(dict(text=s,x_mm=x,y_mm=y,width_mm=w,size_pt=size,font=font))
    return w
def para(s,x,y,w,size=26,leading=11,font='CN',color=INK):
    st=''
    for ch in s:
        if ch=='\n' or (st and pdfmetrics.stringWidth(st+ch,font,size)>w*MM):
            text(st,x,y,size,font,color);y+=leading;st='' if ch=='\n' else ch
        else:st+=ch
    if st:text(st,x,y,size,font,color);y+=leading
    return y
def panel(x,y,w,h,num,title,sub):
    box(x,y,w,h,WHITE,RULE,r=2)
    text(num,x+11,y+22,32,'ENB',TEAL)
    text(title,x+35,y+22,38,'CNB')
    text(sub,x+11,y+39,24,color=MUTED)
    PANEL_LOG.append(dict(x=x,y=y,w=w,h=h,title=title))
def state(x,y,w,cn,en,col=BLUE):
    bg=BLUEPALE if col==BLUE else PALE if col==TEAL else WARMPALE
    box(x,y,w,43,bg,col,r=2)
    text(cn,x+w/2,y+17,30,'CNB',col,'center')
    text(en,x+w/2,y+33,22,'ENB',col,'center')
def point(x,y,col=BLUE):
    C.setFillColor(col);C.circle(*xy(x,y),1.9*MM,fill=1,stroke=0)
def mathrun(tokens,x,y,size=30,col=INK):
    """Editable vector math with conventional italic symbols and subscripts."""
    for normal,sub in tokens:
        x+=text(normal,x,y,size,'MATH',col)
        if sub:x+=text(sub,x,y+2.1,size*.70,'EN',col)
    return x
def row(payload,batch=1):
    return next(r for r in SUMMARY['cost_summary'] if r['payload_size']==payload and r['prompt_length']==64 and r['batch_size']==batch)

def header():
    box(-3,-3,847,1195,LIGHT)
    box(-3,-3,847,157,NAVY);box(-3,151,847,4,TEAL)
    text(CFG['conference'],24,24,29,'CNB',WHITE)
    text('POSTER PAPER  |  '+CFG['poster_id'],817,24,27,'ENB',WHITE,'right')
    text(CFG['title_line_1'],24,63,80,'CNB',WHITE)
    text(CFG['title_line_2'],24,100,80,'CNB',WHITE)
    text(CFG['author']+'  |  '+CFG['affiliation'],24,130,32,'CNB',WHITE)
    text(CFG['date_location'],817,143,26,'CN',WHITE,'right')
    box(24,163,793,49,PALE,r=2)
    text('核心结论  |  当前原型与配置化成本模型支持',35,175,25,'CNB',TEAL)
    text('轻量提交与可恢复挑战协同：正常路径降低链上负担，',35,191,40,'CNB',INK)
    text('异常路径保留证据入口，在证据可得时继续超时仲裁。',35,207,40,'CNB',INK)
    cards=[(24,'01  可恢复挑战','0% → 100%','指定合成超时场景的挑战完成率','超时 2 秒；两条路径各 100 个样本'),
           (294,'02  证据绑定提交','406 B','紧凑提交结构的平均字节数','规范 JSON；合成负载与模拟 TEE'),
           (564,'03  DA 感知成本','96.33%','指定配置下平均模型摊销成本降幅','逐样本降幅均值；非公网费用实测')]
    for x,title,big,label,condition in cards:
        box(x,221,253,92,WHITE,RULE,r=2)
        text(title,x+11,242,32,'CNB',TEAL)
        text(big,x+11,274,73,'CNB' if '→' in big else 'ENB',TEAL)
        text(label,x+11,292,26,'CNB')
        text(condition,x+11,306,24,color=MUTED)

def protocol():
    panel(24,329,480,236,'01','可恢复挑战：恢复活性，保留事实','Safety 与 Liveness 分离；恢复不是正确性裁决。论文 §4.1')
    xs=[38,114,190,266,342,418]
    states=[('已打开','OPEN'),('已响应','RESPONDED'),('二分定位','NARROWING'),('待重放','READY'),('已重放','REPLAYED'),('已结算','RESOLVED')]
    for x,(cn,en) in zip(xs,states):state(x,393,66,cn,en)
    for i in range(5):arrow([(xs[i]+66,414),(xs[i+1],414)],BLUE)
    for x,operation in zip(xs,['open','respond','step','单步证据','replay','resolve']):
        text(operation,x+33,384,23,'CN' if operation=='单步证据' else 'EN',BLUE,'center')
    state(147,464,105,'会话超时','TIMED_OUT',AMBER)
    state(320,464,113,'恢复推进','RECOVERED',TEAL)
    arrow([(209,436),(209,450),(199,450),(199,464)],AMBER,dash=True)
    text('交互超时',135,453,23,color=AMBER,align='right')
    arrow([(252,486),(320,486)],TEAL)
    text('观察节点 recover',287,475,22,color=TEAL,align='center')
    arrow([(376,464),(376,451),(237,451),(237,436)],TEAL)
    text('回到可推进状态，继续定位 / 重放',343,461,22,color=TEAL,align='center')
    mathrun([('Facts(cs','before'),(') = Facts(cs','after'),(')','')],38,529,32,TEAL)
    text('状态根、DA 根、负载哈希、执行轨迹与争议证据不被重写。',38,546,25)
    text('证据可检查时，原型重放比较预期 / 声明哈希；非通用 VM 或真实 ML 执行证明。',38,557,24,color=MUTED)

def architecture():
    panel(520,329,297,236,'02','系统与证据路径','TEE 为模拟环境；DA 为可验证注册表。§3')
    box(538,380,261,30,BLUEPALE,BLUE,r=2)
    text('高频 DApp 请求入口',668.5,399,29,'CNB',BLUE,'center')
    for x,y,w,cn,sub,col in [(538,436,111,'链下执行','模拟 TEE',BLUE),(688,436,111,'链上提交','紧凑承诺',BLUE),
                            (538,499,111,'DA 证据层','负载 + Merkle 证明',TEAL),(688,499,111,'挑战与仲裁','验证 / 重放 / 结算',AMBER)]:
        box(x,y,w,42,BLUEPALE if col==BLUE else PALE if col==TEAL else WARMPALE,col,r=2)
        text(cn,x+w/2,y+17,28,'CNB',col,'center')
        text(sub,x+w/2,y+33,23,'CN',col,'center')
    arrow([(593,410),(593,436)],BLUE)
    arrow([(649,455),(688,455)],BLUE)
    text('摘要',668,449,22,color=BLUE,align='center')
    arrow([(593,478),(593,499)],TEAL)
    text('发布',607,493,22,color=TEAL)
    arrow([(744,478),(744,499)],AMBER)
    text('争议',758,493,22,color=AMBER)
    arrow([(688,520),(649,520)],AMBER,dash=True)
    text('取证',668,513,22,color=AMBER,align='center')
    arrow([(649,539),(675,539),(675,470),(688,470)],TEAL,dash=True)
    text('绑定',668,549,22,color=TEAL,align='center')
    text('蓝：正常提交  绿：证据发布/绑定  橙：异常取证',535,558,22,color=MUTED)

def recovery_experiments():
    panel(24,581,480,228,'03','仲裁连续性的两项实验','RQ3：合成挑战原型，超时 2 秒。论文 §5.3')
    text('A  超时后挑战完成率',38,639,30,'CNB')
    text('B  二分定位轮次',269,639,30,'CNB')
    line(252,629,252,789)
    text('无恢复',38,669,27)
    box(104,658,107,14,LIGHT);line(104,657,104,674,AMBER,1)
    text('0%',240,670,32,'ENB',AMBER,'right')
    text('有恢复',38,705,27)
    box(104,693,107,14,TEAL)
    text('100%',240,705,32,'ENB',TEAL,'right')
    para('两组均检测到超时；\n仅恢复组完成后续挑战。',38,736,199,27,13)
    text('各 100 次；不是生产成功率保证。',38,782,24,color=MUTED)
    x0=287;x1=482;y0=752;yt=663
    for v in [2,4,6]:
        yy=y0-(v-2)/5*(y0-yt);line(x0,yy,x1,yy)
        text(str(v),281,yy+2,23,'EN',MUTED,'right')
    rs=SUMMARY['challenge_summary']
    for i,r in enumerate(rs):
        xx=x0+i*(x1-x0)/5;yy=y0-(r['avg_bisection_rounds']-2)/5*(y0-yt)
        if i:line(px,py,xx,yy,BLUE,1)
        point(xx,yy);text(str(int(r['avg_bisection_rounds'])),xx,yy-5,24,'ENB',BLUE,'center')
        text(str(r['trace_steps']),xx,769,23,'EN',align='center');px,py=xx,yy
    text('轨迹步数 n（按 log2 间距）',383,786,24,color=MUTED,align='center')
    text('各配置 100 次，共 600 次；2-7 轮符合 log2(n)。',269,799,23,color=MUTED)

def compact_experiment():
    panel(520,581,297,228,'04','406 B 如何保留证据','RQ1：规范 JSON；模拟 TEE。论文 §4.2 / §5.1')
    text('绑定：状态根 · 输出哈希 · 证明哈希',537,638,24,'CNB',TEAL)
    text('DA 指针定位负载；DA Merkle 根承诺字段证明。',537,650,23)
    text('完整负载（kB，0-55）',537,666,25,'CNB',BLUE)
    x0=556;x1=797;yt=673;y0=720
    for v in [0,25,50]:
        yy=y0-v/55*(y0-yt);line(x0,yy,x1,yy);text(str(v),551,yy+2,22,'EN',MUTED,'right')
    for i,p in enumerate([128,512,2048,8192]):
        r=row(p);xx=x0+i*(x1-x0)/3;yy=y0-r['avg_full_bytes']/55000*(y0-yt)
        if i:line(px,py,xx,yy,BLUE,1)
        point(xx,yy);text(f"{r['avg_full_bytes']/1000:.2f}",xx,yy-5,24,'ENB',BLUE,'center');px,py=xx,yy
    text('紧凑提交（B，0-500）',537,741,25,'CNB',TEAL)
    y0=776;yt=751
    for v in [0,500]:
        yy=y0-v/500*(y0-yt);line(x0,yy,x1,yy);text(str(v),551,yy+2,21,'EN',MUTED,'right')
    yy=y0-406/500*(y0-yt);line(x0,yy,x1,yy,TEAL,1)
    for i,p in enumerate([128,512,2048,8192]):
        xx=x0+i*(x1-x0)/3;point(xx,yy,TEAL);text(str(p),xx,787,23,'EN',align='center')
    text('406 B',748,743,28,'ENB',TEAL,'center')
    text('响应长度（字符，对数间距）；提示长 64；各 100 次。',537,801,23,color=MUTED)

def cost_experiment():
    panel(24,825,793,183,'05','DA 成本：比较路径，区分总量与摊销','RQ2：响应长 8192、提示长 64；100 样本；gas 等价值为模型单位。§4.3 / §5.2')
    text('DA 路径',38,882,24,'CNB')
    text('总模型成本 b=1',439,882,23,'CNB',align='right')
    text('每份摊销 b=1000',559,882,23,'CNB',align='right')
    r=row(8192);full=r['avg_full_onchain_calldata_amortized_gas']
    profiles=[('全量 calldata','full_onchain_calldata'),('紧凑 + 外部 DA','compact_external_da'),
              ('紧凑 + 类 EIP-4844','compact_eip4844_like'),('紧凑 + 模块化 DA 采样','compact_modular_da_sampling')]
    for i,(name,k) in enumerate(profiles):
        v=r['avg_'+k+'_amortized_gas'];yy=896+i*22
        col=TEAL if i==3 else BLUE
        text(name,38,yy+9,26,'CNB' if i==3 else 'CN',col)
        box(218,yy,101*v/full,11,col)
        text(f'{v:,.2f}',439,yy+9,26,'ENB',col,'right')
        text(f'{v/1000:,.2f}',559,yy+9,26,'ENB',col,'right')
    line(577,874,577,992)
    mathrun([('C','total'),(' = C','commit'),(' + C','DA'),(' + p','challenge'),(' C','challenge')],593,887,30)
    mathrun([('C','amortized'),(' = C','total'),(' / b','')],593,906,30,TEAL)
    text('b：批大小；p：争议概率。',593,922,25)
    text('图中仅计提交 + DA；未加入争议项。',593,938,24)
    para('DA 单价为假设：2.2 / 0.9 / 0.45 gas 等价值/字节。固定总负载成本除以 b，不能据此推断真实吞吐收益。',593,954,210,24,11,color=MUTED)
    text('96.33% 为逐样本降幅均值；图示为成本均值。801.10 据原始网格，论文 801.21 差异见报告。',38,996,24,color=MUTED)

def evidence_footer():
    box(24,1024,520,138,WHITE,RULE,r=2)
    text('06',35,1046,32,'ENB',TEAL)
    text('故障结果矩阵',59,1046,38,'CNB')
    text('RQ4：8 类合成场景，每类 100 次，共 800 次。§5.4',35,1060,24,color=MUTED)
    cols=[38,327,409,487]
    box(36,1067,496,12,PALE)
    for s,x in zip(['场景','检测','完成挑战','SLASHED*'],cols):text(s,x,1076,23,'CNB')
    items=[('正常场景','normal'),('远程证明无效','attestation_invalid'),('DA 不可用','da_unavailable'),
           ('DA 证明无效','da_proof_invalid'),('响应篡改','response_tampered'),('轨迹长度不匹配','trace_length_mismatch'),
           ('超时，无恢复','challenge_timeout_no_recover'),('超时，有恢复','challenge_timeout_recover')]
    for i,(name,k) in enumerate(items):
        yy=1086+i*9.2
        if i%2==0:box(36,yy-7.1,496,9.2,LIGHT)
        r=next(r for r in SUMMARY['failure_summary'] if r['scenario']==k)
        text(name,38,yy,24)
        for x,key in zip(cols[1:],['detection_rate','challenge_success_rate','slashed_rate']):
            val=r[key];text(f'{val:.0%}',x+12,yy,23,'ENB',TEAL if val else MUTED,'center')
    text('* 状态标记，未证明资金罚没；正常记录为 PENDING。',38,1160,22,color=MUTED)
    panel(560,1024,257,138,'07','本地链上对应物','RQ5：Hardhat gas 实测与部署记录。§5.5')
    text('challengeStep',574,1081,24,'ENB',BLUE)
    text(f"{GAS['challenge_step_round1_gas']:,.0f}",800,1081,34,'ENB',BLUE,'right')
    text('challengeRecover',574,1103,24,'ENB',TEAL)
    text(f"{GAS['challenge_recover_gas']:,.0f}",800,1103,34,'ENB',TEAL,'right')
    text('gasUsed；恢复 / 单轮 step ≈ 1.67',574,1120,25)
    text('3 组负载；不能与 DA 模型成本混用。',574,1133,23,color=MUTED)
    text('Sepolia  Chain ID '+str(DEPLOY['chainId']),574,1146,24)
    text('部署区块 '+str(DEPLOY['deployedAtBlock'])+'（已有记录）',574,1159,24)
    text('验证边界：模拟 TEE、合成故障与配置化成本模型；真实 TEE / DA、公网费用与生产性能尚待验证。',24,1171,26,'CNB',TEAL)

def build(revision=1):
    global C
    OUT.mkdir(exist_ok=True);qa=OUT/'qa';qa.mkdir(exist_ok=True)
    raw=qa/f'revision_{revision}_raw.pdf'
    C=canvas.Canvas(str(raw),pagesize=(847*MM,1195*MM),pageCompression=1,
                    enforceColorSpace='CMYK',initialFontName='CN',initialFontSize=28)
    C.setTitle('NDBC 2026 P00145 | '+CFG['title_line_1']+' '+CFG['title_line_2'])
    C.setAuthor('杨帆 | 华东师范大学')
    C.setSubject('A0 portrait with 3 mm bleed; process CMYK vector poster; embedded fonts')
    for f in [header,protocol,architecture,recovery_experiments,compact_experiment,cost_experiment,evidence_footer]:f()
    C.showPage();C.save()
    writer=PdfWriter();writer.clone_document_from_reader(PdfReader(raw));page=writer.pages[0]
    page.trimbox=RectangleObject([3*MM,3*MM,844*MM,1192*MM])
    page.bleedbox=RectangleObject([0,0,847*MM,1195*MM]);page.cropbox=page.mediabox
    target=OUT/'NDBC2026_P00145_Poster_Final_Print.pdf'
    with target.open('wb') as fp:writer.write(fp)
    (qa/f'revision_{revision}_text_layout.json').write_text(json.dumps(TEXT_LOG,ensure_ascii=False,indent=2))
    (qa/'panel_layout.json').write_text(json.dumps(PANEL_LOG,ensure_ascii=False,indent=2))
    print(target)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--revision',type=int,default=1)
    build(ap.parse_args().revision)
