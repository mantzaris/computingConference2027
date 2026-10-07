# Causal Chambers audit

Acquired `lt_interventions_standard_v1` through `causalchamber==0.2.8` into
`.artifacts/data/raw/`. File hashes, exact columns, missingness and experiment
counts are in `results/curated/dataset_audit.json`. Public dataset license: CC BY
4.0. Source: [authors' dataset page and generator](https://github.com/juangamella/causal-chamber/tree/main/datasets/lt_interventions_standard_v1).
The original assignment generator and variables.csv are preserved as artifacts.

The authors' [IID discovery notebook](https://github.com/juangamella/causal-chamber-paper/blob/main/case_studies/causal_discovery_iid.ipynb)
uses 20 physical variables. It includes measurement-setting interventions and
selects some hyperparameters using reference graph metrics. Those choices are
not copied into our protocol.

Subset chosen from physical scope: `red`, `green`, `blue`, `current`, `pol_1`,
`angle_1`. The source-current readout and rotary-position readout avoid the
varying local LED controls that would need to accompany optical intensity
sensors. RGB plus source current needs three parents at most under the
documented physical description. Relevant sensor reference voltages and
oversampling settings must remain fixed. Sensor readings are not interpreted as
physical causes of one another. Units are PWM settings, raw ADC counts and
angular settings, retaining physical-scale transforms. See the authors'
[variable and physical-effect documentation](https://arxiv.org/html/2404.11341v2).

The reference regime randomizes actuators; it is not a natural observational
population. RGB mid-range regimes supply non-test interventions. Complete RGB
strong-range regimes are reserved for T2; later disjoint mid-range rows provide
T1. No real T3 claim is made. Sensor-gain, exposure and voltage changes are
excluded. Each regime is one acquisition run, not an independent apparatus.

Training-only inspection found ~0.395 s median sampling intervals, quantized ADC
counts, and coarse realized polarizer settings. Fixed uniform dequantization is
used (one count for PWM/ADC, 0.9 degree for the position setting). This is an
approximate measurement model, not recovery of latent physical values. Ordered
blocks and at least 64-row gaps separate roles; 10-row reporting blocks support
conditional, descriptive uncertainty. Autocorrelation checks use only the first
4096 reference rows. B=400 counts the non-test rows in each additional mid-RGB
target regime (1,200 total). The 6,656 non-test reference rows also arise from
randomized actuator assignments: the real study therefore reports 7,856 total
non-test experimental observations, with both components explicit. It does not
describe B=400 as the total physical experimentation budget.

Limitations: one physical apparatus; serial dependence and common electronics
may remain; position-setting quantization differs from nominal command spacing;
strong RGB settings extrapolate beyond fitting support. Treat this as predictive
validation under documented actuator assignment, with conditional causal
interpretation, not established causal sufficiency or a graph-identification
benchmark. Human review of this scope is pending.

Exact source verification: the previously used dataset protocol files match
repository commit `0c8a77ea14bd4437b1fdd79adc1aa91ac2342569` byte for byte.
The authors' IID notebook matches paper repository commit
`e20e785ef4ffe797e9a2028b6b9d67f8498831cf`. URL and SHA-256 comparisons are in
`results/curated/data_source_revision.json`; no data or protocol bytes changed.
