"""Validate packaged data, print geometry, fonts, bounds and input preservation."""
from pathlib import Path
import csv, json, hashlib, statistics, math
from collections import defaultdict
from pypdf import PdfReader
import pdfplumber
from PIL import Image

HERE=Path(__file__).resolve().parent
OUT=HERE.parent
ROOT=OUT.parent
DATA=HERE/'data'
MM=72/25.4
def rows(name):return list(csv.DictReader((DATA/name).open()))
def close(a,b):return math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-6)
def mean(rs,key):return statistics.mean(float(r[key]) for r in rs)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

summary=json.loads((DATA/'summary.json').read_text())
cost=rows('cost_grid.csv');challenge=rows('challenge_grid.csv');failure=rows('failure_scenarios.csv')
cost_by=defaultdict(list)
for r in cost:cost_by[(int(r['payload_size']),int(r['prompt_length']),int(r['batch_size']))].append(r)
for s in summary['cost_summary']:
    r=cost_by[(s['payload_size'],s['prompt_length'],s['batch_size'])]
    assert len(r)==s['samples']==100
    for key in ['full_bytes','compact_bytes']:
        assert close(mean(r,key),s['avg_'+key])
    for name in ['full_onchain_calldata','compact_external_da','compact_eip4844_like','compact_modular_da_sampling']:
        assert close(mean(r,name+'_amortized_gas'),s['avg_'+name+'_amortized_gas'])
        assert close(mean(r,name+'_reduction_ratio'),s['avg_'+name+'_reduction_ratio'])
for s in summary['challenge_summary']:
    rs=[r for r in challenge if int(r['trace_steps'])==s['trace_steps']]
    assert len(rs)==100 and close(mean(rs,'bisection_rounds'),s['avg_bisection_rounds'])
    assert close(s['avg_bisection_rounds'],math.log2(s['trace_steps']))
for s in summary['failure_summary']:
    rs=[r for r in failure if r['scenario']==s['scenario']]
    assert len(rs)==100
    for raw,key in [('detected','detection_rate'),('challenge_success','challenge_success_rate')]:
        assert close(sum(r[raw]=='True' for r in rs)/len(rs),s[key])
    assert close(sum(r['final_status']=='SLASHED' for r in rs)/len(rs),s['slashed_rate'])
normal=[r for r in failure if r['scenario']=='normal']
assert all(r['final_status']=='PENDING' for r in normal)
gasrows=rows('measured_gas.csv');gas=json.loads((DATA/'measured_gas_summary.json').read_text())
for key,value in gas['averages'].items():assert close(mean(gasrows,key),value)
sepolia=json.loads((DATA/'sepolia.json').read_text());index=json.loads((DATA/'sepolia_address_index.json').read_text())
assert sepolia['chainId']==index['chainId']==11155111
assert sepolia['deployedAtBlock']==index['exportedAtBlock']==10825904
for value in index['contracts'].values():assert value['address']==sepolia['contracts'][value['alias']]

file=OUT/'NDBC2026_P00145_Poster_Final_Print.pdf'
pdf=PdfReader(file);assert len(pdf.pages)==1;page=pdf.pages[0]
expected={'MediaBox':[0,0,847,1195],'BleedBox':[0,0,847,1195],'TrimBox':[3,3,844,1192]}
boxes={}
for name,exp in expected.items():
    actual=[float(v)/MM for v in page['/'+name]]
    assert all(math.isclose(a,b,rel_tol=0,abs_tol=.001) for a,b in zip(actual,exp)),(name,actual)
    boxes[name]=[round(v,4) for v in actual]
fonts={}
for name,ref in page['/Resources']['/Font'].items():
    f=ref.get_object();desc=f.get('/FontDescriptor')
    assert desc and '/FontFile2' in desc.get_object(),name
    fonts[str(name)]={'base_font':str(f['/BaseFont']),'embedded':True}
operations=page.get_contents().get_data().decode('latin1')
assert ' rg' not in operations and ' RG' not in operations
assert ' k' in operations and ' K' in operations
assert not page['/Resources'].get('/XObject')
assert '/OutputIntents' not in pdf.trailer['/Root'] # Explicitly not certified PDF/X.
with pdfplumber.open(file) as doc:
    chars=doc.pages[0].chars;txt=doc.pages[0].extract_text()
    margins=[min(c['x0'] for c in chars)/MM-3,min(c['top'] for c in chars)/MM-3,
             844-max(c['x1'] for c in chars)/MM,1192-max(c['bottom'] for c in chars)/MM]
    assert min(margins)>=15,(margins,'unsafe text')
    for term in ['杨帆','华东师范大学','P00145','96.33%','406 B','READY','SLASHED','801.21','801.10','93,807','156,891']:
        assert term in txt,term
    assert '\ufffd' not in txt
    (OUT/'qa/final_extracted_text.txt').write_text(txt)
assert file.stat().st_size<20_000_000
layout_file=max((OUT/'qa').glob('revision_*_text_layout.json'),key=lambda p:int(p.name.split('_')[1]))
layout=json.loads(layout_file.read_text());bounds=[];offset=0
for block in layout:
    cs=chars[offset:offset+len(block['text'])];offset+=len(block['text'])
    assert ''.join(c['text'] for c in cs)==block['text']
    bounds.append(dict(text=block['text'],left=min(c['x0'] for c in cs),right=max(c['x1'] for c in cs),
                       top=min(c['top'] for c in cs),bottom=max(c['bottom'] for c in cs)))
assert offset==len(chars)
collisions=[]
for i,a in enumerate(bounds):
    for b in bounds[i+1:]:
        dx=min(a['right'],b['right'])-max(a['left'],b['left'])
        dy=min(a['bottom'],b['bottom'])-max(a['top'],b['top'])
        if dx>.5 and dy>.5:collisions.append(dict(a=a['text'],b=b['text'],overlap_pt=[dx,dy]))
(OUT/'qa/Text_Overlap_Check.json').write_text(json.dumps({'collision_count':len(collisions),'collisions':collisions},ensure_ascii=False,indent=2))
assert not collisions,collisions
manifest=json.loads((OUT/'qa/input_manifest.json').read_text())
preservation={}
for rel,oldhash in manifest.items():
    original=ROOT/rel
    if original.exists():
        assert digest(original)==oldhash,('original changed',rel)
        preservation[rel]=True
preview=OUT/'NDBC2026_P00145_Poster_Preview.png'
image=Image.open(preview);assert image.width>=5000 and image.height>=7000
report={'page_count':1,'pdf_size_bytes':file.stat().st_size,'sha256':digest(file),'boxes_mm':boxes,
        'embedded_fonts':fonts,'text_safe_margins_mm':[round(v,3) for v in margins],
        'min_text_font_pt':min(c['size'] for c in chars),
        'cmyk_vector':True,'raster_objects':0,'icc_output_intent':False,'pdfx_certified':False,
        'preview_pixels':list(image.size),'preview_dpi':list(image.info.get('dpi',[])),
        'source_data_rows':{'cost':len(cost),'challenge':len(challenge),'failure':len(failure),'gas':len(gasrows)},
        'all_source_numbers_recomputed':True,'originals_unchanged':preservation,
        'text_block_collision_count':len(collisions),
        'limitations':['No printer-specific ICC profile or contract proof.','No physical 1-2 metre viewing test.',
                       'Sepolia checked against local records and address index; no independent chain receipt validation.']}
(OUT/'qa/Print_Validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
