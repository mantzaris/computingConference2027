"""Resume the frozen evaluator with a heterogeneous-row CSV export adapter.

The frozen numerical implementation and prediction/cache identities are unchanged.
Projection sensitivity exists only for selected endpoints/systems, so the output
schema must include keys from every row. Missing metrics remain blank, not zero.
"""
import csv
from pathlib import Path


def write_csv(path, rows):
    if not rows:
        return
    keys = list(dict.fromkeys(key for row in rows for key in row))
    temporary = Path(str(path) + '.tmp')
    with open(temporary, 'w', newline='') as stream:
        writer = csv.DictWriter(stream, keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: format(value, '.9g') if isinstance(value, float)
                             else value for key, value in row.items()})
    temporary.replace(path)


def main():
    from sem_update.phase3 import evaluation
    from sem_update.phase3.runtime import (RESULTS, setup, freeze_guard,
                                           atomic_json, read_json, file_hash)
    setup()
    protocol = freeze_guard()
    record = {
        'scope': 'CSV serialization only; no change to predictions, metrics, fits, selections, seeds or protocol',
        'reason': 'Original first-row schema omitted later sw1_64 and sw1_1024 fields',
        'frozen_scientific_hash': protocol['scientific_hash'],
        'frozen_selections_sha256': file_hash(RESULTS / 'frozen_selections.json'),
        'numerical_evaluator_sha256': file_hash(evaluation.__file__),
        'adapter_sha256': file_hash(__file__),
        'missing_metric_representation': 'blank CSV cell, never zero',
        'precision': 'unchanged nine significant decimal digits',
        'failed_attempt_preserved': True,
    }
    destination = RESULTS / 'serialization_adapter.json'
    if destination.exists() and read_json(destination) != record:
        raise RuntimeError('Serialization adapter changed during resume')
    atomic_json(destination, record)
    evaluation.write_csv = write_csv
    evaluation.main()


if __name__ == '__main__':
    main()
