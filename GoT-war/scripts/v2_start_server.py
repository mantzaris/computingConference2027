"""Start only the cached project model after checking the existing GPU host."""
import json
from pathlib import Path
import subprocess
import requests
from got_war.v2.runtime import budget
from got_war.budget import atomic_json

root = Path(__file__).resolve().parents[1]
b = budget(root)
try:
    response = requests.get('http://127.0.0.1:8765/v1/models', timeout=3)
except requests.ConnectionError:
    response = None
if response is not None:
    raise RuntimeError('An endpoint already exists; inspect its owner before starting another service')
compute = subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader']).decode().strip()
if compute:
    raise RuntimeError('GPU has existing compute processes; inspect before allocating the model')
model = json.loads((root/'configs/models.json').read_text())
command = ['env', 'HF_HUB_ENABLE_HF_TRANSFER=0', 'HF_HUB_OFFLINE=1', 'HF_HOME='+str(root/'.cache/huggingface'),
           str(root/'.venv/bin/vllm'), 'serve', model['primary'], '--revision', model['revision'],
           '--host', '127.0.0.1', '--port', '8765',
           '--max-model-len', str(model['max_model_len']), '--gpu-memory-utilization', str(model['gpu_memory_utilization']),
           '--max-num-seqs', str(model['max_num_seqs']), '--dtype', model['dtype'], '--enforce-eager', '--disable-log-requests']
number=len(list(b.run.glob('server_launch*.json')))
item = b.launch(command, 'v2_model_server_'+str(number))
atomic_json(b.run/('server_launch_%02d.json'%number), {'process':item, 'model':model, 'cache_only':True})
print(json.dumps(item))
