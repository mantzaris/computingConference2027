"""Make the declared local graph views readable without changing their content."""
import copy
import math
from pathlib import Path
import shutil
from sem_update.phase3.runtime import root, RESULTS, read_json, atomic_json, digest, file_hash


def content_without_layout(cases):
    result = copy.deepcopy(cases)
    for case in result:
        case.pop('local_positions')
    return digest(result)


def main():
    source = RESULTS / 'illustration_graphs.json'
    report_path = RESULTS / 'visual_review.json'
    if report_path.exists():
        report = read_json(report_path)
        if file_hash(source) != report['graph_input_after_sha256']:
            raise RuntimeError('Reviewed graph input changed; inspect before replacing it')
        return
    previous = root() / 'paper/pre_visual_review'
    previous.mkdir(parents=True, exist_ok=True)
    source_hash = file_hash(source)
    shutil.copy2(source, previous / source.name)
    # Preserve every initial vector/preview and its existing reproduction record.
    shutil.copytree(root() / 'paper/figures', previous / 'figures', dirs_exist_ok=True)
    for name in ('figure_manifest.json', 'plot_reproduction_check.json'):
        path = RESULTS / name
        if path.exists():
            shutil.copy2(path, previous / name)
    for name in ('plot-reproduction.log',):
        path = root() / 'logs' / name
        if path.exists():
            shutil.copy2(path, previous / name)
    cases = read_json(source)
    unchanged = content_without_layout(cases)
    separation = []
    for case in cases:
        nodes = case['local_nodes']
        # Keep the declared distance/label node order and place it clockwise.
        # This avoids coincident spring-layout positions of symmetric nodes.
        positions = {str(node): [math.cos(math.pi / 2 - 2 * math.pi * i / len(nodes)),
                                math.sin(math.pi / 2 - 2 * math.pi * i / len(nodes))]
                     for i, node in enumerate(nodes)}
        case['local_positions'] = positions
        points = list(positions.values())
        minimum = min(math.dist(a, b) for i, a in enumerate(points) for b in points[i + 1:])
        assert minimum >= 2 * math.sin(math.pi / len(nodes)) - 1e-12
        separation.append({'scm': case['scm'], 'nodes': len(nodes), 'minimum_separation': minimum})
    assert content_without_layout(cases) == unchanged
    atomic_json(source, cases)
    atomic_json(report_path, {
        'reason': 'Visual inspection found overlapping local node labels in the initial spring layout',
        'change': 'Shared circular local positions in the original declared node order; whole-graph positions unchanged',
        'unchanged': 'All node subsets, target/outcome choices, graph edges, component weights, response values and scientific metrics',
        'content_without_local_layout_sha256': unchanged,
        'graph_input_before_sha256': source_hash,
        'graph_input_after_sha256': file_hash(source),
        'originals_preserved': str(previous.relative_to(root())),
        'local_separation_checks': separation,
        'source_sha256': file_hash(__file__),
        'harm_axis': 'Final reporting sets a zero-based frequency range using the plotted confidence bounds; numeric inputs are unchanged',
    })


if __name__ == '__main__':
    main()
