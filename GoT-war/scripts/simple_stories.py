"""Offline one-command reproduction; --generate uses an already running endpoint."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from got_war import simple_stories
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--generate',action='store_true')
a=p.parse_args()
if a.generate:simple_stories.generate(ROOT)
else:simple_stories.reproduce(ROOT)
