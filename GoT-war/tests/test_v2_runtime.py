import json
import signal
import sys
from datetime import datetime, timezone, timedelta
import pytest
from got_war import budget as module


def budget_for_test(root):
    (root/'configs').mkdir()
    end = (datetime.now(timezone.utc)+timedelta(seconds=30)).isoformat()
    (root/'configs/budget.json').write_text(json.dumps({'campaign_id':'identity_test',
        'hard_deadline':end, 'soft_deadline':end, 'no_heavy_jobs_after':end}))
    return module.Budget(root)


def test_identity_capture_retries_before_registering(tmp_path, monkeypatch):
    b = budget_for_test(tmp_path)
    real = module.process_birth
    calls = []
    def flaky(pid):
        calls.append(pid)
        return None if len(calls)<3 else real(pid)
    monkeypatch.setattr(module, 'process_birth', flaky)
    task = b.launch([sys.executable, '-c', 'import time; time.sleep(30)'], 'owned')
    try:
        assert task['birth'] is not None and len(calls)>=3
        assert b.stop_owned(signal.SIGKILL)==['owned']
    finally:
        b.stop_owned(signal.SIGKILL)


def test_unverifiable_launch_is_not_registered(tmp_path, monkeypatch):
    b = budget_for_test(tmp_path)
    monkeypatch.setattr(module, 'process_birth', lambda pid: None)
    with pytest.raises(RuntimeError, match='identity could not be verified'):
        b.launch([sys.executable, '-c', 'import time; time.sleep(30)'], 'unverified')
    assert not (b.run/'processes.json').exists()
def test_concurrent_checkpoint_writers_keep_complete_json(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    import json
    from got_war.budget import atomic_json
    destination=tmp_path/'shared_summary.json'
    def write(worker):
        for i in range(20):atomic_json(destination,{'worker':worker,'iteration':i,'payload':'x'*4096})
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(write,range(4)))
    result=json.loads(destination.read_text())
    assert result['worker'] in range(4) and result['iteration']==19 and result['payload']=='x'*4096
    assert list(tmp_path.glob('*.tmp.*'))==[]

