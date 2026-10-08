"""Regression for exporting mixed endpoint/projection-sensitivity rows."""
import csv
import importlib.util
from pathlib import Path


def test_optional_sensitivity_fields_are_preserved(tmp_path):
    script = Path(__file__).resolve().parents[1] / 'tools/evaluate_frozen.py'
    spec = importlib.util.spec_from_file_location('phase3_metric_export', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows = [
        {'endpoint': 'T1', 'sw1': 0.123456789123, 'nll': None},
        {'endpoint': 'T2', 'sw1': 0.2, 'sw1_64': 0.21, 'sw1_1024': 0.19},
        {'endpoint': 'T3', 'sw1': 0.3, 'nll': 1.2},
    ]
    destination = tmp_path / 'metrics.csv'
    module.write_csv(destination, rows)
    first = destination.read_bytes()
    with destination.open() as stream:
        actual = list(csv.DictReader(stream))
    assert actual[0]['sw1'] == '0.123456789'
    assert actual[0]['sw1_64'] == actual[0]['sw1_1024'] == actual[0]['nll'] == ''
    assert actual[1]['sw1_64'] == '0.21' and actual[1]['sw1_1024'] == '0.19'
    assert actual[2]['nll'] == '1.2' and actual[2]['sw1_64'] == ''
    assert not Path(str(destination) + '.tmp').exists()
    module.write_csv(destination, rows)
    assert destination.read_bytes() == first
