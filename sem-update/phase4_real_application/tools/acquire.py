"""Download real records and pinned acquisition protocols; never operate equipment."""
import hashlib
import json
import os
from pathlib import Path
import urllib.request
import zipfile

PROJECT = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get('SEM_UPDATE_ARTIFACT_ROOT', PROJECT / '.artifacts/phase4_real_application'))
DATASETS = {'wt_validate_v1': 'bde214eb50abc801307bf7d4aadcafc9',
            'wt_walks_v1': '19bb4e92cbe0b8dff49299b9b509ac36'}

def fetch(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        temporary = path.with_suffix(path.suffix + '.partial')
        urllib.request.urlretrieve(url, temporary)
        temporary.replace(path)

def sha(path, algorithm='sha256'):
    h = hashlib.new(algorithm)
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(2**20), b''):
            h.update(block)
    return h.hexdigest()

def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    pin = ROOT / 'raw/repository_revision.json'
    provenance=PROJECT/'phase4_real_application/results/data_provenance.json'
    revision=json.loads(provenance.read_text())['revision'] if provenance.exists() else 'main'
    fetch('https://api.github.com/repos/juangamella/causal-chamber/commits/'+revision, pin)
    revision = json.loads(pin.read_text())['sha']
    manifest = {'repository': 'https://github.com/juangamella/causal-chamber',
                'revision': revision, 'datasets': {}, 'outcomes_opened': False}
    for name, expected in DATASETS.items():
        paths = ['README.md', 'variables.csv', 'LICENSE_DATASETS.txt', 'LICENSE_SOFTWARE.txt']
        paths += (['wt_standard_validation_configs.csv', 'generators/binary_interventions.py']
                  if name == 'wt_validate_v1' else
                  ['generators/actuators_random_walk.py', 'generators/loads_hatch_mix.py',
                   'generators/regime_jumps.py', 'regimes_targets.py'])
        sources = {}
        for file in paths:
            url = f'https://raw.githubusercontent.com/juangamella/causal-chamber/{revision}/datasets/{name}/{file}'
            target = ROOT / 'protocols' / name / file
            fetch(url, target)
            sources[file] = {'url': url, 'sha256': sha(target)}
        url = f'https://causalchamber.s3.eu-central-1.amazonaws.com/downloadables/{name}.zip'
        archive = ROOT / 'raw' / (name + '.zip')
        fetch(url, archive)
        if sha(archive, 'md5') != expected:
            raise ValueError('Published archive checksum mismatch: ' + name)
        destination = ROOT / 'raw' / name
        destination.mkdir(exist_ok=True)
        with zipfile.ZipFile(archive) as z:
            for member in z.infolist():
                target = (destination / member.filename).resolve()
                if destination.resolve() not in target.parents:
                    raise ValueError('Unsafe archive member')
            z.extractall(destination)
            files = [{'name': m.filename, 'bytes': m.file_size} for m in z.infolist()]
        manifest['datasets'][name] = {'url': url, 'md5': expected, 'sha256': sha(archive),
                                     'bytes': archive.stat().st_size, 'members': files, 'protocols': sources}
    (ROOT / 'acquisition_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({n: {'archive_bytes': r['bytes'], 'members': len(r['members'])}
                      for n, r in manifest['datasets'].items()}))

if __name__ == '__main__':
    main()
