"""Check manuscript claims and build integrity against preserved compact evidence.

This reads existing metrics only. It does not load models or run experiments.
Detailed mappings and validation output are editorial artifacts, not paper content.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
ART = PROJECT / '.artifacts/manuscript_draft'
BUILD = HERE / 'build'
PDF = HERE / 'draft.pdf'
SOURCES, CLAIMS = {}, []


def source(path):
    p = PROJECT / path
    SOURCES[path] = hashlib.sha256(p.read_bytes()).hexdigest()
    return p


def csv(path):
    return pd.read_csv(source(path))


def js(path):
    return json.loads(source(path).read_text())


def subset(frame, **selector):
    for key, value in selector.items():
        frame = frame[frame[key] == value]
    return frame


def claim(name, actual, expected, evidence, selector=None, tolerance=1e-6):
    if isinstance(actual, (int, float, np.number)):
        assert np.isclose(actual, expected, rtol=0, atol=tolerance), (name, actual, expected)
        actual = float(actual)
    else:
        assert actual == expected, (name, actual, expected)
    CLAIMS.append(dict(claim=name, value=actual, source=evidence,
                       selector=selector, tolerance=tolerance))


def main():
    p2 = 'phase2/results/'
    small = csv(p2 + 'method_summary.csv')
    metrics = csv(p2 + 'metrics.csv')
    selected = subset(metrics, study='controlled', endpoint='T2', stage='selected')
    main_methods = ['M0', 'M1', 'M2', 'M3', 'M4', 'M5', 'fixed', 'random']
    expected = [.325007, .193962, .272248, .106168, .117548, .130180, .181821, .142134]
    for method, mean in zip(main_methods, expected):
        sel = dict(study='controlled', endpoint='T2', method=method)
        row = subset(small, **sel).iloc[0]
        raw = subset(selected, method=method)
        claim('Controlled ' + method + ' T2', row['mean'], mean, p2+'method_summary.csv', sel)
        claim('Controlled ' + method + ' reaggregation', raw.sw1.mean(), row['mean'], p2+'metrics.csv', sel)
        claim('Controlled ' + method + ' SCM count', len(raw[['family','d','seed']].drop_duplicates()), 15, p2+'metrics.csv', sel)
        claim('Controlled ' + method + ' conditions', len(raw), 60, p2+'metrics.csv', sel)
        for key in ['low','high','logical_seconds','prediction_seconds']:
            CLAIMS.append(dict(claim='Controlled '+method+' '+key, value=float(row[key]), source=p2+'method_summary.csv', selector=sel))
    reliability = csv(p2+'repair_reliability.csv')
    base = subset(selected, method='fixed').set_index('task_id').sw1
    for method, count in [('M3',8),('M4',7),('M5',1),('random',5),('tau0',8),('uniform',6)]:
        row = subset(reliability, study='controlled', stage='selected', method=method, endpoint='T2').iloc[0]
        raw = subset(selected, method=method).set_index('task_id').sw1
        computed = int(((raw-base) > np.maximum(.001,.05*base)).sum())
        claim(method+' controlled harmful conditions', computed, count, p2+'metrics.csv', {'method':method})
        claim(method+' harm table agreement', row.harmful_count, count, p2+'repair_reliability.csv', {'method':method,'stage':'selected'})
    comparisons = csv(p2+'primary_comparisons.csv')
    for method, difference, p in [('M4',-.01137983086,.046875),('M5',-.02401204051,.0082397461)]:
        row = subset(comparisons, a='M3', b=method).iloc[0]
        claim('M3 minus '+method, row['mean'], difference, p2+'primary_comparisons.csv', {'a':'M3','b':method})
        claim('M3 versus '+method+' Holm p', row.p_holm, p, p2+'primary_comparisons.csv')
    discovery = subset(csv(p2+'discovery_coverage.csv'), study='controlled')
    claim('Controlled DCDI optimizer-stopping successes', int(discovery.converged.sum()), 29, p2+'discovery_coverage.csv')
    claim('Controlled DCDI raw-per-node successes', int((discovery.h_raw/discovery.d <= 1e-8).sum()), 0, p2+'discovery_coverage.csv')
    claim('Controlled DCDI outputs requiring projection', int((discovery.projected_edges > 0).sum()), 5, p2+'discovery_coverage.csv')
    llm = csv(p2+'llm_edit_audit.csv')
    for key, count in [('valid_new_edits',122),('score_rejections',97),('accepted_changes',25)]:
        claim('LLM edit '+key, int(llm[key].sum()), count, p2+'llm_edit_audit.csv')
    light = subset(small, study='real', metadata_variant='coherent', endpoint='T2')
    for method, mean in [('M1',.0855734125),('M3',.134851247),('M5',.145990953),('fixed',.146088257),('M2',.172341704)]:
        row = subset(light, method=method).iloc[0]
        claim('Light polarizer '+method, row['mean'], mean, p2+'method_summary.csv', {'study':'real','metadata_variant':'coherent','endpoint':'T2','method':method})

    p3 = 'phase3/results/'
    large = subset(csv(p3+'metrics.csv'), resource='adjusted', sensitivity='primary')
    summary = subset(csv(p3+'summary.csv'), resource='adjusted')
    claim('Scaling independent SCMs', large.scm.nunique(), 45, p3+'metrics.csv')
    for method in main_methods:
        part = subset(large, method=method)
        claim('Scaling '+method+' conditions', len(part), 90, p3+'metrics.csv')
        claim('Scaling '+method+' largest graph', int(part.d.max()), 100, p3+'metrics.csv')
        assert part.sw1.notna().all() and np.isfinite(part.sw1).all()
    for d, m3, m5, fixed, harm, retention in [(20,.097591,.102162,.106173,2,.25),(50,.080263,.081759,.082131,0,.8),(100,.070146,.070065,.070146,0,1.)]:
        for method, value in [('M3',m3),('M5',m5),('fixed',fixed)]:
            sel=dict(stratum='A-d'+str(d), method=method)
            row=subset(summary,**sel).iloc[0]
            claim('Scaling d%d %s T2'%(d,method),row['mean'],value,p3+'summary.csv',sel)
        rows=subset(large,d=d,profile='sparse',method='M3')
        claim('Scaling d%d M3 harms'%d,int(rows.harmful.sum()),harm,p3+'metrics.csv')
        claim('Scaling d%d M3 retention'%d,rows.retained.mean(),retention,p3+'metrics.csv')
    for method,count in [('M3',2),('M4',1),('M5',0),('random',1)]:
        claim('Scaling all profiles '+method+' harms',int(subset(large,method=method).harmful.sum()),count,p3+'metrics.csv')
    discovery=subset(csv(p3+'discovery.csv'),sensitivity='primary')
    claim('Scaling DCDI datasets',len(discovery),45,p3+'discovery.csv')
    claim('Scaling DCDI raw-per-node successes',int((discovery.h_per_node<=1e-8).sum()),0,p3+'discovery.csv')
    claim('Scaling DCDI step caps',int((discovery.steps==60000).sum()),44,p3+'discovery.csv')
    weights=subset(csv(p3+'mixture_weights.csv'),resource='adjusted',sensitivity='primary',profile='sparse')
    for d,w in [(20,.877),(50,.961),(100,.980)]:
        claim('Scaling d%d initial mixture weight'%d,subset(weights,d=d).initial_weight_before_audit.mean(),w,p3+'mixture_weights.csv',tolerance=.0005)

    p4='phase4_real_application/results/'
    wind=csv(p4+'summary.csv'); costs=csv(p4+'costs.csv'); runs=csv(p4+'metrics.csv')
    for method,value in zip(main_methods,[1.091071,.813118,.219902,.331048,.367959,.350596,.360158,.332035]):
        row=subset(wind,method=method).iloc[0]
        claim('Wind '+method+' contrast error',row.effect_error,value,p4+'summary.csv',{'method':method})
        raw=subset(runs,method=method,panel='primary')
        claim('Wind '+method+' acquisition/target reaggregation',raw.groupby('target').effect_error.mean().mean(),row.effect_error,p4+'metrics.csv',{'method':method,'panel':'primary'})
        for key in ['ci_low','ci_high','coverage90','joint_sw1']:
            CLAIMS.append(dict(claim='Wind '+method+' '+key,value=float(row[key]),source=p4+'summary.csv',selector={'method':method}))
    claim('Wind projected DCDI strict convergence',bool(subset(costs,method='M2').iloc[0].strict_convergence),False,p4+'costs.csv')
    graphs=js(p4+'graphs.json'); initial=set(map(tuple,graphs['M3']['initial']['edges'])); selected_graph=set(map(tuple,graphs['M3']['selected']['graph']['edges']))
    for name,actual,expected in [('initial edges',len(initial),14),('selected edges',len(selected_graph),15),('added edges',len(selected_graph-initial),2),('removed edges',len(initial-selected_graph),1),('hatch adjacent edges',sum(2 in edge for edge in selected_graph),0)]:
        claim('Wind M3 '+name,actual,expected,p4+'graphs.json')
    claim('Wind M3/M4/M5 shared bank',len({graphs[m]['bank_hash'] for m in ['M3','M4','M5']}),1,p4+'graphs.json')
    split=js(p4+'split_manifest.json'); primary=[r for r in split['final_acquisitions'] if r['panel']=='primary']
    claim('Wind primary acquisitions',len(primary),5,p4+'split_manifest.json')
    claim('Wind primary observations',sum(r['n'] for r in primary),699,p4+'split_manifest.json')
    extra = split['preprocessing_fit_rows'] - split['retained_rows_by_role']['fit']
    claim('Wind preprocessing-only observations',extra,1,p4+'split_manifest.json')
    claim('Wind non-test observations including preprocessing-only row',split['non_test_intervention_rows']+extra,3399,p4+'split_manifest.json')
    observed=csv(p4+'observed_effects.csv')
    for run,outcome,effect in [('validate_load_in','pressure_upwind',26.50594),('validate_load_in','current_in',.106030),('validate_load_out','pressure_downwind',-26.14912),('validate_load_out','current_out',.107945),('validate_hatch_rpms','pressure_upwind',-5.42556),('validate_hatch_rpms','pressure_downwind',-7.60634),('validate_hatch_rpms','current_in',-.002438)]:
        row=subset(observed,run=run,outcome=outcome).iloc[0]
        claim('Wind measured '+run+' '+outcome,row.effect,effect,p4+'observed_effects.csv',{'run':run,'outcome':outcome},tolerance=1e-5)
        for key in ['ci_low','ci_high','unit','n_low','n_high']:
            value=row[key]; value=value.item() if isinstance(value,np.generic) else value
            CLAIMS.append(dict(claim='Wind '+run+' '+outcome+' '+key,value=value,source=p4+'observed_effects.csv'))
    decisions=csv(p4+'decision_summary.csv')
    assert (decisions.violations==0).all()
    assert np.allclose(decisions.mean_feasible_regret_a,.00042141919)
    claim('Wind identical regret across methods',decisions.mean_feasible_regret_a.nunique(),1,p4+'decision_summary.csv')

    # Bibliography, anonymity, reader-facing language and build checks.
    tex_files=[HERE/'main.tex']
    tex=tex_files[0].read_text()
    assert not re.search(r'\\(?:input|include|bibliography|bibliographystyle)\s*\{',tex), 'Manuscript requires external LaTeX content'
    assert '../' not in tex, 'Manuscript refers to assets outside its directory'
    assets=json.loads((HERE/'assets.json').read_text())['assets']
    for name,asset in assets.items():
        data=(HERE/name).read_bytes()
        assert hashlib.sha256(data).hexdigest()==asset['sha256'], name
    assert tex.isascii(), 'Reader-facing TeX contains non-ASCII punctuation'
    citations=set()
    for match in re.findall(r'\\cite\{([^}]+)\}',tex):citations.update(match.split(','))
    keys=set(re.findall(r'\\bibitem\{([^}]+)\}',tex))
    assert keys==citations, (keys-citations,citations-keys)
    assert len(keys)==21
    assert tex.count('\\begin{equation}')==8
    abstract=tex.split(r'\keywords')[0].split(r'\begin{abstract}')[1]
    words=len(abstract.split())
    assert 150<=words<=250
    log=BUILD.joinpath('main.log').read_text(errors='replace')
    assert 'Overfull' not in log
    assert 'undefined references' not in log and 'undefined citations' not in log
    assert not re.search(r'Citation .* undefined',log)
    for name in ['controlled','wind','secondary']:
        assert ART.joinpath('tables/'+name+'.tex').read_text().strip() in tex, 'Embedded table differs from evidence: '+name
    aux=BUILD.joinpath('main.aux').read_text()
    appendix_page=int(re.search(r'\\newlabel\{appendix-start\}\{\{[^}]*\}\{(\d+)\}',aux).group(1))
    info=subprocess.check_output(['pdfinfo',str(PDF)],text=True)
    pages=int(re.search(r'^Pages:\s+(\d+)',info,re.M).group(1))
    assert appendix_page-1<=18 and pages-appendix_page+1<=7
    author=re.search(r'^Author:[ \t]*(.*)$',info,re.M)
    assert author is None or not author.group(1).strip()
    pdftext=BUILD.joinpath('manuscript.txt').read_text()
    for forbidden in ['mantzaris','computingConference2027','sem-update/','ad21e60','8c452ac','a17a8f7','6b836ef','phase two','phase three','phase four','TODO','placeholder','test-suite']:
        assert forbidden.lower() not in pdftext.lower(), forbidden
    assert pdftext.count('Declaration on Generative AI')==1
    result=dict(status='passed',claims_checked=len(CLAIMS),source_hashes=SOURCES,
                abstract_words=words,main_pages=appendix_page-1,
                additional_pages=pages-appendix_page+1,total_pages=pages,
                bibliography_entries=len(keys),equation_groups=8,
                bundled_assets=len(assets),
                pdf_sha256=hashlib.sha256(PDF.read_bytes()).hexdigest(),
                manuscript_tex_bytes=sum(p.stat().st_size for p in tex_files),
                bibliography_bytes=(HERE/'references.bib').stat().st_size,
                scientific_review='Human review pending; this checks evidence consistency, not causal identification.')
    (ART/'claim_evidence.json').write_text(json.dumps(CLAIMS,indent=2)+'\n')
    (ART/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_hashes'},indent=2))


if __name__=='__main__':
    main()
