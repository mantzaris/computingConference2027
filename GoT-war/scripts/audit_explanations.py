"""Run the source-model explanation audit after application inference."""
import sys
from got_war.explanation_audit import run
run(sys.argv[1] if len(sys.argv)>1 else '.')
