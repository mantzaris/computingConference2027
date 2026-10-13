"""Versioned catalogues, honest unavailable-inference report, and Graphviz figures."""
import copy
from datetime import datetime, timezone
import gzip
import hashlib
import html
import io
import json
from pathlib import Path
import subprocess
import tarfile
import textwrap
import xml.etree.ElementTree as ET

from ..budget import atomic_json
from .core import fingerprint, informative, query, verify_reported_result
from .study import RUN


def wrap(s, width=25):
    return '\n'.join(textwrap.wrap(str(s),width=width,break_long_words=False))


def q(s):
    return json.dumps(str(s),ensure_ascii=False)


def render(record, folder):
    """Render recorded prose only. This renderer never supplies a causal phrase."""
    rep=record['representation'];gate=record['display_gate'];ident=record.get('id',record.get('case'))
    offline=record.get('provenance')=='software-authored controlled fixture, not LLM output'
    stem=ident+('_'+record['arm'] if record.get('arm') in ('A','B','C') else '')
    chosen=set(gate.get('displayed_edges',[]));edges=[e for e in rep['edges'] if e['id'] in chosen]
    if any(not informative(e['label']) for e in edges):
        raise ValueError('Rendering refused an uninformative causal label')
    statuses=gate.get('display_status',{})
    ms={m['child']:m for m in rep['mechanisms']}
    trace=record.get('queries',[None])[0]
    worlds=trace['result'].get('worlds',[]) if trace else []
    intervention=trace.get('do',trace.get('alignment',{}).get('do',{})) if trace else {}
    lines=['digraph G {',
        'graph [rankdir=TB, bgcolor="white", pad="0.16", nodesep="0.28", ranksep="0.6", splines=polyline, fontname="DejaVu Sans", fontsize=12, labelloc=t, label='+q(
            ident.title()+(' · offline controlled contract example\nAuthored fixture; no new LLM inference or human review' if offline
                           else ' · generated mechanism hypothesis\nSame-model semantic review; independent adjudication pending')+
            ('\n'+trace['id']+': do '+str(intervention)+'; outcome set '+str(trace['result']['values']) if trace else ''))+'];',
        'node [shape=box, style="rounded,filled", fillcolor="#eef4f7", fontname="DejaVu Sans", fontsize=14, margin="0.12,0.08", color="#355568"];',
        'edge [fontname="DejaVu Sans", fontsize=12, arrowsize=0.7, penwidth=1.2];']
    for v in rep['variables']:
        values=sorted({w['counterfactual'][v['id']] for w in worlds},key=repr)
        shown=('{'+', '.join(map(str,values))+'}') if len(values)>1 else str(values[0]) if values else 'unknown'
        state=str(v['factual'])+(' → '+shown if values and values!=[v['factual']] else ' (unchanged)' if worlds else '')
        m=ms.get(v['id']);label=wrap(v['label'],18)+'\n'+v['id']+' · '+state
        if m and len(m['parents'])>1:label+='\nJoint mechanism '+m['id']
        elif m:label+='\nMechanism '+m['id']
        else:label+='\nBoundary input'
        fill='#e0eff1' if v['id']==rep['outcome'] else '#fbf1da' if v['boundary']=='fixed_context' else '#eef4f7'
        color='#6845a2' if v['id'] in intervention else '#986447' if len(values)>1 else '#355568'
        if len(values)>1:fill='#fff0df'
        lines.append(q(v['id'])+' [label='+q(label)+', fillcolor='+q(fill)+', color='+q(color)+
                     ', penwidth='+('2' if v['id'] in intervention else '1.2')+', tooltip='+q(v['definition'])+'];')
    for e in edges:
        status=statuses.get(e['id'],e['status']);supported=status in ('explicit','contextual')
        label=wrap(e['label'],22)+'\n'+e['id']+' · '+status
        lines.append(q(e['parent'])+' -> '+q(e['child'])+' [label='+q(label)+', style='+q('solid' if supported else 'dashed')+
            ', color='+q('#286c72' if supported else '#986447')+', fontcolor='+q('#264e59' if supported else '#815135')+
            ', tooltip='+q(e['process'])+', URL='+q('../../results/v3/CATALOGUE.md#'+ident+'-'+e['id'])+'];')
    lines.append('legend [shape=note,fontsize=11,fillcolor="#ffffff",color="#c7cdd2",label='+q(
        ('Solid: explicit controlled-text relationship' if offline else 'Solid: supported directional assessment')+
        '\nDashed: unresolved hypothesis; no identified function\nPurple border: intervention; orange fill: unresolved state\nEdge/joint IDs link to the mechanism catalogue\nNo widths encode probability or attribution')+'];')
    if rep['variables']:lines.append(q(rep['outcome'])+' -> legend [style=invis];')
    lines.append('}')
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);dot='\n'.join(lines)+'\n'
    for ext in ('svg','pdf'):
        (folder/(stem+'.'+ext)).write_bytes(subprocess.check_output(['dot','-T'+ext],input=dot.encode()))
    svg=ET.fromstring((folder/(stem+'.svg')).read_bytes())
    width=float(svg.attrib['width'].replace('pt',''));height=float(svg.attrib['height'].replace('pt',''))
    minfont=min(float(x.attrib['font-size']) for x in svg.iter() if 'font-size' in x.attrib)
    return {'id':ident,'dot':dot,'width_pt':width,'height_pt':height,'minimum_font_pt':minfont,
        'minimum_font_at_7inch_width_pt':minfont*min(1,504/width),
        'edges':[{k:e[k] for k in ('id','parent','child','label','status','process')} for e in edges],
        'intervention_trace':trace,
        'withheld':gate.get('withheld',[]),'provenance':record.get('provenance'),
        'semantic_validity':'Author-defined controlled fixture only; not an empirical model result.' if offline else 'Generated interpretation conditional on recorded review, assumptions and coverage.'}


