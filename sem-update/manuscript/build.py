"""Compile the draft using bundled assets, without experimental work."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
BUILD = HERE / 'build'
PDF = HERE / 'draft.pdf'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh-figures', action='store_true',
                        help='Regenerate figures from the existing repository evidence before compiling.')
    args = parser.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update(TEXINPUTS=str(HERE) + ':',
               TEXMFVAR=str(BUILD / 'texmf-var'), TEXMFCONFIG=str(BUILD / 'texmf-config'),
               MPLCONFIGDIR=str(BUILD / 'matplotlib'), CUDA_VISIBLE_DEVICES='')
    manifest_path = HERE / 'assets.json'
    manifest = json.loads(manifest_path.read_text())
    if args.refresh_figures:
        subprocess.run([sys.executable, str(HERE / 'figures.py')], env=env, check=True)
        for name, asset in manifest['assets'].items():
            if asset['kind'] == 'figure':
                data = (PROJECT / asset['source']).read_bytes()
                (HERE / name).write_bytes(data)
                asset.update(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    for name, asset in manifest['assets'].items():
        data = (HERE / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == asset['sha256'], 'Asset checksum mismatch: ' + name
    command = ['xelatex', '-interaction=nonstopmode', '-halt-on-error',
               '-file-line-error', '-recorder', '-output-directory=' + str(BUILD), 'main.tex']
    for stage in range(3):
        result = subprocess.run(command, cwd=HERE, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (BUILD / ('latex%d.stdout' % stage)).write_bytes(result.stdout)
        if result.returncode:
            print(result.stdout.decode(errors='replace')[-8000:])
            raise SystemExit(result.returncode)
    subprocess.run(['pdftotext', '-layout', str(BUILD / 'main.pdf'),
                    str(BUILD / 'manuscript.txt')], check=True)
    PDF.write_bytes((BUILD / 'main.pdf').read_bytes())
    print(PDF)

if __name__ == '__main__':
    main()
