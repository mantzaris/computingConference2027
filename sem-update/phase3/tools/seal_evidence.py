"""Snapshot executed code/curated outputs, then inventory and archive evidence.

Run only after the coordinator completes. Redirect this tool's stdout outside
the phase3 artifact root so an archive log cannot mutate an inventoried input.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile


def main():
    project = Path(__file__).resolve().parents[2]
    root = Path(os.environ.get('SEM_UPDATE_ARTIFACT_ROOT', project / '.artifacts/phase3')).resolve()
    state = json.loads((root / 'runs/main_session.json').read_text())
    if state['status'] != 'complete':
        raise RuntimeError('Coordinator is not complete')
    snapshot = root / 'archives/executed_code_and_outputs.tar.gz'
    if snapshot.exists():
        raise RuntimeError('Executed snapshot already exists; preserve and verify it')
    files = []
    for name in ['src', 'scripts', 'requirements.lock', 'phase3/tools', 'phase3/tests',
                 'phase3/configs', 'phase3/results', 'phase3/paper']:
        path = project / name
        files.extend([path] if path.is_file() else
                     [p for p in path.rglob('*') if p.is_file() and '__pycache__' not in p.parts])
    with tarfile.open(snapshot, 'w:gz') as archive:
        for path in sorted(set(files)):
            archive.add(path, arcname=str(path.relative_to(project)), recursive=False)
    record = {'path': str(snapshot.relative_to(root)), 'bytes': snapshot.stat().st_size,
              'sha256': hashlib.sha256(snapshot.read_bytes()).hexdigest(), 'files': len(set(files)),
              'scope': 'Executed code, locked dependency specification, configurations, tests and final curated numeric/figure outputs; final narrative and preservation records live in Git',
              'scientific_source': 'Frozen pre-evaluation source and pilot source are separately preserved'}
    text = json.dumps(record, indent=2) + '\n'
    (project / 'phase3/results/executed_snapshot.json').write_text(text)
    (root / 'archives/executed_snapshot.json').write_text(text)
    for command in ['artifact_manifest.py', 'archive_evidence.py']:
        args = [sys.executable, str(project / 'phase3/tools' / command)]
        if command == 'archive_evidence.py': args.append('create')
        subprocess.run(args, check=True)


if __name__ == '__main__':
    main()
