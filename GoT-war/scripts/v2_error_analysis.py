"""Descriptive error-stage audit; frozen primary scoring is unchanged."""
import collections
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from got_war.v2.analysis import structural_scores,parse_answers
from got_war.v2.runtime import paths


def main():
    root,run,result=paths(ROOT)
    cases=[json.loads(line) for line in (run/'benchmark_cases.jsonl').read_text().splitlines()]
    cases=[c for c in cases if c['split']=='test'];records=[];counts=collections.Counter();examples=collections.defaultdict(list)
    for case in cases:
        f=run/'benchmark'/(case['id']+'.json')
        if not f.exists():continue
        r=json.loads(f.read_text());records.append(r)
        if not r.get('model'):
            counts['rejected synthesis']+=1;examples['rejected synthesis'].append(case['id'])
        else:
            counts['admitted synthesis']+=1;scores=structural_scores(r,case)
            for key,label in [('known_function_agreement','at least one wrong known function'),('unknown_flag_accuracy','incorrect unknown-rule flag'),('event_state_agreement','declared state differs from source'),('direction_precision','extra proposed influence'),('direction_recall','omitted declared influence')]:
                if scores[key]<1:counts[label]+=1;examples[label].append(case['id'])
            if not r.get('trace',{}).get('ranking_available',False):counts['admitted model with unavailable FULL ranking']+=1
            if r.get('trace',{}).get('attribution',{}).get('contrast')==0:counts['admitted model with zero selected coalition contrast']+=1
        e=r.get('explanation',{})
        if e.get('sentences'):
            counts['generated explanation']+=1
            if e.get('reviewer_failure'):counts['reviewer failed actual-ID contract']+=1;examples['reviewer failed actual-ID contract'].append(case['id'])
            if not e.get('deterministic_check',{}).get('passed',False):counts['explanation failed deterministic checks']+=1;examples['explanation failed deterministic checks'].append(case['id'])
            if e.get('review',{}).get('reviewer_valid') and not e['review'].get('all_supported'):counts['prose not fully supported by same-model review']+=1;examples['prose not fully supported by same-model review'].append(case['id'])
            if e.get('displayable'):counts['displayable explanation']+=1
        for method in ('B0','B1'):
            output=r.get('methods',{}).get(method,{})
            if any(v is None for v in parse_answers(output,case['queries']).values()):counts[method+' missing or malformed answer(s)']+=1
    lines=['# Version 2 error analysis','',
        'This is a descriptive stage audit of %d/%d held-out records. Counts can overlap within one SCM; they are not extra independent samples. Examples are the first stable SCM IDs in each category, not a representative error-rate sample. Primary estimates and paired intervals remain those in `test_summary.json`.'%(sum(r.get('completed',False) for r in records),len(cases)), '',
        '| Stage or property | SCM count | First retained examples |','|---|---:|---|']
    for label,count in sorted(counts.items()):lines.append('| '+label+' | '+str(count)+' | '+', '.join(examples.get(label,[])[:3])+' |')
    lines += ['', '## What the failures mean', '',
        '- Formal rejection means no candidate survived the fixed initial generation plus two repairs. It is an end-to-end failure, even if its extracted adjacency remains usable by B1.',
        '- Formal admission means typed, active-input, DAG and self-declared factual consistency. It does not by itself mean faithful extraction of the supplied states or known functions; the separate grounding/function scores expose those errors.',
        '- A wrong unknown-rule flag can make ALT too narrow or unnecessarily uncertain. A correct compatible-family solver cannot recover uncertainty that synthesis failed to mark.',
        '- B2 deliberately supplies one conditional model answer. Its nonabstaining singleton is scored as unsupported when the source family is underidentified; this operational metric is not a calibrated confidence probability.',
        '- Deterministic explanation failures include trace-field names, numbers, identifiers, tie qualifiers and sentence-format failures. A valid-ID reviewer can still accept unsupported prose. Reviewer control accuracy and false acceptance are reported separately; no semantic human gold is available.',
        '- Source ranking measures agreement with a frozen structural-slice label, not reading benefit or a minimal sufficient evidence set. In a factual-value control, known factual states and the stated intervention semantics can answer the question without all positively labeled downstream rules. A zero contrast can therefore make influence-based ranking unavailable while the relevance label remains positive. This metric mismatch is disclosed without changing its frozen definition.',
        '- The explicit controlled texts do not independently vary source reliability. FULL versus uniform support therefore tests the behavior of the implemented weights on this corpus, not a general benefit from weighting heterogeneous narrative evidence.', '',
        '## Application-stage failures', '',
        'Fresh transcript-based construction failed after retained schema, graph, mechanism and representation repairs. Its last composite-event mechanism contradicted its own factual state. A separately labeled refinement of the first earlier LLM proposal reached a six-node model only after dependency retraction, a single verbal-mechanism serialization diagnostic and lossless replay of an already generated literal operand. No researcher selected a story predicate or supplied a table entry.', '',
        'The retained application has four fixed scope boundaries and only two connected functions. Its unequal six-path game exposes substitution, inhibition and player/reference sensitivity, but all seven directional judgments and all six weakest-link path scores remain unsupported/zero. It yields no evidence-weighted source ranking and only one functional interpretation. Those are failures to establish a grounded, robust war explanation, not reasons to raise scores or pad the graph.', '',
        'The application prose is rejected for nonexistent numeric trace-field keys and excess actual sentences. Its reviewer covers all six actual sentence IDs; this is an explanation failure, not the version-1 invented-sentence-ID failure. The reviewer labels all prose sentences supported and scores 3/4 on strict controls, calling the invalid probability claim unverifiable instead of unsupported. This does not establish independent narrative entailment.', '',
        'Targeted assistant inspection flags planned versus realized actions, composite/misaligned timing, an internally inconsistent outcome audit and reference-policy ambiguity. The raw model remains unchanged. These concerns and the generated scout-inhibition/war-necessity assumptions require researcher adjudication. Full context stays in the private review packet; public source links and equations remain available.', '',
        'No paired retrieval ablation, second model, additional application seeds, human comprehension study or new northern/Daenerys experiment was run. The frozen controlled AST interface differs from the later application finite-table/serialization interface. Their comparison cannot identify which application repair improved narrative validity.']
    (result/'ERROR_ANALYSIS.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'held_out_records':len(records),'counts':dict(counts)}))


if __name__=='__main__':main()