def citation(ref):
    loc=ref.get('source_location',{});url=loc.get('url') or '#'
    if url.startswith('controlled://'):url='../../configs/v3_development.json'
    return '[%s](%s), passage characters %s–%s: %s'%(ref['passage_id'],url,ref.get('start','?'),ref.get('end','?'),ref['supports'])


def catalogue(data):
    lines=['# V3 mechanism catalogue','',
        '**Offline authored contract examples. These are not outputs of the new LLM pipeline, and no human review is claimed.**',
        'The natural A/B/C comparison is unrun because the authorized pod cannot initialize CUDA. Original v2 records remain unchanged. Full machine-readable examples, families and provenance are in the reproduction archive.', '']
    for example in data['examples']:
        rep=example['representation'];fam=example['family'];ident=example['id']
        lines+=['## '+ident.title(),'','Outcome: '+next(v['label'] for v in rep['variables'] if v['id']==rep['outcome'])+'.',
            '', 'Family coverage: **'+fam['coverage']+'**; '+str(len(fam['models']))+' compatible structural models. Scope assumptions concern this authored controlled system only.','',
            '| Variable | Meaning | Factual | Event time | Role |','|---|---|---:|---|---|']
        for v in rep['variables']:
            lines.append('| %s | %s | %s | %s | %s |'%(v['id'],v['definition'],v['factual'],v['event_time'],v['boundary']))
        for e in rep['edges']:
            lines+=['', '<a id="'+ident+'-'+e['id']+'"></a>', '### '+e['id']+': '+e['label'],'',
                e['parent']+' → '+e['child']+'. Direction status: **'+e['status']+'**. Endpoint support: '+json.dumps(e['endpoint_support'])+'.','',e['process'],'',
                'Conditions: '+('; '.join(e['conditions']) or 'As qualified in the process and joint mechanism')+'. Qualifications: '+('; '.join(e['qualifications']) or 'None added')+'.',
                'Gaps: '+('; '.join(e['gaps']) or 'None within this controlled contract')+'. Alternatives: '+('; '.join(e['alternatives']) or 'No additional interpretation invented')+'.','']
            lines += ['- '+citation(ref) for ref in e['evidence']]
        for m in rep['mechanisms']:
            local=fam['local'][m['child']];f=next(f for f in fam['functions'] if f['child']==m['child'])
            lines+=['','### '+m['id']+': joint/function record','',m['description'],'',m['joint_description'] or 'One parent; no multi-parent interaction is asserted.','',
                'Scope assumptions: '+'; '.join(f['scope_assumptions'])+'.',
                'Local coverage: '+local['coverage']+'; '+str(len(local['tables']))+' compatible functions. Inputs: '+', '.join(local['inputs'])+'. Unknown rows: '+str(local['unknown_rows'])+'.','',
                '| Input tuple | Compatible output values |','|---|---|']
            for i,row in enumerate(local['rows']):
                lines.append('| `%s` | `%s` |'%(row,sorted({t[i] for t in local['tables']})))
            lines+=['','Constraints are traceable to evidence or assumptions individually:','']
            for c in f['constraints']:
                lines.append('- `%s` (%s): inputs `%s` permit `%s`. %s'%(c['id'],c['basis'],c['when'],c['allowed'],c['rationale']))
                lines.extend('  '+citation(ref) for ref in c['evidence'])
        lines+=['','### Fixed-family intervention results','','| Query | Intervention | Outcome set | Coverage |','|---|---|---|---|']
        for r in example['queries']:
            lines.append('| %s | `%s` | `%s` | %s |'%(r['id'],r['do'],r['result']['values'],r['result']['status']))
        lines+=['','These numbers execute the authored contract; they measure neither discovery accuracy nor reader comprehension. Every intervention reuses the same family and factual boundary values.','']
    lines+=['## Preserved v2 interpretation audit','',
        'This is replay and inspection of earlier LLM output, not a new v3 application result. All seven v2 directional judgments remain unsupported; source priorities remain unavailable. No new edge labels or source judgments were authored to rescue the literary graph.','']
    for node in data['v2_replay']['nodes']:
        lines+=['### V2 '+node['id']+': '+node['label'],'',
            'Original generated description: '+str(node['original_generated_description']),'',
            'Declared parents: '+str(node['parents'])+'. Actual local configurations: '+str(len(node['behavior']['rows']))+'.',
            'Retained same-model description check: '+str(node['retained_v2_semantic_review'].get('description_matches_behavior','unassessed'))+'.',
            'Necessary conditions for output one within the assumed function: `'+json.dumps(node['behavior']['necessary_for_one'])+'`.','']
        omitted=[x for x in node['behavior']['parent_changes'] if x['witness_count']]
        for change in omitted:
            lines.append('- `%s` has %s behavior; example `%s`.'%(change['parent'],change['polarity'],json.dumps(change['witnesses'][:1])))
    lines+=['','The capture rule retained a negative semantic agreement flag, but that reviewer reason discusses actors and source entailment rather than a precise truth-table contradiction. It is evidence of a nonbinding/mixed review gate, not independent literary adjudication. A one-way “if” statement need not claim necessity. The actual rule also contains scout inhibition absent from its concise prose; this is a mechanism-coverage gap requiring review.','']
    return '\n'.join(lines)


