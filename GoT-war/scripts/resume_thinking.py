"""Resume cached source review with explicit, conservative quote alignment."""
import json
from pathlib import Path
from got_war.budget import Budget,process_birth,atomic_json
b=Budget('.')
old=next(p for p in reversed(json.loads((b.run/'processes.json').read_text())) if p['label'].startswith('application_thinking'))
stat=Path('/proc/%s/stat'%old['pid'])
if process_birth(old['pid'])==old['birth'] and stat.exists() and stat.read_text().split(') ',1)[1].split()[0]!='Z':
    raise RuntimeError('Prior application worker is still active')
for failure in (b.run/'application').glob('*/failure.json'):
    saved=failure.with_name('literal_failure_before_%s.json'%old['pid'])
    if not saved.exists():failure.rename(saved)
r=b.launch(['bash','-c','PYTHONPATH=src .venv/bin/python scripts/modular_application.py'],'application_thinking_aligned')
atomic_json(b.run/'span_alignment_revision.json',{'job':r,'change':'Copy matching contiguous lexical words from the selected source paragraph, preserving source punctuation. An explicit ellipsis may yield one literal fragment, never a joined quotation. Original generated quotations and failed exact-string checks are retained. No synonyms or missing words are inferred.'})
print(r['label'],r['pid'])
