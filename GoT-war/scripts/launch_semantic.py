from got_war.budget import Budget
b=Budget('.')
b.check(heavy=True,estimated_seconds=180*45,reserve_seconds=5*3600)
r=b.launch(['bash','-c','PYTHONPATH=src .venv/bin/python scripts/semantic_campaign.py'],'application_semantic')
print(r['label'],r['pid'])
