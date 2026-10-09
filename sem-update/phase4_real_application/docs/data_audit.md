# Recorded wind-tunnel evidence

The [official repository](https://github.com/juangamella/causal-chamber) supplies
the [validation experiments](https://github.com/juangamella/causal-chamber/tree/main/datasets/wt_validate_v1)
and [actuator trajectories](https://github.com/juangamella/causal-chamber/tree/main/datasets/wt_walks_v1).
`tools/acquire.py` pins the repository revision, downloads the real ZIP archives,
and checks their published MD5 plus SHA256. No acquisition generator was executed.
The acquisition protocols are descriptions of previous physical experiments.
CSV measurements are CC BY 4.0; accompanying code is MIT. Cite Gamella, Peters
and Bühlmann, *Nature Machine Intelligence* (2025),
[doi:10.1038/s42256-024-00964-x](https://doi.org/10.1038/s42256-024-00964-x).

The downloaded records contain **28 trajectory files / 891,016 rows** and
**28 validation files / 23,449 rows**, with no missing entries. The trajectory
archive has 16 random-walk files, ten mixed-trajectory files and two regime-jump
files. Random walk 1 contains only 1,016 rows; the other random walks have 10,000.
This differs from the README's ten-seed description and from treating all 16
generator iterations as complete acquisitions. Each regime-jump file has three
counter resets: 34 recorded counter segments across 28 trajectory files, not
34 proven independent acquisitions. The five primary validation files have
699 rows: `validate_load_out` has 49 rather than its protocol's 50.

File names, lengths, median sampling intervals, missingness and hashes are in
`results/acquisitions.csv`. Full schemas, sensor settings, counter-segment
boundaries and time ranges are in ignored `dataset_audit_full.json`. The recorded
timestamps are small elapsed/uptime-like values, inconsistent with the dictionary's
Unix-epoch description. We use within-file time differences, without inventing
calendar dates, cross-file session independence or acquisition chronology.
There is one physical apparatus. Distinct files identify recorded experimental
acquisitions; they do not identify independent physical systems.
Walks 2–16 occupy consecutive recorded clock intervals, with roughly eight seconds
between files. They must not be described as independent acquisition days. The
startup filter increases the separation of retained rows, but does not remove
shared atmospheric drift across the acquisition sequence. Run-resampling results
are conditional sensitivity measures under exchangeability of these files.

The `intervention` indicator marks the first measurement after a SET instruction.
It does not identify a target. `wt_standard_validation_configs.csv` and
`generators/binary_interventions.py` define the target, binary values, fixed
nuisance settings and wait. We check the recorded command against `flag` and the
protocol's low/high assignment in every reserved file. Fan commands use 0.01/1;
hatch uses 0/45 degrees. Other fan/hatch commands remain at their recorded values.
The primary files wait 10 seconds after assignment. The 5/8-second experiments
form a separate secondary panel; immediate hatch experiments are not interpreted
as steady-state model tests. Randomized assignments support total effects under
these operating conditions, not direct edges.

The modeled sensor settings are fixed: current and all pressure OSRs 8,
tachometer resolution 1, current ADC references 1.1, standard open-loop chamber
configuration. Random-walk speaker controls vary. Their microphone OSR is 1;
validation uses 8. The two compatible mixed runs have fixed speaker settings but
only two acquisitions and strongly dependent trajectories. Therefore microphone
measurements are excluded from the main joint model, and recorded acoustic
contrasts are reported separately at OSR 8 and reference 5. No incompatible
microphone distributions are pooled. Electronic-parameter validation experiments
and regime jumps changing sensor settings are excluded from causal actuator tests.

Quality auditing computes missingness without returning measured outcome values
to fitting or selection code. Eligibility uses commands, timestamps and sensor
settings only. Reserved outcomes become available to the evaluation code only
after protocol, selected models and checkpoint hashes are sealed.

Development inspected the first 2,000 rows of compatible fast-1 and slow-2 mixed
runs and all 10,000 rows of random-walk 16. Outlet-speed settling estimates from
six available mixed-run transitions range from 2.8 to 10.3 seconds; this is an
approximate response diagnostic, not a calibrated equipment specification.
The frozen command-window filter limits changes over ten seconds to 0.1 duty
fraction and five hatch degrees, omits the first 15 seconds, and spaces retained
rows by at least three seconds. In the 194 eligible development rows, residual
lag-one autocorrelations after a command-polynomial fit are -0.09/-0.04 for
currents, 0.27/0.44 for speeds and 0.80–0.88 for pressures. Pressure residual SDs
are 3.0–4.5 Pa. Thus a quasi-steady response surrogate is tested, with retained
drift/dependence explicitly limiting its interpretation. It is unsuitable for
claims about transient feedback control. No iid-row confidence interval is used.

The full raw audit, calibration references, actual development arrays and source
protocols remain under `.artifacts/phase4_real_application/`. The preserved
acquisition manifest lists exact pinned-source and archive hashes.
