"""One entry point for reproducible execution and read-only analysis."""
import argparse,json
from pathlib import Path
from .budget import Budget


def main():
    parser=argparse.ArgumentParser(description='Source-grounded structural programs with a persisted elapsed deadline')
    parser.add_argument('command',choices=['environment','corpus','benchmark-build','pilot','generate','evaluate','attribute','figures','run','resume','status'])
    parser.add_argument('--root',default='.')
    parser.add_argument('--split',choices=['development','calibration','test'])
    args=parser.parse_args();root=Path(args.root).resolve()
    if not (root/'PLAN.md').exists():
        if (root/'GoT-war/PLAN.md').exists():root=root/'GoT-war'
        else:parser.error('Use the existing GoT-war directory containing PLAN.md')
    if args.command=='status':print(json.dumps({'remaining_seconds':Budget(root).remaining()},indent=2));return
    if args.command=='environment':
        from .environment import collect
        print(json.dumps(collect(root),indent=2));return
    if args.command=='corpus':
        from .sources import build
        from .retrieval import freeze_packets
        Budget(root).check(heavy=True);print(build(root));print(freeze_packets(root));return
    if args.command=='benchmark-build':
        from .benchmark import build
        print(build(root));return
    if args.command=='pilot':
        from .experiments import pilot
        print(pilot(root));return
    if args.command=='generate':
        from .application import run_application
        Budget(root).check(heavy=True);run_application(root);return
    if args.command in ('run','resume'):
        from .experiments import run_benchmark
        from .application import run_application
        from .application_baselines import run as application_baselines
        from .explanation_audit import run as audit_explanations
        Budget(root).check(heavy=True)
        run_benchmark(root,args.split);run_application(root)
        application_baselines(root);audit_explanations(root)
    if args.command in ('evaluate','attribute','run','resume'):
        from .evaluation import evaluate
        print(json.dumps(evaluate(root),indent=2))
    if args.command in ('attribute','run','resume'):
        from .verification import verify
        print(json.dumps(verify(root),indent=2))
    if args.command in ('figures','run','resume'):
        from .visualization import render
        print('Networks rendered:',render(root))

if __name__=='__main__':main()
