"""Record-driven application gallery and compact evidence/assumption catalogue."""
from collections import Counter
from datetime import datetime
import html
import json
import gzip
import base64
from pathlib import Path

from ..v3.core import fingerprint, solve
from .figures import render_case, Drawing, Canvas


def esc(x):return html.escape(str(x))
def bullet(items):return '<ul>'+''.join('<li>'+esc(i)+'</li>' for i in items)+'</ul>' if items else 'None recorded.'

def behavior(record, scenario, child):
    f=scenario['family']['local'][child]; table=scenario['family']['models'][0][child]
    rows=f['rows']; inputs=f['inputs']; lookup={tuple(row):out for row,out in zip(rows,table)}
    effects={}
    for i,parent in enumerate(inputs):
        changes=[]
        for row,out in zip(rows,table):
            if row[i]!=0:continue
            hi=list(row);hi[i]=1;new=lookup[tuple(hi)]
            if new!=out:changes.append({'context':dict(zip(inputs,row)),'before':out,'after':new})
        effects[parent]=changes
    return {'inputs':inputs,'rows':rows,'outputs':table,'effects':effects}


def public_ref(ref):
    import hashlib
    r={k:v for k,v in ref.items() if k!='quote'}
    if 'quote' in ref:r['quote_sha256']=hashlib.sha256(ref['quote'].encode()).hexdigest()
    return r


def accounting(root):
    import ast
    folder=Path(root)/'runs/application_v4_20261013';calls=[]
    for p in sorted((folder/'qwen').glob('*/pass*.json')):
        r=json.loads(p.read_text());usage=r.get('raw',{}).get('usage',{})
        calls.append({'case':r['case'],'file':str(p.relative_to(root)),'seconds':r['elapsed_seconds'],
            'prompt_tokens':usage.get('prompt_tokens',0),'generated_tokens':usage.get('completion_tokens',0),
            'json_valid':r.get('parsed') is not None,'transport_error':r.get('error'),
            'repair':'repair' in p.stem,'request_sha256':r.get('request_sha256')})
    window=json.loads((folder/'service_window.json').read_text());stop=json.loads((folder/'service_stop.json').read_text())
    launch_line=next(line for line in (folder/'v4_model_server.log').read_text().splitlines() if 'non-default args: ' in line)
    actual_launch=ast.literal_eval(launch_line.split('non-default args: ',1)[1])
    samples=[json.loads(s) for s in (folder/'gpu_samples.jsonl').read_text().splitlines()]
    # The campaign watchdog also logs unit-free three-column samples. Keep one
    # service-watchdog series for integration; never double-count interleaving.
    samples=[s for s in samples if 'MiB' in s['sample']]
    peak=max(int(s['sample'].split(' MiB')[0]) for s in samples)
    weighted=0
    for a,b in zip(samples,samples[1:]):
        seconds=(datetime.fromisoformat(b['at'])-datetime.fromisoformat(a['at'])).total_seconds()
        weighted+=min(20,seconds)*float(a['sample'].split(',')[1].strip(' %'))/100
    return {'calls':calls,'requests':len(calls),'valid_json':sum(c['json_valid'] for c in calls),
        'repairs':sum(c['repair'] for c in calls),'generated_tokens':sum(c['generated_tokens'] for c in calls),
        'server_generated_tokens':stop['generated_tokens'],'prompt_tokens':sum(c['prompt_tokens'] for c in calls),
        'request_seconds':sum(c['seconds'] for c in calls),
        'service_seconds':(datetime.fromisoformat(stop['at'])-datetime.fromisoformat(window['started_at'])).total_seconds(),
        'peak_vram_mib':peak,'sampled_utilization_weighted_seconds':weighted,'service':window,'stop':stop,
        'actual_server_arguments':actual_launch,'codex_tokens':None,'codex_served_build':None,'billing_cost':None}


