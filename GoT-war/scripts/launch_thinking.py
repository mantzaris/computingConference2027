from got_war.budget import Budget
b=Budget('.')
b.check(heavy=True,estimated_seconds=180*70,reserve_seconds=5*3600)
r=b.launch(['bash','-c','PYTHONPATH=src .venv/bin/python scripts/thinking_campaign.py'],'application_thinking')
print(r['label'],r['pid'])
