#!/usr/bin/env python3
"""Synchronize durable results every 20 minutes without relying on the chat connection."""
import json,time,traceback
from datetime import datetime,timezone
from pathlib import Path
from remote import Remote,ROOT
cfg=json.loads((ROOT/'configs/budget.json').read_text())
while datetime.now(timezone.utc)<datetime.fromisoformat(cfg['hard_deadline']):
    try:
        r=Remote()
        try:print(datetime.now(timezone.utc).isoformat(),r.pull(['runs','results','configs/models.json']),flush=True)
        finally:r.close()
    except Exception as e:print('SYNC_ERROR',type(e).__name__,str(e)[:500],flush=True)
    if (ROOT/'runs'/cfg['campaign_id']/'COMPLETE').exists():break
    time.sleep(1200)
