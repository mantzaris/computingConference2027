# Data acquisition

Raw and processed arrays are excluded from Git. Run, from sem-update:

```bash
export SEM_UPDATE_ARTIFACT_ROOT="$PWD/.artifacts"
export PYTHONPATH="$PWD/src"
.artifacts/venv/bin/python -m sem_update.cli prepare-data
```

The command downloads the public Causal Chambers dataset through its authors'
Python interface, verifies its download checksum, computes per-file SHA-256
hashes and writes a compact schema manifest. See `docs/dataset_audit.md` for
subset, assignment, measurement and split limitations. The dataset's CC BY 4.0
license requires attribution to Gamella, Peters and Bühlmann (2025),
DOI [10.1038/s42256-024-00964-x](https://doi.org/10.1038/s42256-024-00964-x).

Synthetic equations, reference graphs and full arrays are separate artifacts.
Learner views expose fit, early-stop, search and audit roles; final evaluation
loads a separate sealed design only after the protocol and selected models are
frozen. Public metadata prompts are constructed without graph or outcome input.
