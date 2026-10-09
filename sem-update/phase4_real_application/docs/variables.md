# Variable dictionary and interpretation

Definitions and conversion constants follow the authors'
[Appendix II, Tables 1 and 3](https://arxiv.org/html/2404.11341v2#A2).
The numerical calibration is a published point estimate; its uncertainty is not
included in the empirical intervals.

| Columns | Modeled meaning / units | Reason |
| --- | --- | --- |
| load_in, load_out | Fan PWM duty fraction | Recorded commanded actuators |
| hatch | Opening command, degrees; 0 closed, 45 open | Recorded commanded actuator |
| rpm_in, rpm_out | Fan speed, revolutions/minute | Measured mechanical response |
| current_in, current_out | Current, A: raw × 1.16 / (1023 × 2) at nominal reference 1.1 | Electrical-load endpoints |
| pressure_upwind, pressure_downwind, pressure_intake | Each barometer minus simultaneous pressure_ambient, Pa | Pressure responses relative to ambient |
| pressure_ambient | External barometer, Pa | Environmental context; declared root assumption |

There are 11 modeled measured/commanded quantities. Pressure differencing is an
invertible change of coordinates when ambient is retained; it adds no node or
observation. Sensor offsets remain in the levels. Subtracting the same noisy
ambient measurement also creates shared measurement error, so independent
structural disturbances are an approximation, not a verified physical fact.

The excluded `mic` is a microphone-circuit amplitude: raw × 5/1023 volts in the
reserved acoustic experiments. It is not calibrated dB SPL. `v_in`, `v_out` and
`v_mic` are ADC reference settings, not motor supply voltages. No electrical power,
airflow, aerodynamic efficiency or acoustic safety limit is calculated.

`pot_1`, `pot_2`, `signal_1` and `signal_2` describe the speaker circuitry, which
is outside the main pressure/current question. Speaker variation, unmeasured
temperature, atmospheric drift, shared electronics and fluid pathways can still
violate causal sufficiency. The reduced graph must not be presented as a complete
physical mechanism. `osr_*`, `res_*`, `v_*`, config, counter, flag, intervention
and timestamp are acquisition/design metadata, not added physical outcomes.
