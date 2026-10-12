"""Actual-host process-scope check using only disposable test children."""
import json
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
from got_war import budget as module
from got_war.v2.runtime import budget

root=Path(__file__).resolve().parents[1];b=budget(root)
with tempfile.TemporaryDirectory(dir=root/'.cache',prefix='v2_supervision_') as temp:
    test=Path(temp);(test/'configs').mkdir();end=(datetime.now(timezone.utc)+timedelta(seconds=2)).isoformat()
    (test/'configs/budget.json').write_text(json.dumps({'campaign_id':'scope_probe','hard_deadline':end,'soft_deadline':end,'no_heavy_jobs_after':end}))
    guard=module.Budget(test)
    other=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],start_new_session=True)
    actual=module.process_birth;calls=[]
    def transient(pid):
        calls.append(pid)
        return None if len(calls)<3 else actual(pid)
    try:
        with patch.object(module,'process_birth',transient):
            task=guard.launch([sys.executable,'-c','import time; time.sleep(30)'],'owned_probe')
        (guard.run/'completed_artifact').write_text('preserve')
        time.sleep(2.1)
        expired=False
        try:guard.check()
        except RuntimeError:expired=True
        stopped=guard.stop_owned(signal.SIGKILL)
        result={'at':datetime.now(timezone.utc).isoformat(),'host':'actual RunPod','identity_retry_calls':len(calls),
            'registered_identity_nonnull':task['birth'] is not None,'deadline_enforced':expired,'owned_stopped':stopped==['owned_probe'],
            'unregistered_test_child_survived':other.poll() is None,'artifact_preserved':(guard.run/'completed_artifact').read_text()=='preserve'}
        assert all(result[k] for k in ('registered_identity_nonnull','deadline_enforced','owned_stopped','unregistered_test_child_survived','artifact_preserved'))
    finally:
        guard.stop_owned(signal.SIGKILL);other.terminate();other.wait(timeout=5)
module.atomic_json(b.run/'supervision_probe.json',result)
print(json.dumps(result,indent=2))