def review_packet(data, config):
    return '\n'.join([
        '# Researcher review packet: v3 development', '', '**Pending. No researcher judgments have been recorded.**', '',
        '1. Inspect the controlled packet texts in `configs/v3_development.json`. The beacon has explicit substitution/inhibition. The ferry has implied permission/action context, a missing intermediate rule and a later belief. The mathematical reference deliberately uses all eight compatible missing rules rather than the hidden generating rule. These are authored diagnostic cases, not independent natural-narrative validation.', '',
        '2. Inspect `CATALOGUE.md` and the two graphs. Their edge phrases, joint descriptions and partial tables are authored software fixtures. They establish that the implementation can retain and display these records; they do not establish that an LLM can synthesize them.', '',
        '3. Inspect the preserved v2 capture record in the catalogue: its semantic agreement flag is false but it survived admission. Separate (a) event/actor establishment, (b) directional influence, (c) exact functional claims, and (d) whether the prose omits input-dependent behavior. Do not treat the old reviewer as gold or read a bare “if” as “if and only if.”', '',
        '4. Review source coverage for the new Five Kings packet. It uses seven source scenes selected by lexical relevance within three temporal windows. Early selections mostly concern the Wall, a middle selection is retrospective, and late selections include reports and a war council. Coverage in time does not establish causal coverage. The fixed target is conflict active at the end of season 1. Does this packet establish that endpoint, as distinct from an earlier order, intention or isolated military action? No v3 construction has run, so there are no new literary mechanisms to adjudicate.', '',
        '5. Before a new inference attempt, decide whether the packet and three-case development contrast are informative enough. After GPU access is restored, the next authorized experiment should run precisely these paired packets and inspect source→description and description→function disagreements; expand only if the end-to-end gate succeeds.', '',
        'For each future generated item record: ID; endpoint-event support; causal-direction support; exact-function constraints; temporal/information issue; passage/offset; counterexample if applicable; verdict and rationale. Leave unknowns unknown. No comprehension improvement has been tested.', '',
        'Full private natural passage context: `.private/v3/review_packet.html`. Public source locations:', '',
        *['- [%s](%s), %s, lines %s–%s.'%(p['id'],p['url'],p['episode'],p['first_line'],p['last_line']) for p in config['cases'][2]['passages']], '',
        'The original v2 review packet and unfilled form remain at `results/v2/five_kings_REVIEW_PACKET.md` and `results/v2/five_kings_review_form.csv`. Their status has not changed.', ''])


