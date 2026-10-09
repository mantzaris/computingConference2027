# Draft application section — human scientific review pending

We studied recorded interventions on the Causal Chambers physical wind tunnel
(Gamella, Peters and Bühlmann, 2025). The application concerns how inlet/outlet
fan duty and hatch position change measured pressures, fan speeds and electrical
currents. We audited both official wind-tunnel archives, verifying actual
acquisition files, assignment protocols, sensor settings and calibration. The
main process representation contains eleven commanded or measured quantities;
three pressures are expressed relative to simultaneous ambient pressure. Current
uses the published ADC calibration. We do not interpret pressure as airflow,
ADC reference settings as motor supply voltage, or microphone amplitude as dB SPL.

We fitted quasi-steady predictive SCMs to slowly varying command windows from
eight acquisition files. Early stopping, graph search, calibration and audit use
separate files. The main procedure uses 3,399 recorded non-test observations,
including preprocessing; development examined an additional 14,000 rows.
Commands are replaced under intervention, and targeted root densities do not
enter the scientific likelihood. Residual pressure dependence and common ambient
measurement error limit the independent-disturbance interpretation. The static
model is a response surrogate rather than an identified instantaneous mechanism.
All configurations and selections were frozen before opening final measurements.

The primary test comprises 699 observations in five randomized acquisition files,
covering three actuator targets after ten-second waits. Other commands are held
at their protocol-specified values. Our endpoint is absolute error in the
high-minus-low pressure/current contrasts, divided by fitting-derived scales,
with equal outcome and actuator weights. Confidence intervals resample acquisition
files within actuator and consecutive experimental blocks; they condition on one
apparatus and fixed fitted models. Five grouped training-file refits describe
additional selection sensitivity. Three shorter-wait acquisitions are secondary.

The capped/projected DCDI-DSF adaptation with common flows obtained the lowest
observed primary error, 0.2199 (95% interval 0.1987–0.2462). Errors were 0.3310
for disturbance-guided repair, 0.3506 for the anchored ensemble, 0.3680 for robust
selection, 0.8131 for ridge and 1.0911 for independent marginals. Fixed flows and
random repair scored 0.3602 and 0.3320. DCDI reached its 40,000-step cap without
strict convergence; the result is not a converged native DCDI claim. Its charged
fit/discovery cost was 699 seconds, compared with 297 for disturbance-guided
repair, 29 for fixed flows and 0.50 for ridge. The prespecified Holm-adjusted
comparisons do not establish broad method superiority. The flexible mechanisms
were useful within this case, while fixed flows offered a favorable moderate-cost
compromise. None of the repair procedures crossed the historical harmful-repair
threshold, but nominal 90% coverage remained substantially below target.

The measured interventions expose both useful engineering responses and model
failures. With the hatch closed and outlet duty 0.01, increasing inlet duty from
0.01 to 1 increased relative upwind pressure by 26.51 Pa (25.97–26.94) and inlet
current by 0.1060 A (0.1030–0.1089). Opening the hatch at inlet/outlet duties 1/0.01
reduced relative upwind pressure by 5.43 Pa (4.52–6.38), while the inlet-current
change was −0.00244 A (−0.00521 to +0.00048). Thus pressure adjustment is measured,
but an electrical saving is unresolved. The returned fifteen-edge M3 graph
contains no hatch pathway and fails to represent this total effect. Five selected
edges occurred in fewer than three of five grouped refits. We therefore distinguish
predictive graph edges, selection frequency and randomized total-effect evidence
in separate figure panels; no direct edge is declared experimentally established.

A frozen Qwen3-8B generated a semantic prior from verified definitions without
test measurements or reference adjacency. A serialization correction recovered
the actual proposals without changing edges. The first proposal worsened every
matched primary comparison; M3 error increased to 0.5020. Possible benchmark
knowledge during pretraining further limits discovery claims. A separate measured
acoustic panel found an outlet-command microphone-circuit increase of 0.461 V
(0.259–0.657), but incompatible training sensor settings precluded a valid
generative acoustic comparison.

An offline decision exercise chose between the two recorded arms using a
development-fixed pressure threshold. All methods selected the same arms, with
zero mean-pressure violations and identical mean current regret of 0.000421 A.
This provides no demonstrated control advantage. Sparse fitting support at the
final command corners, serial dependence, shared acquisition history, omitted
temperature and a single apparatus limit transportability. Replicated randomized
operating grids, common sensor configurations and longer dynamic characterization
would most improve confidence. Earlier light-tunnel and synthetic findings remain
separate; this application does not revise or pool their results.

Scientific figures are generated from recorded data and frozen predictions using
matplotlib. GenAI assisted code and drafting and supplied the explicitly evaluated
semantic prior. Human review of assumptions, claims and final text remains pending.
The review manuscript must follow the current double-blind and disclosure rules;
this draft and its repository links are not a submission-ready anonymous package.
