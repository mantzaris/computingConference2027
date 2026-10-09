# Engineering interpretation

The recorded interventions establish useful **total actuator responses on this
apparatus**, while the fitted graph remains a predictive hypothesis. At hatch 0°
and the other fan at duty 0.01, increasing inlet duty to 1 raises upwind-relative
pressure by 26.51 Pa [25.97, 26.94] and inlet current by 0.1060 A
[0.1030, 0.1089]. Increasing outlet duty instead lowers downwind-relative pressure
by 26.15 Pa [25.91, 26.49] and raises outlet current by 0.1079 A
[0.1039, 0.1128]. These are different recorded operating contrasts, not an
efficiency comparison between interchangeable fans. Intervals are pointwise 95%
experimental-block intervals and omit sensor-calibration uncertainty.

Mechanical coupling is visible in the measurements. Raising inlet duty also
raises the low-command outlet fan's speed by 1,102.5 rpm [1,100.0, 1,105.1].
Raising outlet duty raises inlet speed by 886.7 rpm [879.3, 894.1]. These support
cross-fan total effects under the specified nuisance commands; they do not
identify a direct speed-to-speed edge or measure airflow. Sources:
[observed contrasts](../results/observed_effects.csv), with supplementary frozen
model speed predictions in `reports/speed_predictions.csv` under artifact storage.

The hatch is particularly informative. At inlet duty 1 and outlet duty 0.01,
opening 0→45° lowers upwind-relative pressure by 5.426 Pa [4.522, 6.376], lowers
downwind-relative pressure by 7.606 Pa [6.714, 8.584], and lowers outlet speed by
349.5 rpm [346.9, 352.4]. The inlet-current change is −0.00244 A
[−0.00521, +0.00048], which does not establish an electrical saving. Thus the
measured hatch response offers pressure adjustment with an unresolved small
current change under this one condition. Further randomized settings and
calibration are needed before recommending an operating rule.

The separate outlet acoustic experiment records +0.461 V [0.259, 0.657] in
microphone-circuit amplitude. This is not sound pressure level. The immediate
hatch acoustic contrast and ten-second hatch contrast even have opposite signs;
different acquisition protocols prevent attributing that difference solely to
settling time. A compatible microphone/speaker configuration is needed for a
generative acoustic comparison. See [acoustic table](../results/acoustic.csv).

## What the graph establishes

The prespecified main M3 graph has 14 initial edges and 15 returned edges,
with two additions and one removal. It retains fan-command pathways, but **leaves
the hatch disconnected despite its measured pressure effect**. Five returned
edges occur in fewer than three of five grouped fitting-file refits; both added
edges appear in zero refits. This is a substantive failure of the learned process
representation, not evidence that the hatch has no effect. Stable edges are not
automatically causal either: current, pressure and speed can share unmeasured
fluid, temperature, electronic and temporal influences. An instantaneous DAG
cannot establish the direction of these unresolved pathways.

The graph's separate experimental panel displays total effects. It does not
upgrade model arrows to experimentally verified direct edges. The complete graph,
edge status and conditional selection frequencies are in
[graphs](../results/graphs.json) and [edge table](../results/process_edges.csv).
M5 combines two complete SCMs, assigning 0.9151 to G0 and 0.0849 to its other
component. Those weights concern prediction, not causal truth. Component graphs
are supplied separately, at the same positions.

## Which models were useful

The capped/projected **DCDI-DSF adaptation + common flows (M2)** has the lowest
observed primary error: 0.2199 [0.1987, 0.2462], versus M3 0.3310, random repair
0.3320, M5 0.3506, fixed flows 0.3602, M4 0.3680, ridge 0.8131 and marginals
1.0911. This is a descriptive ranking on five acquisition files, not a formal
general-superiority result. DCDI did not strictly converge: its 40,000-step cap
and 13-edge projection are essential qualifications. None of the four frozen
method contrasts is significant after Holm correction.

Fixed flows reduce primary error by about 56% relative to ridge on the same G0,
at 29.44 versus 0.50 seconds of charged fitting. This is a useful within-case
benefit of the flexible generative mechanisms. M3 costs 296.84 seconds for only
an 8.1% observed improvement over fixed flows; random repair is essentially tied
at 276.74 seconds. M2 costs 699.31 seconds, including 670.99 seconds of discovery.
Thus fixed flows provide a useful moderate-cost compromise, while ridge remains
the cheapest nontrivial model and M2 offers the best observed aggregate accuracy.
Per-outcome tradeoffs remain: M2's upwind-contrast MAE is 4.97 Pa versus fixed
flows' 3.44 Pa, but its downwind MAE is 1.39 versus 5.30 Pa. A single aggregate
does not define a universally best engineering model. See
[comparison](../results/comparison.md) and [unit errors](../results/engineering_summary.csv).

At the 120-second completed-prefix ceiling, diagnostic/random errors are
0.3166/0.3310, with achieved charges 106.0/118.7 seconds. At the 12,000-update
ceiling they are 0.3310/0.3320, with 11,900/11,450 updates. Larger checkpoint
ceilings saturate the fixed 24-candidate banks; they are not additional training.
These are matched ceilings with reported achieved costs, not exactly equal
hardware work. Longer search did not monotonically improve final prediction.

All four repair procedures have zero harmful regimes out of five under the
unchanged joint-SW definition. This cannot establish reliable repair across
systems. Nominal 90% predictive coverage is only 65.7–73.0% for the main flow
methods, and M4 worsens primary contrast error despite passing the audit and harm
threshold. Five grouped M3 refits range from 0.2644 to 0.4835 in primary error.
Joint SW is additionally sensitive to ambient drift and should not replace the
engineering endpoint. The grouped files share an acquisition sequence; refitting
spread is conditional sensitivity, not independent-day uncertainty.

The actual semantic LLM prior adds **no observed primary benefit**: M3 error
rises from 0.3310 to 0.5020, and every matched semantic initialization is worse
on this endpoint. It improves some coverage values but does not resolve
miscalibration. The 69.15-second GPU generation cost is charged separately in
[semantic comparison](../results/semantic_comparison.csv). This one public-benchmark
experiment neither proves general LLM ineffectiveness nor independent discovery.

## Operating decisions and missing evidence

The frozen 6.1875 Pa threshold does not distinguish the methods' decisions.
Every main and semantic model chooses the low arm in all five recorded pairs,
with zero measured mean-pressure violations. Mean feasible-current regret is
0.000421 A for every method, driven by a 0.002107 A hatch-arm mean difference
whose current uncertainty includes zero. Consequently the offline exercise
does **not demonstrate a decision advantage or verified energy savings**.
No threshold was changed after seeing this uninformative result.

Only 1–7 of 1,786 fitting rows fall near each final joint command tuple using
the descriptive ±0.1 duty / ±5° neighborhood. This support check was calculated
after evaluation and did not change eligibility or selection. The benchmark
substantially tests extrapolation to sparsely recorded operating corners.

The most useful new physical measurements would be replicated randomized
fan-by-hatch grids across separate days, with standardized settling histories,
compatible acoustic electronics and speaker settings, and temperature/ambient
context. Several measured pressure targets should yield nontrivial competing
recorded alternatives. Longer settling diagnostics and time-series identification
would test the static approximation. Calibrated supply voltage, airflow and sound
pressure would be required before claims about power, aerodynamic efficiency or
dB SPL. These are proposed measurements, not experiments performed here.