def results_text(data, config, validation):
    stop=data.get('blocker',{});start=config.get('_budget',{}).get('started_at')
    duration=(datetime.fromisoformat(stop['at'])-datetime.fromisoformat(start)).total_seconds() if start and stop.get('at') else None
    lines=['# V3 bounded development delivery','',
        '**Implemented, offline-validated, and inference-blocked. The new generative method is not yet empirically demonstrated.** Versions 1 and 2 remain unchanged; their old held-out test set was not used for tuning. Independent researcher review remains pending.','',
        '## What changed','',
        'Mechanism records now govern construction rather than serving only as graph annotations. They connect variables, substantive edge/joint prose, source-exact locations, qualifications, functional constraints, explicit assumptions, retained alternatives, and fixed-family intervention results. A diagnosis/retrieval/revision loop precedes complete functions. Unknown rows need no invented output. Exhaustive families, sampled candidates, inconsistent constraints and unavailable executable scopes have distinct statuses.','',
        'Source→description review, description→function counterexamples and function→reported-result checks are separate. Negative checks withhold a mechanism instead of replacing its prose with generic table text. The graph renderer uses recorded specific phrases, visible evidence status and catalogue IDs. Source uncertainty can downgrade a display status but cannot upgrade unsupported evidence. No attribution formula or old source score was changed.','',
        '## Bounded A/B/C comparison','',
        '| Case | A: existing v2 | B: presentation only | C: mechanism first |',
        '|---|---|---|---|']
    lines+=['| '+c['id']+' | Unrun | Unrun | Unrun |' for c in config['cases']]
    lines+=['',
        'The three source packets, query references and per-arm allowances were fixed before any inference request. B shares A’s variables/functions and preserves all retained v2 hypotheses; immutable model hashes prevent a presentation-only change from becoming a modeling change. The runner records every stage and failure. All nine planned cells are unavailable, not failed syntheses or zero-accuracy observations. No component gain, prose-quality gain, source-grounding gain, repair success or human comprehension benefit can be estimated. No expansion was run.','',
        'The existing authenticated pod and cached Qwen3-14B-AWQ revision were present, with an idle RTX 4090. The dedicated v3 server failed during initialization: CUDA `cuInit(0)=999`, PyTorch reported CUDA unavailable, and opening `/dev/nvidia-uvm` returned `OSError [Errno 5] Input/output error`. Other inspected HTTP ports returned HTML, not a usable inference API. No driver, pod, billing or unrelated service change was attempted.','',
        'The immutable service window was 15:02:48–17:02:48 UTC on 2026-10-13, capped at 150,000 generated tokens. It was closed at '+stop.get('at','unknown')+'. '+('The failed startup/watchdog attempt lasted %.1f minutes. '%(duration/60) if duration is not None else '')+
        '**New inference requests: 0; generated tokens: 0; substantive v3 GPU inference: none.** Sampled GPU memory remained 1 MiB with 0% utilization. Only the v3 watchdog needed stopping; the failed model process had exited. The pod, SSH and Jupyter remain available. Billing cost is unknown.','',
        '## Offline evidence','',
        '| Check | Result | What it establishes |','|---|---:|---|',
        '| Two-input partial-function families | 256/256 matched a bit-mask oracle | Finite constraint enumeration |',
        '| Outcome sets across those families | 1,024/1,024 matched | Uncertainty preservation in the declared mathematical family |',
        '| Authored controlled fixture queries | 8/8 reference sets matched | Execution and representation contracts, not extraction |',
        '| Prior v2 application queries | 8/8 reproduced | Preservation/replay of old numerical results |',
        '| Software tests | '+str(validation.get('tests',{}).get('passed','See validation.json'))+' passed | Structural, provenance, revision and process contracts; not literary validity |',
        '| New A/B/C inference | 0/9 cells run | No empirical comparison available |','',
        'The partial ferry fixture retains eight compatible functions and returns `{0,1}` when the missing departure rule matters. Directly preventing crossing returns `{0}` under the explicit recording mechanism. Sampled agreement is never labeled identified; separately recorded certificates are limited to direct target interventions or witnesses exhausting the declared output domain. Missing intermediate and multiple missing mechanisms, contradictory constraints, background preservation, exact source provenance, invented reviewer IDs, misleading chronology, and concrete necessity/sufficiency counterexamples are covered by the tests.','',
        'The preserved v2 record confirms information loss: substantive prose is stored but replaced for operative descriptions; the capture candidate survives a false description-match flag; the renderer uses signs/blank edges. That flag’s reason conflates source interpretation and function agreement, so it is not taken as semantic gold. The actual capture function includes an inhibitory input unmentioned in its short description. The earlier seven unsupported directional judgments and unavailable path ranking remain untouched.','',
        '## Acceptance and limits','',
        '| Criterion | Status |','|---|---|',
        '| Displayed edges have substantive phrases and evidence status | Implemented; demonstrated on authored fixtures |',
        '| Known description/function contradictions withheld | Deterministically tested; semantic extraction unrun |',
        '| Assumptions remain visible | Implemented in records/catalogue |',
        '| Missing mechanisms survive without becoming complete rules | Exhaustive and sampled contract checks pass |',
        '| Improvement beyond appearance is measured | Formal engine behavior checked; LLM A/B/C gains unmeasured |',
        '| Natural narrative discovery and grounded mechanisms | Not demonstrated |','',
        'The finite prototype covers declared integer/categorical domains and at most 64 input rows per function. Enumeration is bounded at 4,096 local candidates and 512 global models; larger candidate spaces are explicitly sampled, and larger local domains remain unavailable. Fixed graph, determinism, omitted variables and hidden confounding are assumptions, not discoveries. Same-model semantic review can miss unsupported bridges or mistranslate prose into formal assertions. A correct solver cannot repair that failure. Source fidelity and researcher adjudication remain unresolved.','',
        'The controlled ferry deliberately contains an explicit scope statement for its missing function. It tests preserving uncertainty while interpreting some ordinary event prose, not unrestricted open-domain discovery. V2’s unchanged television wording is a domain mismatch on the two controlled cases; future measurements must disclose it. The presentation-only contrast shares A’s inference costs and cannot rescue a failed base model.','',
        '## Next experiment','',
        'Restore CUDA/UVM access through the pod operator, then authorize a fresh bounded service window without altering the completed v3 budget. Run the already specified three paired packets. Prioritize whether C extracts the omitted-rule scope, separates permission from action and later belief from cause, and whether its substantive descriptions survive exhaustive counterexamples. Independently adjudicate the Five Kings endpoint and causal bridges before expanding the corpus. If the source→description stage still fails, the next intervention should target evidence coverage or concept revision, not more decorative prose.','',
        'This delivery supports an engineering prototype and a sharper failure diagnosis. It does not yet support a new methodological performance claim or an application contribution. The earlier controlled-methods/failure-analysis manuscript remains the measured manuscript; no new completed-study manuscript is claimed.','',
        '## Reproduction','',
        'Run `PYTHONPATH=src python3 -m got_war.v3.report restore .`, then `PYTHONPATH=src python3 -m got_war.v3.report reproduce .`. Create the ignored temporary parent with `mkdir -p .cache`, then run `PYTHONPATH=src python3 -m pytest -q --basetemp=.cache/pytest_tmp` for the full suite. The compact bundle contains authored fixtures, compatible families, the unchanged v2 model/audit excerpt, protocol versions, blocker/accounting and validation inputs. It excludes full copyrighted passages, credentials, weights, and raw server logs. A fresh private source packet and a working authorized endpoint are needed for new inference.','',
        'Files: `docs/V3_METHOD.md`, `configs/v3_development.json`, `results/v3/comparison.json`, `results/v3/component_summary.json`, `results/v3/CATALOGUE.md`, `results/v3/REVIEW_PACKET.md`, `results/v3/validation.json`, `results/v3/reproduction.tar.gz`, and `figures/v3/{beacon,ferry}.{svg,pdf}`. The component table uses nulls for unrun quantities and distinguishes unsupported identification from a conditional singleton hypothesis. The figures are explicitly labeled offline authored contract examples.','']
    return '\n'.join(lines)


