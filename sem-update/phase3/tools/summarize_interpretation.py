"""Post-evaluation descriptive checks from compact, immutable plotting inputs.

This does not fit, select, sample, alter hypotheses, or add formal tests.
"""
import json
import pandas as pd
from sem_update.phase3.reporting import bootstrap
from sem_update.phase3.runtime import RESULTS, atomic_json, file_hash


def main():
    metrics = pd.read_csv(RESULTS / 'metrics.csv')
    primary = metrics[(metrics.sensitivity == 'primary') & (metrics.resource == 'adjusted')]
    checkpoints = pd.read_csv(RESULTS / 'checkpoints.csv')
    checkpoints = checkpoints[checkpoints.sensitivity == 'primary'].copy()
    checkpoints['policy'] = checkpoints.method.str.split('_').str[1]
    checkpoints['ceiling'] = checkpoints.method.str.replace(r'^checkpoint_(diagnostic|random)_', '', regex=True)
    matched = []
    for (d, profile, ceiling), rows in checkpoints.groupby(['d', 'profile', 'ceiling']):
        paired = rows.pivot(index=['family', 'scm'], columns='policy', values='sw1').dropna()
        difference = (paired.diagnostic - paired.random).rename('delta').reset_index()
        mean, lo, hi, n = bootstrap(difference, 'delta')
        diagnostic = rows[rows.policy == 'diagnostic']
        random = rows[rows.policy == 'random']
        matched.append({'d': int(d), 'profile': profile, 'ceiling': ceiling,
                        'scms': n, 'paired_conditions': int(diagnostic.conditions.sum()),
                        'diagnostic': float(paired.diagnostic.mean()), 'random': float(paired.random.mean()),
                        'paired_delta': mean, 'low': lo, 'high': hi,
                        'diagnostic_updates': float(diagnostic.fitting_updates.mean()),
                        'random_updates': float(random.fitting_updates.mean()),
                        'diagnostic_search_seconds': float(diagnostic.search_gpu_seconds.mean()),
                        'random_search_seconds': float(random.search_gpu_seconds.mean())})
    oracle = []
    for (d, profile), group in primary.groupby(['d', 'profile']):
        seeds = group[group.method == 'oracle'].scm.unique()
        subset = group[group.scm.isin(seeds)]
        oracle.append({'d': int(d), 'profile': profile, 'scms': len(seeds),
                       'means_on_same_scms': {name: float(rows.sw1.mean()) for name, rows in subset.groupby('method')},
                       'uncertainty': 'Unavailable: one SCM per family/profile cell; descriptive subset only'})
    rankings = []
    for (d, family, profile), rows in primary.groupby(['d', 'family', 'profile']):
        means = rows.groupby('method').sw1.mean()
        main = means[[m for m in means.index if m.startswith('M')]]
        rankings.append({'d': int(d), 'family': family, 'profile': profile,
                         'scms': int(rows.scm.nunique()), 'best_observed': main.idxmin(),
                         'means': {k: float(v) for k, v in means.items()}})
    graphs = json.loads((RESULTS / 'illustration_graphs.json').read_text())
    illustrations = []
    for case in graphs:
        paths = {}
        for panel in case['panels']:
            children = {}
            for a, b in panel['graph']['edges']:
                children.setdefault(a, []).append(b)
            queue = [case['target']]; seen = set(queue)
            for node in queue:
                for child in children.get(node, []):
                    if child not in seen: seen.add(child); queue.append(child)
            paths[panel['label']] = case['outcome'] in seen
        illustrations.append({'scm': case['scm'], 'target': case['target'], 'outcome': case['outcome'],
                              'kind': case['kind'], 'directed_path_exists': paths})
    harms = {method: {'conditions': int(len(rows)), 'harm_count': int(rows.harmful.sum()),
                      'retained_count': int(rows.retained.sum())}
             for method, rows in primary[primary.method.isin(['M3', 'M4', 'M5', 'random'])].groupby('method')}
    weights = pd.read_csv(RESULTS / 'mixture_weights.csv')
    weights = weights[(weights.sensitivity == 'primary') & (weights.resource == 'adjusted')]
    weight_summary = [{'d': int(d), 'profile': profile, 'mean_initial_weight_before_audit': float(rows.initial_weight_before_audit.mean()),
                      'min_initial_weight_before_audit': float(rows.initial_weight_before_audit.min()),
                      'max_initial_weight_before_audit': float(rows.initial_weight_before_audit.max())}
                     for (d, profile), rows in weights.groupby(['d', 'profile'])]
    atomic_json(RESULTS / 'interpretation_checks.json', {
        'scope': 'Descriptive post-evaluation analysis; formal contrasts remain the 24 frozen comparisons',
        'source_sha256': file_hash(__file__),
        'inputs': {name: file_hash(RESULTS / name) for name in
                   ['metrics.csv', 'checkpoints.csv', 'mixture_weights.csv', 'illustration_graphs.json']},
        'matched_computation': matched, 'oracle_matched': oracle,
        'cell_rankings': rankings, 'harm_totals': harms, 'mixture_anchors': weight_summary,
        'illustration_paths': illustrations,
    })


if __name__ == '__main__':
    main()