def render(root, records, usage, render_figures=True):
    root=Path(root);out=root/'results/v4';out.mkdir(parents=True,exist_ok=True)
    config=json.loads((root/'configs/v4_campaign.json').read_text()); byid={r['case']:r for r in records}
    if render_figures:
        (root/'figures/v4').mkdir(parents=True,exist_ok=True)
        Drawing.portfolio=Canvas(str(root/'figures/v4/PORTFOLIO.pdf'),pageCompression=1,invariant=1)
    allfigs=[];attempts=[]
    for i,c in enumerate(config['cases']):
        r=byid.get(c['id'])
        if r is None:
            attempts.append({'case':c['id'],'status':'unavailable','nodes':0,'edges':0,'scenarios':0,'questions':0});continue
        r['scope']=c
        figures=render_case(root,r,i) if render_figures else json.loads((root/'runs/application_v4_20261013'/c['id']/'figures.json').read_text())
        folder=root/'runs/application_v4_20261013'/c['id'];folder.mkdir(parents=True,exist_ok=True)
        (folder/'figures.json').write_text(json.dumps(figures,separators=(',',':')))
        allfigs.extend(figures)
        attempts.append({'case':c['id'],'status':r['status'],'nodes':len(r['representation']['variables']),
            'edges':len(r['representation']['edges']),'scenarios':len(r['scenarios']),'questions':len(r['queries']),
            'direction_status':dict(Counter(e['status'] for e in r['representation']['edges'])),
            'partial_coverage':r['partial_family']['coverage'],
            'partial_cartesian_size':r['partial_family'].get('cartesian_size_within_local_candidates'),
            'unresolved_answers':sum(not q['partial_result']['identified'] for q in r['queries']),
            'scenario_disagreements':sum(len({tuple(s['result']['values']) for s in q['conditional']})>1 for q in r['queries'])})
    if Drawing.portfolio is not None:
        Drawing.portfolio.setTitle('GoT-war v4: eighteen application views');Drawing.portfolio.save();Drawing.portfolio=None
    if render_figures:
        from PIL import Image, ImageDraw
        sheet=Image.new('RGB',(1500,2400),'white');pen=ImageDraw.Draw(sheet)
        for i,f in enumerate(allfigs):
            preview=Image.open(root/'figures/v4'/(f['stem']+'.png')).convert('RGB')
            preview.thumbnail((475,365));x=(i%3)*500+(500-preview.width)//2;y=(i//3)*400+25
            sheet.paste(preview,(x,y));pen.text(((i%3)*500+10,(i//3)*400+6),str(f['number'])+' '+f['case']+' / '+f['view'],fill='#203744')
        sheet.save(root/'figures/v4/contact_sheet.png')
    stats={'attempts':attempts,'figure_count':len(allfigs),'figures':allfigs,'usage':usage,'independent_review':'pending',
        'queries_selected_before_execution':True,'old_test_set_used':False,'case_independence':False,'counterfactual_gold':None}
    concise=dict(stats,usage={k:v for k,v in usage.items() if k not in ('calls','service')},
        figures={c['id']:[f['number'] for f in allfigs if f['case']==c['id']] for c in config['cases']})
    (out/'summary.json').write_text(json.dumps(concise,separators=(',',':'),ensure_ascii=False)+'\n')
    table=['| Case | Nodes / edges | Conditional SCMs | Questions | Scenario disagreements |','|---|---:|---:|---:|---:|']
    for a in attempts:table.append('| '+a['case']+' | %s / %s | %s | %s | %s |'%(a['nodes'],a['edges'],a['scenarios'],a['questions'],a.get('scenario_disagreements','—')))
    disagreements=sum(a.get('scenario_disagreements',0) for a in attempts)
    totalq=sum(a['questions'] for a in attempts);unknown=sum(a.get('unresolved_answers',0) for a in attempts)
    totalnodes=sum(a['nodes'] for a in attempts);totaledges=sum(a['edges'] for a in attempts)
    report=f'''# Version 4 Game of Thrones portfolio

[Open the numbered gallery and mechanism catalogue](GALLERY.html). The SVG/PDF figures are in [figures/v4](../../figures/v4/); local PNG previews regenerate from the PDFs. [Independent-review packet](REVIEW_PACKET.md); [method and reproduction](../../docs/V4_METHOD.md).

**{len(records)} of {len(config['cases'])} case scopes completed**, with {totalnodes} variable records, {totaledges} edge records and {len(allfigs)} distinct figure views. Each case retains a partial mechanism family and two explicitly assumed executable SCMs. There are no evidence-identified complete literary SCMs. All {unknown}/{totalq} selected answers remain unresolved under the partial families; {disagreements} questions distinguish the two declared scenarios. These are targeted sensitivity examples, not independent statistical samples or an accuracy estimate.

{chr(10).join(table)}

The portfolio improves explanatory inspection: allegations differ from facts, mobilization from assembled forces, permission from crossing, preparation from ambush, and encirclement from its later persistence. Every displayed edge has a specific process phrase, evidence status and a catalogue entry. Local truth tables expose exactly which additional assumptions produce the conditional answers. This is a demonstrated representation and execution capability, not independently established narrative causal discovery.

The Stark–Lannister outcome is narrowed to Tywin's documented field-army order. The northern coalition outcome is the assembled host's negotiated crossing with Frey aid. Blackwater concerns repelling Stannis's assault; the Red Wedding concerns the gathered royal coalition, not all northern resistance. Bolton concerns military capture of Winterfell. Astapor concerns immediate defeat and departure with freed troops, not durable governance. These related cases overlap and are not independent observations.

**Paper shortlist:** 08 (wildfire joint mechanism), 11 (Red Wedding preparation and exposure), 14 (relief inhibits persistent encirclement), 15 (joint-intervention sensitivity), 16 (Astapor overview), and 17 (recognized command plus implemented order). Figures 14 and 15 form a complementary pair. Selection reflects specificity, source visibility, mathematical consistency and layout, not a claim that selected cases establish general accuracy. Full overviews remain in the gallery; the detail views are easier to use at column width.

**Inference and generation.** Qwen3-14B-AWQ ran on the newly authorized RTX 4090: {usage['requests']} requests, {usage['generated_tokens']:,} generated and {usage['prompt_tokens']:,} prompt tokens; {usage['valid_json']} responses parsed as JSON. The {usage['repairs']} repairs are retained alongside the initial failures. Summed request wall time was {usage['request_seconds']/60:.1f} minutes; service residency was {usage['service_seconds']/60:.1f} minutes; peak sampled VRAM was {usage['peak_vram_mib']:,} MiB. Sampled utilization-weighted time was {usage['sampled_utilization_weighted_seconds']/60:.1f} minutes, not billed GPU time. The server count was {usage['server_generated_tokens']:,.0f} generated tokens. The service stopped early after these passes, below both 150,000 tokens and two hours. Current Codex read explicit packets, generated the final representations/scenarios, revised proposals and reviewed them. Its exact served build, token usage and billing are unavailable. The final models are hybrid, assistant-mediated hypotheses, not autonomous Qwen outputs or a v3 A/B/C replication.

**Failures and limitations.** Initial Blackwater responses exhausted the output allowance and failed JSON parsing. A smaller per-pass output schema repaired formatting, not interpretation. Inspected errors include Tyrion/Bronn role confusion, an overclaim of total fleet destruction, Edmure/Robb wedding confusion, and Meereen events imported into the Bolton scope. Astapor's proposed water-offer-to-negotiation link lacks support and was retracted. These examples are an error inventory, not a blinded error-rate assessment. Initial GPU access on the old pod remained broken; the user supplied a replacement. The new project environment worked. An initial watchdog launch lacked a module path; an absolute-path relaunch supplied working identity-checked supervision.

Source access succeeded for 41 episode pages and 924 scene containers, but one unofficial transcription family is not independent corroboration. Some containers merge locations. Source assertions, contextual inferences and exact functions remain distinct; contextual labels are fallible Codex judgments awaiting researcher review. No support rubric was loosened to create nonzero path weights: v1/v2 zero-weight findings remain preserved. V4 does not claim a source-ranking or path-attribution benefit and does not add an attribution experiment. It also does not complete the unrun v3 comparison, estimate causal probabilities, or measure reader comprehension.

The evidence-only implementation fixes factual input rows but leaves other rows free within the declared graph/domain/background. Every local family is exhaustive; the global products exceed the 512-candidate cap. Each reported binary outcome set is certified by retained 0 and 1 witnesses, not by interpreting a sampled singleton as identification. Scenario agreement is only agreement under the stated extra assumptions.

**Next experiment:** independently adjudicate the six shortlisted views, especially Sansa's inferred communication, Frey risk protection, command recognition, and the necessity of relief or dragon fire. Freeze the resulting partial constraints before a source-matched, application-focused comparison of autonomous synthesis versus targeted mechanism revision. Assess source entailment and description/function contradictions before any reader study. The current manuscript can gain an exploratory application portfolio; a validated application-success claim remains unsupported. Prior controlled methods/failure-analysis findings are unchanged.
'''
    (out/'RESULTS.md').write_text(report)
    head='''<!doctype html><html lang="en"><meta charset="utf-8"><title>GoT-war v4 application gallery</title><style>body{font:16px/1.45 system-ui,sans-serif;color:#203744;margin:2rem auto;max-width:1100px;padding:0 1rem}a{color:#176c75}figure{margin:1rem 0;border:1px solid #ccd9df;padding:1rem}figure img{display:block;max-width:100%;max-height:800px;margin:auto}figcaption{margin-top:1rem}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #d4dce1;padding:.4rem;text-align:left;vertical-align:top}details{padding:.7rem;margin:.7rem 0;background:#f6f8fa}summary{cursor:pointer;font-weight:600}code{overflow-wrap:anywhere}h2{border-top:2px solid #247b77;padding-top:1rem}.pending{background:#fff3da;padding:1rem}@media print{details{display:block}figure{break-inside:avoid}nav{display:none}}</style><h1>Six conflicts: mechanisms, assumptions and consequences</h1><p class="pending">Exploratory generated television interpretations. Complete functions are assumed scenarios. Independent researcher review is pending. All selected questions remain unresolved in the broader partial families.</p><nav><a href="RESULTS.md">Results</a> · <a href="REVIEW_PACKET.md">Review packet</a> · <a href="../../docs/V4_METHOD.md">Method</a> · <a href="../../figures/v4/contact_sheet.png">Local contact sheet</a></nav>'''
    parts=[head,'<h2>Case comparison and attempted-case register</h2><table><tr><th>Case</th><th>Outcome boundary</th><th>Nodes / edges</th><th>Status / uncertainty</th></tr>']
    for c,a in zip(config['cases'],attempts):parts.append('<tr><td><a href="#'+c['id']+'">'+esc(c['title'])+'</a></td><td>'+esc(c['outcome'])+'</td><td>'+str(a['nodes'])+' / '+str(a['edges'])+'</td><td>'+esc(a['status'])+'; '+str(a.get('unresolved_answers',0))+' unresolved questions</td></tr>')
    parts.append('</table><p>Overlap: A/B share S01 political and military context; B/D concern the same Frey alliance at different endpoints; C/D share Lannister strategy; E follows the earlier northern collapse; D/F share episodes but distinct locations. No case-level confidence interval is justified.</p>')
    parts.append('<p>Shared legend: teal = direct process evidence; ochre = contextual inference; dashed purple = hypothesis. Tan nodes are fixed boundary inputs, blue nodes endogenous and green nodes the outcome. Event/report/belief types, source support and exact functional assumptions are in the catalogue. Edge IDs are local to each case. All 0 states mean absence of the specifically defined event by the stated endpoint, not an unspecified opposite.</p>')
    for c in config['cases']:
        if c['id'] not in byid:continue
        r=byid[c['id']];rep=r['representation'];parts.append('<h2 id="'+c['id']+'">'+esc(c['title'])+'</h2><p><b>'+esc(c['outcome'])+'</b> '+esc(c['boundary'])+'</p><p>'+esc(c['interval'])+'</p>')
        for fig in [f for f in allfigs if f['case']==c['id']]:
            base='../../figures/v4/'+fig['stem'];parts.append('<figure id="figure-'+str(fig['number'])+'"><a href="'+base+'.svg"><img loading="lazy" src="'+base+'.svg" alt="'+esc(fig['caption'])+'"></a><figcaption><b>Figure '+str(fig['number'])+'.</b> '+esc(fig['caption'])+' <a href="'+base+'.svg">SVG</a> · <a href="'+'../../figures/v4/PORTFOLIO.pdf#page='+str(fig['number'])+'">portfolio PDF page</a> · <a href="'+base+'.pdf">local PDF</a> · <a href="'+base+'.png">local PNG</a></figcaption></figure>')
        # Unique exact locations, no republished full passages or repeated excerpts.
        refs={}; ids={}
        for obj in rep['variables']+rep['edges']+rep['mechanisms']:
            for ref in obj.get('evidence',[]):
                key=(ref['passage_id'],ref['start'],ref['end'],ref['supports'])
                if key not in refs:refs[key]=ref;ids[key]='r'+str(len(ids)+1)
        def links(obj):
            return ', '.join('<a href="#'+c['id']+'-'+ids[(x['passage_id'],x['start'],x['end'],x['supports'])]+'">'+ids[(x['passage_id'],x['start'],x['end'],x['supports'])]+'</a>' for x in obj.get('evidence',[]))
        parts.append('<details><summary>Variable catalogue: meaning, actor, time and factual state</summary><table><tr><th>ID / event</th><th>Operational meaning</th><th>Actor / kind / boundary</th><th>Event / statement rank; factual state</th><th>Evidence</th></tr>')
        for v in rep['variables']:parts.append('<tr><td>'+esc(v['id']+' / '+v['label'])+'</td><td>'+esc(v['definition'])+'</td><td>'+esc(v['actor']+'; '+v['kind']+'; '+v['boundary'])+'</td><td>'+esc(str(v['event_time'])+' / '+str(v['statement_time'])+'; '+str(v['factual']))+'</td><td>'+links(v)+'</td></tr>')
        parts.append('</table><p>Episode ranks provide an ordering, not elapsed time. Fractional ranks are model ordering conventions; offscreen events have uncertain exact dates. A later report is separated from its earlier attributed event. All domains are {0,1}.</p></details>')
        parts.append('<details><summary>Edge catalogue: process, support, conditions and limits</summary>')
        for e in rep['edges']:
            parts.append('<p id="'+c['id']+'-'+e['id']+'"><b>'+esc(e['id']+' '+e['parent']+' → '+e['child']+' | '+e['label'])+'</b> ['+esc(e['status'])+'] '+esc(e['process'])+' '+links(e)+'</p>')
            parts.append('<p>'+esc('Conditions: '+('; '.join(e['conditions']) or 'Only the declared case context.'))+' '+esc('Qualifications/gaps: '+('; '.join(e['qualifications']+e['gaps']) or 'No additional edge-specific gap recorded; complete function still assumed.'))+'</p>')
            if e['alternatives']:parts.append('<p>Alternatives: '+esc('; '.join(e['alternatives']))+'</p>')
        parts.append('<p>Endpoint occurrence evidence is in the variable catalogue. No edge status is a causal probability. No independent contradicting source was acquired; empty contradiction lists do not establish absence of contrary evidence. Context and source limitations remain in the case review notes below.</p></details>')
        parts.append('<details><summary>Joint mechanisms, exact truth tables and assumption register</summary>')
        for m in rep['mechanisms']:
            loc=r['partial_family']['local'][m['child']]
            parts.append('<h3>'+esc(m['id'])+'</h3><p>'+esc(m['description']+' '+m['joint_description'])+' '+links(m)+'</p><p>Partial: '+str(len(loc['rows'])-len(loc['unknown_rows']))+' observed row; '+str(len(loc['unknown_rows']))+' unknown rows; '+str(len(loc['tables']))+' compatible local functions. Global enumeration: '+esc(r['partial_family']['coverage'])+'.</p>')
            parts.append('<table><tr><th>Scenario</th><th>Explicit assumption</th><th>Input order; truth-table outputs</th><th>Functional parent behavior</th></tr>')
            for s in r['scenarios']:
                b=behavior(r,s,m['child']);f=next(f for f in s['family']['functions'] if f['child']==m['child']);ass=next(x['rationale'] for x in f['constraints'] if x['basis']=='assumption')
                effects=[]
                for p,changes in b['effects'].items():
                    signs=sorted({'positive' if z['after']>z['before'] else 'inhibitory' for z in changes})
                    effects.append(p+': '+('/'.join(signs) if signs else 'inactive')+' ('+str(len(changes))+' changing contexts)')
                parts.append('<tr><td>'+esc(s['label'])+'</td><td>'+esc(ass)+'</td><td><code>'+esc(','.join(b['inputs'])+'; '+' '.join(''.join(map(str,row))+':'+str(y) for row,y in zip(b['rows'],b['outputs'])))+'</code></td><td>'+esc('; '.join(effects))+'</td></tr>')
            parts.append('</table>')
        parts.append('<p>All extra table restrictions are assumptions, including fixed decisions and successful implementation. Tables exhaust the small declared input domains. An inactive edge in one scenario is retained visibly because another mechanism interpretation may use it. Each intervention replaces only its target equations and reuses every other table and fixed background.</p></details>')
        parts.append('<details><summary>Exact source locations and what each citation supports</summary><table><tr><th>Ref</th><th>Source / location</th><th>Support judgment</th></tr>')
        for key,ref in refs.items():
            rid=ids[key];loc=ref['source_location'];parts.append('<tr id="'+c['id']+'-'+rid+'"><td>'+rid+'</td><td><a href="'+esc(loc['url'])+'">'+esc(ref['passage_id'])+'</a>; scene characters '+str(ref['start'])+'–'+str(ref['end'])+'</td><td>'+esc(ref['supports'])+'</td></tr>')
        parts.append('</table><p>Offsets are within the normalized complete scene. Source and quote hashes are retained in the reproduction bundle. Full transcripts and surrounding context stay private; the linked unofficial transcription may change.</p></details>')
        parts.append('<details><summary>Generation revisions and unresolved review questions</summary>'+bullet(r['generation']['source_reading_notes'])+bullet([x.get('reason','') for x in r['generation']['revision_history']])+'<p>Current Codex source and semantic review is not independent adjudication. Review status: pending.</p></details>')
    parts.append('</html>');full=''.join(parts)
    # Lossless self-contained compression keeps the complete catalogue in the
    # public release without increasing the byte cap or external dependencies.
    payload=base64.b64encode(gzip.compress(full.encode(),mtime=0)).decode()
    (out/'GALLERY.html').write_text('<!doctype html><meta charset="utf-8"><title>GoT-war v4 gallery</title><h1>Game of Thrones application portfolio</h1><p>Opening 18 figures and the full mechanism catalogue. <a href="RESULTS.md">Results</a>. If this browser lacks gzip decompression, run <code>python3 scripts/v4_reproduce.py --expand-gallery</code> and open GALLERY_EXPANDED.html.</p><script id="portfolio-data" type="application/octet-stream">'+payload+'</script><script>const bytes=Uint8Array.from(atob(document.getElementById("portfolio-data").textContent),c=>c.charCodeAt(0));new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"))).text().then(s=>{document.open();document.write(s);document.close();});</script>')
    return stats


if __name__=='__main__':
    import sys
    root=Path(sys.argv[1]).resolve();cfg=json.loads((root/'configs/v4_campaign.json').read_text())
    records=[json.loads((root/'runs/application_v4_20261013'/c['id']/'validated.json').read_text()) for c in cfg['cases'] if (root/'runs/application_v4_20261013'/c['id']/'validated.json').exists()]
    print(json.dumps({k:v for k,v in render(root,records,accounting(root)).items() if k in ('attempts','figure_count')}))