def private_review(root, config):
    f=root/'.private/v3/five_kings_packet.json'
    if not f.exists():return
    packet=json.loads(f.read_text());rows=['<!doctype html><meta charset="utf-8"><title>V3 pending researcher review</title>',
        '<style>body{max-width:960px;margin:40px auto;font:17px/1.5 sans-serif}pre{white-space:pre-wrap;background:#f5f5f5;padding:15px}</style>',
        '<h1>Version 3: source coverage review, pending</h1><p>No v3 model inference occurred. These are exact cached passage contexts, not new literary causal claims.</p>',
        '<p>Outcome: '+html.escape(config['cases'][2]['outcome'])+'</p>']
    for p in packet['segments']:
        rows+=['<h2>'+html.escape(p['id'])+'</h2><a href="'+html.escape(p['url'])+'">Source</a><pre>'+html.escape(p['text'])+'</pre>']
    (root/'.private/v3/review_packet.html').write_text('\n'.join(rows))


def build(root):
    root=Path(root);run=root/'runs'/RUN;data=json.loads((run/'offline.json').read_text());cfg=json.loads((root/'configs/v3_development.json').read_text())
    cfg['_budget']=json.loads((root/'configs/budget_v3.json').read_text())
    figures=[render(x,root/'figures/v3') for x in data['examples']]
    (root/'results/v3/CATALOGUE.md').write_text(catalogue(data))
    (root/'results/v3/REVIEW_PACKET.md').write_text(review_packet(data,cfg))
    checks=[]
    for example in data['examples']:
        for r in example['queries']:
            checks.append(verify_reported_result(example['representation'],example['family'],r['do'],r['result']))
    validation={'engine':data['engine'],'authored_queries':len(checks),'authored_query_checks_pass':all(c['passed'] for c in checks),
        'v2_query_replay_count':len(data['v2_replay']['query_replay']),'v2_query_replay_pass':data['v2_replay']['passed'],
        'figures':figures,'visual_inspection':'pending','automated_checks_are_scientific_validation':False}
    old=root/'results/v3/validation.json'
    if old.exists():
        for key in ('tests','visual_inspection','clean_export','preservation','offline_pipeline_replay'):
            if key in json.loads(old.read_text()):validation[key]=json.loads(old.read_text())[key]
    atomic_json(old,validation)
    (root/'results/v3/RESULTS.md').write_text(results_text(data,cfg,validation))
    private_review(root,cfg)
    return validation


