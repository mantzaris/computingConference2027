"""Reuse the existing SSH route for version-2-only deployment and checkpoints."""
import argparse
import json
import time
from datetime import datetime, timezone
from remote import Remote, ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['put', 'pull', 'sync', 'command'])
    parser.add_argument('items', nargs='*')
    args = parser.parse_args()
    cfg = json.loads((ROOT / 'configs/budget_v2.json').read_text())
    run = 'runs/' + cfg['campaign_id']
    while True:
        # A manual final pull may have closed the campaign while this worker
        # slept. Do not overwrite newer local publication artifacts afterward.
        if args.action == 'sync' and (ROOT/run/'COMPLETE').exists():
            return
        if args.action == 'sync' and datetime.now(timezone.utc) >= datetime.fromisoformat(cfg['hard_deadline']):
            return
        remote = None
        try:
            remote = Remote()
            remote.s.delaybeforesend = .005
            if args.action == 'put':
                print(remote.put(args.items), flush=True)
            elif args.action == 'command':
                print(remote.command(args.items[0]), flush=True)
            else:
                print(datetime.now(timezone.utc).isoformat(), remote.pull(
                    [run, 'results/v2', 'data/manifests/v2_sources.json', '.private/prompts_v2'],
                    sync_record=run+'/sync.json'), flush=True)
        except Exception as error:
            print('V2_TRANSPORT_FAILURE', type(error).__name__, str(error)[:300], flush=True)
            if args.action != 'sync':
                raise
        finally:
            if remote:
                remote.close()
        if args.action != 'sync' or (ROOT/run/'COMPLETE').exists():
            return
        time.sleep(cfg['sync_interval_seconds'])


if __name__ == '__main__':
    main()
