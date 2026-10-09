# Phase-four protocol

This is a new application of the existing methods, preserving all three previous
studies and their negative findings. The application asks whether recorded fan
and hatch commands predict measured pressure, speed and current responses under
changed operating conditions. Microphone contrasts form a separate descriptive
panel because the usable training and test sensor configurations differ.

`results/protocol.json` is the machine-readable freeze; it hashes science source,
configuration, data partitions, LLM proposal and final assignment design. The
protocol must be frozen before main fitting. All selections/checkpoints are then
sealed before final measured outcomes are evaluated. No reference adjacency is
used for initialization, search, LLM prompts, tuning or figures.

Acquisition roles are fixed: random walks 2–9 fit, 10–11 early stopping, 12–13
search, 14 calibration and 15 one-time audit. Random walk 16 is development.
Whole acquisition files remain in one role. Command-space bins preserve joint
recorded assignments; no independent resampling of correlated command tuples.
The final primary panel is `validate_load_in`, `validate_load_in_mic`,
`validate_load_out`, `validate_load_out_mic`, `validate_hatch_rpms` (699 measurements,
five acquisition files). This tests transfer from slowly varying commands to
randomized binary assignment at fixed nuisance commands, on the same apparatus.
It is a changed acquisition/distribution and operating-setting test. Every target
is already visible in training: no unseen-target or new-apparatus claim.

The modeling choice is a **quasi-steady predictive surrogate**, not an established
instantaneous DAG. Eligible command histories and retained temporal dependence
are documented in the audit. The primary test waits ten seconds; shorter waits
are labeled separately. Dynamic histories cannot be transported at a common
sample lag between the ~0.3-second walks and irregular 5–11-second randomized
records without additional modeling assumptions. We restrict the scientific
claim to settled-response prediction and test its reliability directly, rather
than infer transient physical mechanisms from this sampling mismatch.

Pressure differences and calibrated currents use fitting-only standardization.
No regime-specific centering is applied. M0 uses eligible fitting marginals:
there is no unmanipulated observational sample, so these are acquisition-policy
marginals. M1 fits ridge Gaussian mechanisms on a fit-only Gaussian-BIC DAG;
the small ridge grid is selected on the independent development acquisition.
M2 uses the pinned DCDI-DSF density and existing optimizer adaptation, with known
assigned commands, then common flows. It is not a native converged DCDI claim.
Raw acyclicity, legacy stopping, projection and discovery/refit costs are reported.

M3–M5 share an immutable, calibration-blind bank of at most 24 graphs. M3 selects
the mean calibration objective; M4 uses rho=0.5; M5 uses at most three complete
SCMs, energy-score weights and tau=0.01. Each receives the full standalone bank
cost, plus selection and generation. The historical one-time audit returns G0
on rejection. Fixed flows and random repair remain controls. Matched completed
prefixes use 12k/24k/36k updates and 120/300/600 charged seconds, with achieved
costs and coverage reported. Equal final generation is 4,096 complete observations
per method/arm and 256 joint SW projections. Common random streams make identical
models exactly comparable. Parent-set caching remains canonical and data-specific.

Command nodes have no physical mechanism estimated under intervention. A masked
nuisance view fits their assignment-law placeholders using the same observed rows;
all physical-node losses are zero for that view. Every score/audit excludes command
densities, and all predictions replace commands exactly. No extra observations
are created. Ambient and command nodes have no incoming model edges. This is a
declared design/context assumption applied to all graph methods. Diagnostics
retain MMD/HSIC but use the first fixed search environment as a conditional
reference because no unmanipulated observational environment exists.

One bounded actual local Qwen3-8B proposal (at most one validation retry) receives
verified variable descriptions and root constraints only. It may know this public
benchmark from pretraining. Schema failures and fallback are retained. Semantic
and training-only starts receive matched downstream procedures; this experiment
tests a fallible prior, not independent discovery or novel physics.

Primary error is absolute error of the randomized high-minus-low contrast on
five engineering outcomes: both currents and three ambient-relative pressures,
divided by fitting SD. Average equally over outcomes and actuator targets, then
over repeated acquisition files for a target. Secondary endpoints are joint SW1,
marginal W1, effect direction, 90% marginal prediction coverage/width and worst
regime. Harm retains the historical SW threshold relative to the corresponding
fixed-G0 model; it is distinct from the primary contrast endpoint.

Empirical intervals use 2,000 paired hierarchical resamples of acquisitions within
target and consecutive ten-row experimental blocks within acquisition. There is
only one hatch acquisition. These intervals condition on one apparatus, the
fitted model and Monte Carlo streams. Five grouped fit-run bootstrap refits
separately describe selection frequency and refitting sensitivity; they are not
five physical replications. Four prespecified paired acquisition sign-flip tests
use Holm correction. Model predictive intervals, empirical confidence intervals,
refit spread and four-batch Monte Carlo SEs are kept distinct.

Offline decisions choose only between each recorded binary pair, minimizing
predicted total current subject to mean upwind-relative pressure at least the
development 75th percentile (6.1875 Pa). If neither predicted arm is feasible,
choose larger pressure, then smaller current, then the low arm. Report measured
constraint violations, feasible alternatives and current regret only when the
chosen arm and a measured comparator satisfy the constraint. This is a finite
recorded-alternative assessment, not verified optimal control or equipment use.

Figures show the full 11-node G0/M3 graph, M5 component graphs, and separate
experimental total effects. Fixed positions express process roles, not imposed
edge directions. Responses focus on both currents and up/downwind pressures.
Any mismatch panel uses the largest absolute M3 primary contrast error with
lexical ties. Edge frequency comes from five grouped training-run refits and is
not a causal posterior. The device cap is 12 additional hours including pilots,
tests, failures, LLM and refits. No automatic budget extension is permitted.