def pack(root):
    root=Path(root);paths=['runs/'+RUN+'/offline.json','runs/'+RUN+'/pre_inference_freeze.json',
        'runs/'+RUN+'/infrastructure.json','runs/'+RUN+'/infrastructure_blocker.json',
        'runs/'+RUN+'/service_stop.json','runs/'+RUN+'/gpu_samples.jsonl','runs/'+RUN+'/COMPLETE']
    # Reproduction preserves pre-inference versions even though no inference ran;
    # post-blocker offline hardening is a disclosed development revision.
    extra=root/'runs'/RUN/'pre_inference_code'
    if extra.exists():paths += [str(p.relative_to(root)) for p in extra.rglob('*') if p.is_file()]
    members={};out=io.BytesIO()
    with gzip.GzipFile(fileobj=out,mode='wb',mtime=0) as gz:
        with tarfile.open(fileobj=gz,mode='w') as tar:
            for name in sorted(paths):
                data=(root/name).read_bytes();info=tarfile.TarInfo(name);info.size=len(data);info.mtime=0
                tar.addfile(info,io.BytesIO(data));members[name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    binary=out.getvalue();(root/'results/v3/reproduction.tar.gz').write_bytes(binary)
    atomic_json(root/'results/v3/reproduction_manifest.json',{'files':members,'archive_bytes':len(binary),
        'archive_sha256':hashlib.sha256(binary).hexdigest(),'expanded_bytes':sum(v['bytes'] for v in members.values()),
        'scope':'Offline controlled contracts, original v2 generated descriptions/function behavior, pre-inference protocol versions and infrastructure closure. No new inference responses exist.'})


def restore(root):
    root=Path(root).resolve();manifest=json.loads((root/'results/v3/reproduction_manifest.json').read_text())
    data=(root/'results/v3/reproduction.tar.gz').read_bytes()
    if hashlib.sha256(data).hexdigest()!=manifest['archive_sha256']:raise ValueError('Archive hash mismatch')
    count=0
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tar:
        if set(tar.getnames())!=set(manifest['files']):raise ValueError('Unexpected archive members')
        for member in tar.getmembers():
            name=member.name;dest=(root/name).resolve()
            if not member.isfile() or root not in dest.parents or '..' in Path(name).parts:raise ValueError('Unsafe member')
            blob=tar.extractfile(member).read()
            if hashlib.sha256(blob).hexdigest()!=manifest['files'][name]['sha256']:raise ValueError('Member hash mismatch')
            if dest.exists() and dest.read_bytes()!=blob:raise ValueError('Refusing to overwrite changed '+name)
            if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(blob);count+=1
    return count


def reproduce(root):
    root=Path(root);data=json.loads((root/'runs'/RUN/'offline.json').read_text())
    from .offline import exhaustive_validation, examples
    expected=exhaustive_validation()
    if expected!=data['engine']:raise ValueError('Engine regression differs')
    fixtures=examples(json.loads((root/'configs/v3_development.json').read_text()))
    if fixtures!=data['examples']:raise ValueError('Controlled fixture reproduction differs')
    from ..structural_programs import SCM
    scm=SCM(data['v2_replay']['model'])
    for r in data['v2_replay']['query_replay']:
        if scm.solve(interventions=r['do'])[r['target']] != r['stored']:
            raise ValueError('Original v2 query reproduction mismatch')
    validation=build(root)
    if not validation['authored_query_checks_pass']:raise ValueError('Query trace failure')
    print(json.dumps({'engine_comparisons':1280,'authored_queries':8,'figures':2,'passed':True}))


if __name__=='__main__':
    import sys
    action=sys.argv[1] if len(sys.argv)>1 else 'build';root=sys.argv[2] if len(sys.argv)>2 else '.'
    if action=='restore':print('Restored',restore(root))
    else:globals()[action](root)
