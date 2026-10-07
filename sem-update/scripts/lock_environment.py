"""Record the tested dependency closure, excluding unrelated container packages."""
import importlib.metadata as md
from pathlib import Path
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

roots=['torch','numpy','scipy','pandas','networkx','matplotlib','nflows','pyyaml',
       'pytest','transformers','accelerate','huggingface-hub','causalchamber',
       'pypdf','setuptools','packaging']
pending=list(roots)
found={}
while pending:
    name=canonicalize_name(pending.pop())
    if name in found:
        continue
    dist=md.distribution(name)
    found[name]=dist.version
    for text in dist.requires or []:
        req=Requirement(text)
        if req.marker is None or req.marker.evaluate({'extra':''}):
            if md.version(req.name) not in req.specifier:
                raise RuntimeError('installed dependency does not satisfy '+text)
            pending.append(req.name)
target=Path(__file__).resolve().parents[1]/'requirements.lock'
target.write_text('# Tested Python 3.12 / Linux x86_64 / CUDA 12.8 environment.\n'
                  '--extra-index-url https://download.pytorch.org/whl/cu128\n'+
                  '\n'.join(name+'=='+found[name] for name in sorted(found))+'\n')
print(f'Locked {len(found)} installed distributions in {target}')
