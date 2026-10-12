#!/usr/bin/env python3
"""Authenticated SSH-shell transport (no SCP/SFTP); connection settings stay private."""
import argparse, base64, io, json, pathlib, re, shlex, sys, tarfile, time, uuid
import pexpect
ROOT = pathlib.Path(__file__).resolve().parents[1]

class Remote:
    def __init__(self):
        self.cfg = json.loads((ROOT/'.private/transport.json').read_text())
        self.root = self.cfg['remote_root']
        self.s = pexpect.spawn('ssh', ['-tt','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no','-o','ConnectTimeout=20','-o','ServerAliveInterval=30','-i',self.cfg['identity'],self.cfg['target']], encoding='utf-8', timeout=60, maxread=65536)
        self.s.expect(r'[#\$] ')
        self.s.sendline("stty -echo; export PS1='' PS2=''; printf '\\nGOT_READY\\n'")
        self.s.expect('\r\nGOT_READY\r\n')
    def python(self, code, timeout=180):
        tag='GOT_RESULT_'+uuid.uuid4().hex
        encoded=base64.b64encode(code.encode()).decode()
        self.s.sendline("python3 - <<'GOT_TRANSPORT_PY'")
        self.s.sendline('import base64,traceback')
        self.s.sendline('try:')
        self.s.sendline(' exec(base64.b64decode(')
        for start in range(0,len(encoded),1800): self.s.sendline(repr(encoded[start:start+1800]))
        self.s.sendline(' ))')
        self.s.sendline('except Exception: traceback.print_exc()')
        self.s.sendline('print('+repr(tag)+')')
        self.s.sendline('GOT_TRANSPORT_PY')
        self.s.expect(tag, timeout=timeout)
        return re.sub(r'\x1b\[[0-9;?]*[A-Za-z]', '', self.s.before).replace('\r','').strip()
    def command(self, cmd, timeout=180):
        code='import subprocess\nr=subprocess.run('+repr(cmd)+',shell=True,cwd='+repr(self.root)+',stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout='+str(timeout-5)+')\nprint(r.stdout.decode(errors="replace"))\nprint("EXIT",r.returncode)'
        return self.python(code,timeout)
    def put(self, paths):
        out=io.BytesIO()
        with tarfile.open(fileobj=out,mode='w:gz') as tar:
            for name in paths:
                p=ROOT/name
                if p.is_dir():
                    for f in p.rglob('*'):
                        if f.is_file() and not any(x in f.parts for x in ('__pycache__','.venv','.cache')) and ('.private' not in f.parts or name == '.private/packets'):
                            tar.add(str(f),arcname=str(f.relative_to(ROOT)))
                else: tar.add(str(p),arcname=name)
        payload=base64.b64encode(out.getvalue()).decode()
        code='import base64,io,tarfile,pathlib\nr=pathlib.Path('+repr(self.root)+');r.mkdir(parents=True,exist_ok=True)\np=base64.b64decode('+repr(payload)+')\nwith tarfile.open(fileobj=io.BytesIO(p),mode="r:gz") as t:\n for m in t.getmembers():\n  assert not m.issym() and not m.islnk() and not m.name.startswith("/") and ".." not in pathlib.PurePosixPath(m.name).parts\n t.extractall(r,filter="data")\nprint("Uploaded",len(p),"bytes")'
        return self.python(code)
    def pull(self, paths):
        code='import io,tarfile,pathlib,base64\nr=pathlib.Path('+repr(self.root)+')\nb=io.BytesIO()\nwith tarfile.open(fileobj=b,mode="w:gz") as t:\n for name in '+repr(paths)+':\n  p=r/name\n  if not p.exists(): continue\n  files=[p] if p.is_file() else p.rglob("*")\n  for f in files:\n   if f.is_file() and not f.is_symlink() and "__pycache__" not in f.parts:\n    t.add(f,arcname=str(f.relative_to(r)))\nprint("GOT_PAYLOAD:"+base64.b64encode(b.getvalue()).decode())'
        response=self.python(code,300)
        payload=response.split('GOT_PAYLOAD:',1)[1].strip()
        binary=base64.b64decode(payload)
        with tarfile.open(fileobj=io.BytesIO(binary),mode='r:gz') as t:
            for m in t.getmembers():
                assert not m.issym() and not m.islnk() and not m.name.startswith('/') and '..' not in pathlib.PurePosixPath(m.name).parts
                dest=ROOT/m.name
                assert ROOT in dest.resolve().parents
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes(t.extractfile(m).read())
        (ROOT/'runs/last_sync.json').write_text(json.dumps({'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'bytes':len(binary),'paths':paths},indent=2)+'\n')
        return 'Synchronized %d compressed bytes'%len(binary)
    def close(self):
        self.s.sendline('exit');self.s.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['put','pull','cmd','python']);p.add_argument('args',nargs='+');p.add_argument('--timeout',type=int,default=180);a=p.parse_args()
    r=Remote()
    try:
        if a.action=='put': print(r.put(a.args))
        elif a.action=='pull': print(r.pull(a.args))
        elif a.action=='python': print(r.python(pathlib.Path(a.args[0]).read_text(),a.timeout))
        else: print(r.command(a.args[0],a.timeout))
    finally:r.close()
