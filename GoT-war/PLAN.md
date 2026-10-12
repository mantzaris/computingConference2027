# GoT-war: Generative Structural Models for Evidence-Weighted Causal Paths

Implementation and research plan for Codex. Prepared 2026-10-12.

## 1. Goal and execution contract

Build a reproducible research prototype that uses a local generative language model to turn narrative documents into executable structural causal models. Explain a specified war outcome through weighted causal paths, their shared mechanisms, and their aggregate contribution. Generate publication-quality network figures with at least 10 substantive nodes per principal case study.

The general methodology must apply beyond Game of Thrones. The LLM must discover variable definitions, candidate dependencies, mechanisms, alternative interpretations, and explanatory language. Do not encode a predefined list of causes of war, character-specific rules, or desired conclusions.

The user supplies the following execution environment:

- Local project directory: GoT-war, relative to the Codex session's working directory.
- Remote compute: an already connected RunPod instance.
- GPU: one NVIDIA RTX 4090 with 24 GB VRAM.
- Hard ceiling: 24 elapsed hours for the execution campaign, including setup, downloads, failed attempts, inference, analysis, and final synchronization.
- Target completion: 22 hours, retaining two hours for recovery and delivery.

This document plans the work. It does not assert that the remote connection, data, or GPU have been inspected in this planning session.

When executing, reuse the existing RunPod connection and available model cache. Do not create another instance, change billing, use paid external inference, or restart unrelated services. Do not terminate the pod itself unless separately authorized. Stop only processes created by this project and record their process identities.

Deliver functioning code, measured results, uncertainty and failure analyses, clear figures, and an anonymous paper draft or evidence-backed manuscript scaffold. Acceptance is a goal, not a guarantee. Report incomplete work honestly.

## 2. Scientific scope and contribution

Working title: Generative Structural Equation Synthesis for Evidence-Weighted Causal Path Explanations.

Research questions:

1. Can an LLM generate source-grounded variables and executable structural mechanisms without topic-specific causal rules?
2. Do these mechanisms improve intervention reasoning and explanation fidelity over direct text answers and graph-only reasoning?
3. Can a fixed collection of overlapping causal paths explain the aggregate modeled outcome without duplicating shared mechanisms?
4. Which path contributions remain stable when plausible equations, source evidence, or reference scenarios change?
5. Which source segments substantiate influential paths, and which influential paths lack strong support?

Proposed contributions, to substantiate experimentally:

- A source-linked method for joint variable, graph, and structural-program generation.
- An evidence assessment layer separate from structural influence.
- A path-coalition attribution computed through explicit mechanism interventions.
- A visual explanation linking narrative segments, structural equations, shared paths, and aggregate outcome.

Do not claim these individual ingredients are new. The proposed contribution is their integration and evaluation. Existing narrative causal systems, language-model structural mechanisms, equation synthesis, and Shapley/path attribution must be discussed.

### Primary application

Use one continuity: HBO television Game of Thrones. Record the exact corpus version and source types. Do not silently combine television events with book continuity.

| Case | Intended focus | Graph target |
| --- | --- | --- |
| War of the Five Kings | Onset versus escalation and faction participation | 16-22 variables |
| Robert's Rebellion | Retrospective evidence and competing explanations | 12-18 variables |
| Daenerys's conquest of Westeros | Coalition changes and continuation of conflict | 14-20 variables |

These are provisional cases. At the corpus gate, select cases with sufficient traceable evidence. If Robert's Rebellion is too sparsely documented, replace it with another documented conflict and explain the change. Do not pad a graph to meet its node target. A war is not interchangeable with a single battle; record the level of analysis.

For every case, freeze an outcome definition with actor scope, onset/continuation/escalation meaning, and narrative time horizon. Outcomes must be comparable across alternative models of that case.

### Bounded initial scope

- Three documented application cases.
- A controlled benchmark of 60 independent generating SCMs, described below.
- One primary GPU model; an optional small second-model robustness subset only if time remains.
- Three accepted alternative SCMs per main application case when evidence permits.
- At most two repair attempts per generated artifact.
- Eight canonical explanation paths per application model by default; retain and report the omitted graph context.
- No model pretraining or fine-tuning in this 24-hour campaign.
- Interactive visualization is optional after static figures and core results are complete.

## 3. Data acquisition and evidence protocol

1. Inspect the local project and existing remote workspace before fetching anything. Read applicable AGENTS.md files and preserve existing work.
2. Search for accessible scripts, transcripts, official episode material, or authorized user-provided text. Prefer primary material. Label secondary summaries explicitly and keep their analyses distinguishable.
3. Store a source manifest containing URL or supplied filename, title, continuity, episode/chapter identifier, source type, access date, content hash, and availability/license notes.
4. Do not bypass access controls. Do not publish a copyrighted full-text corpus. Release source identifiers, derived annotations, small justified excerpts, and acquisition instructions as appropriate.
5. Segment at scene or passage boundaries. Assign stable IDs; preserve offsets and short evidence spans. Separate story-event time, statement time, and audience-revelation time.
6. Cluster duplicate or near-duplicate descriptions of the same evidence. Corroboration from a repeated summary is not independent evidence.
7. Build source-bounded retrieval using lexical retrieval and, if already available or inexpensive, local embeddings. Reuse the same retrieved evidence for matched baselines.
8. Record propositions as established event, character report, character belief, disputed account, or explicit modeling assumption. Do not treat a character report as automatically true.
9. Mark missing evidence as unknown. Do not complete missing scenes from model memory and label them as extracted evidence.

Corpus gate at hour 3: either freeze a usable version or document the access blocker and continue the general implementation and controlled experiments. Produce a clear gap report instead of silently replacing the GoT application with invented narratives.

## 4. Mathematical methodology

### 4.1 Generative model construction

Let the corpus be $\mathcal D=\{s_1,\ldots,s_n\}$ and the outcome question be $Q$. The LLM proposes models:

$$
M^{(k)}\sim q_\theta(M\mid\mathcal D,Q).
$$

Represent a probabilistic candidate as:

$$
M=(\mathcal V,\mathcal U,\mathcal F,P_{\mathcal U},\mathcal R),
\qquad
X_i=f_{\pi_i}(X_{\mathrm{Pa}(i)},U_i).
$$

Here $\pi_i$ is an LLM-generated executable expression, and $\mathcal R$ records evidence, variable definitions, assumptions, and provenance. The induced graph is determined by the functional dependencies. If no justified background distribution is available, retain compatible background states and compute ranges instead of pretending to estimate probabilities.

The LLM discovers:

- Variable names and operational definitions.
- State spaces: binary, categorical, ordinal, or bounded numeric where supported.
- Parent sets and temporal placement.
- Structural expressions and interactions.
- Alternative mechanisms for ambiguous links.
- Evidence records and concise mechanism descriptions.

Generic mathematical operators are fixed; application reasons are not. Allow compositions of arithmetic, comparisons, logical operations, conditional expressions, categorical lookups, and validated link functions. Numeric latent states such as trust must have a stated measurement rule or remain unresolved.

Do not force an additive or all-Boolean application model. Controlled benchmark families may intentionally use predefined mathematical mechanisms to provide known ground truth; those mechanisms must not be copied into application rules.

### 4.2 Restricted structural-program representation

Use a typed JSON abstract syntax tree rather than executing unrestricted generated Python. Include:

- Stable variable ID, label, type, allowed values/bounds, actor context, time interval.
- Parent IDs, local noise/background IDs, and structural expression.
- Source IDs and exact supporting offsets.
- Evidence status, explicit assumptions, and alternative-rule IDs.
- Human-readable equation and explanation generated from the same AST.

The evaluator must prohibit filesystem/network access, imports, arbitrary eval/exec, undeclared variables, and unbounded loops. Apply AST depth, size, evaluation-time, and memory limits. Only declared parent values and noise inputs enter a mechanism during execution. Source passages guide synthesis; the full narrative is not a hidden runtime input.

Check acyclicity, temporal consistency, state validity, active functional dependence, factual compatibility, and graph/equation agreement. A declared input that cannot affect the output over its valid domain is not automatically a causal edge. For large domains, disclose that dependency checks are sampled.

Use explicit common-cause nodes in initial models where supported. Independent local disturbances are a modeling assumption, not a fact inferred from prose. Represent unresolved confounding in limitations and alternatives rather than adding an unexplained bidirected edge to a DAG.

### 4.3 Evidence support and structural influence are separate

For edge $e$, retrieve supporting and contradicting evidence:

$$
\mathcal S_e=\operatorname{Retrieve}_\theta(\mathcal D,\operatorname{claim}_e).
$$

Generate an assessment:

$$
c_e=\operatorname{Assess}_\theta(\operatorname{claim}_e,\mathcal S_e),
\qquad c_e\in[0,1].
$$

Assessment criteria: explicit versus inferred mechanism, temporal compatibility, source status, contradictions, and independent corroboration. Save component assessments and source records.

Treat $c_e$ as an evidence-support score unless independent calibration establishes a probabilistic interpretation. LLM confidence, repeated generation agreement, and attention weights are not calibrated causal probabilities. A citation can support an event without supporting the functional form of its outgoing edge; assess these separately.

Fit an optional calibration map using only the controlled calibration split or genuine independently reviewed labels. Do not transfer synthetic calibration guarantees to GoT. Keep a uniform-score ablation.

Do not multiply $c_e$ into every structural equation by default. Epistemic confidence and physical/narrative influence have different meanings. Evidence affects candidate retention, sensitivity analysis, and display priority; the structural equation defines influence.

### 4.4 Propose, execute, diagnose, repair

$$
M^{(k+1)}
\sim q_\theta\!\left(
M\mid
\mathcal D_{\mathrm{build}},Q,M^{(k)},
\operatorname{Diagnostics}_{\mathrm{dev}}(M^{(k)})
\right).
$$

Use failures to revise variable definitions, parent sets, or equations. Suggested diagnostic ordering is:

1. Invalid structure or execution.
2. Contradiction with accepted source observations.
3. Unsupported or temporally impossible mechanism.
4. Failure on development queries.
5. Unnecessary complexity or constant-outcome memorization.

A candidate-ranking objective, used only after hard validity checks, is:

$$
\mathcal J(M)=
\mathcal L_{\mathrm{evidence}}(M)
+\lambda_1\mathcal L_{\mathrm{development}}(M)
+\lambda_2 C(M)
+\lambda_3 A(M).
$$

$C$ measures structural/program complexity; $A$ measures unsupported assumptions. Define all terms and weights in configuration, tune only on development data, and report sensitivity. Do not invent statistical fit values from textual judgments.

Factual fit alone is insufficient: all-root models, lookup tables for event IDs, and arbitrary residuals can memorize the story. Audit these failure modes and use independent intervention tasks.

Keep original and repaired candidates. If repair fails, report failure; do not substitute a researcher-written story rule and call it generated.

### 4.5 Factual compatibility, interventions, and counterfactuals

For accepted factual evidence $\mathcal E$, define:

$$
\mathcal U_M(\mathcal E)=
\{u:\operatorname{Solve}(M,u)\text{ agrees with }\mathcal E\}.
$$

An intervention $\iota=\operatorname{do}(X_j=x')$ replaces only the target equation:

$$
X_i^{\iota}=
\begin{cases}
x',&i=j,\\
f_{\pi_i}(X_{\mathrm{Pa}(i)}^{\iota},U_i),&i\ne j.
\end{cases}
$$

Freeze the other equations. For individual counterfactuals use the same compatible background state in factual and modified worlds. Do not independently resample the two worlds.

If a justified $P_{\mathcal U}$ is specified:

$$
P_M(Y_\iota=y\mid\mathcal E)=
\sum_u
\mathbf1[Y_{M_\iota}(u)=y]P_M(u\mid\mathcal E).
$$

Otherwise return the possible outcomes over compatible backgrounds and retained models. LLM decoder randomness is not automatically the story's exogenous noise.

Separate:

- Predictive risk before an outcome.
- Population/scenario intervention risk under a stated background distribution.
- Retrospective counterfactuals conditioned on factual evidence.

Conditioning on an already observed war makes its factual probability 1. Do not present that tautology as a successful likelihood prediction.

### 4.6 Aggregation through the structural equations

For a binary war outcome, a possible probabilistic structural representation is:

$$
W=\mathbf1[U_W\le h_{\pi_W}(X_{\mathrm{Pa}(W)})],
\qquad U_W\sim\operatorname{Uniform}(0,1).
$$

Here $h_{\pi_W}$ maps to $[0,1]$ and is generated by the LLM. Independence of $U_W$ from its parents is an explicit assumption of this specification. Deterministic equations remain valid alternatives.

Incoming influences combine at every intermediate node through its generated function, and then at the outcome. The method must support interactions, redundancy, necessary combinations, and inhibitory effects. Do not use a sum of edge scores, a product of edge confidences, or a noisy-OR as the universal war equation.

Model-implied probabilities depend on assumed mechanisms and distributions. Coefficients not identified by the available evidence require stated ranges or alternative models.

### 4.7 A fixed collection of explanatory paths

For each outcome, extract directed paths from a declared source-event boundary to the target:

$$
\mathcal P_W=\{p_1,\ldots,p_K\}.
$$

Use meaningful starting events; avoid counting every suffix of a path as a separate independent origin. Deduplicate identical paths. Include inhibitory routes. Fix the selection rule before final evaluation. Default $K=8$ for tractability; preserve the full model for computation.

Record all candidate paths, retained paths, selection rationale, graph coverage, and remaining background. Path enumeration and truncation are explanation policies, not scientific facts.

A conservative display heuristic is:

$$
c_p=\min_{e\in E(p)}c_e.
$$

Label it weakest-link evidence support, not a path probability. Check ranking sensitivity to an alternative summary such as the geometric mean, which is also only a heuristic.

### 4.8 Path-coalition attribution with shared edges

For a coalition $S\subseteq\mathcal P_W$:

$$
E(S)=\bigcup_{p\in S}E(p).
$$

Let $E_{\mathrm{focus}}=\bigcup_{p\in\mathcal P_W}E(p)$. Define an explicit mechanism comparison. An active edge transmits its current parent value. An inactive edge in $E_{\mathrm{focus}}\setminus E(S)$ supplies a fixed, documented reference value to the child equation. Edges outside $E_{\mathrm{focus}}$ remain active.

Choose semantically meaningful reference values from development evidence or declared counterfactual assumptions. A reference can be unknown or contested; retain alternatives. Do not always replace every value with numeric zero.

Compute:

$$
v_M(S)=\mathbb E_{U\sim P_{\mathcal U}}
[W_{M_{E(S)}}(U)].
$$

For retrospective attribution, replace the background measure with the stated factual posterior. When a probability measure cannot be justified, compute scenario-specific values and sensitivity ranges.

The path attribution is:

$$
\phi_p^M=
\mathbb E_{\sigma}
\left[
v_M(\operatorname{Pre}_{\sigma}(p)\cup\{p\})
-v_M(\operatorname{Pre}_{\sigma}(p))
\right].
$$

For the fixed path collection and baseline:

$$
v_M(\mathcal P_W)=v_M(\varnothing)+
\sum_{p\in\mathcal P_W}\phi_p^M.
$$

Implementation:

- Shared edges are enabled once through set union.
- Cache each coalition by its effective edge mask, since different path coalitions may create identical graphs.
- Use common background draws for paired differences.
- For $K\le6$, enumerate coalitions exactly when inexpensive.
- Otherwise use 64 sampled path permutations initially, with 128 background draws where applicable; increase only within budget.
- Report numerical/Monte Carlo error separately from structural-model uncertainty.
- Stop attribution refinement when its tolerance or budget is reached.

Interpretation limits:

- This is a specified mechanism-ablation, path-coalition game. It is not automatically a natural path-specific causal effect or an actionable intervention.
- Edge unions can enable recombined routes. Report this; do not claim isolated-path effects.
- The allocation changes with the path collection and reference inputs. Run a baseline/reference sensitivity check and a disjoint-mechanism grouping check.
- Shared-edge handling prevents duplicate execution. It does not make the allocation uniquely true.
- Attribution explains the chosen full-model versus reference contrast, not the fraction of objective historical responsibility.
- Do not sum contributions across every edge in a chain.

### 4.9 Evidence weights for narrative segments

Let $a_{\ell p}$ allocate the evidential support of path $p$ among deduplicated source segments:

$$
a_{\ell p}\ge0,
\qquad
\sum_\ell a_{\ell p}=1
$$

when supporting evidence exists. Store the allocation and rationale. Unsupported paths have no fabricated supporting segment.

Define a display/retrieval priority:

$$
R_\ell=\sum_{p\in\mathcal P_W}
a_{\ell p}c_p|\phi_p|.
$$

This prioritizes segments supporting influential, well-evidenced mechanisms. Keep sign information in the path record. Show influential but weakly supported paths in a separate uncertainty view.

$R_\ell$ is an evidence-relevance score, not the causal effect of deleting a passage. Evidence removal changes the analyst's knowledge; event intervention changes the modeled world.

### 4.10 Alternative models and grounded explanations

For each application case, generate up to three admissible mechanism alternatives. Use the same outcome and aligned variable meanings where averaging or comparing numbers. When schemas cannot be aligned, present qualitative model comparisons.

Report ranges:

$$
[\underline{\phi}_p,\overline{\phi}_p]
=
[\min_{M\in\mathfrak M}\phi_p^M,
\max_{M\in\mathfrak M}\phi_p^M]
$$

only for corresponding paths under aligned definitions and comparison policies. These are sensitivity envelopes over the tested models, not confidence intervals over all possible worlds.

Generate prose from a structured execution trace:

$$
\widehat E_Q\sim
p_\theta(E\mid Q,T_Q),
$$

where $T_Q$ contains source IDs, assumptions, equations, interventions, state changes, aggregate values, and disagreements. Check every numerical and causal claim against the trace. Display a verification failure instead of silently retaining an unsupported statement.

## 5. Experiments and evaluation

### 5.1 Controlled benchmark

Target 60 independent generating SCMs:

- 20 with 12 variables.
- 20 with 18 variables.
- 20 with 24 variables.
- Within each size, 10 sufficiently specified narratives and 10 deliberately incomplete narratives.
- Include chains, forks, colliders, shared ancestors, converging paths, conjunctions, redundancy, and negative effects.

Use generic or randomized entity labels unrelated to GoT. Generate gold mechanisms independently of the inference pipeline, then render narratives. The generation mechanism is retained as benchmark metadata and hidden from the model being evaluated.

Split by generating SCM, including all of its paraphrases:

- 12 development SCMs.
- 12 calibration SCMs.
- 36 held-out test SCMs.

Balance size and evidence condition across splits. Do not place two paraphrases of the same SCM in different splits.

Create one original narrative per SCM and a matched paraphrase/renaming/reordering variant for the held-out set. Generate 8 gold queries per SCM, mixing ancestry, intervention, counterfactual, joint-cause, and evidence-support questions.

Verify narrative-to-gold fidelity. Use a deterministic traceable renderer as the guaranteed-consistent fallback; LLM paraphrases need explicit fidelity checks. Mark automated verification as automated. Do not claim independent human validation if none occurred.

For sufficiently specified cases, measure exact or equivalent functional behavior on withheld interventions. For incomplete cases, measure abstention, compatible-set coverage, or explicit uncertainty. Do not penalize a justified alternative as wrong merely because one hidden generating model was sampled.

### 5.2 Application evaluation

For each war:

- Freeze its source packet and outcome.
- Generate the variables, graph, equations, and up to three alternatives.
- Produce approximately 12-20 factual, structural, and counterfactual questions.
- Generate at least 10 meaningful nodes, ideally 14-20, with source records.
- Prepare a source-audit table separating event support from mechanism support.
- Prepare an optional independent human-review form.

GoT counterfactuals have no observable gold outcomes. Evaluate evidence traceability, formal consistency, explanation fidelity, and sensitivity. Report human judgments only if actual people supply them. Without a reader study, describe visual interpretability as a design objective and case-study observation, not a demonstrated comprehension improvement.

### 5.3 Methods

| ID | Method | Purpose |
| --- | --- | --- |
| B0 | Direct LLM answer from the same retrieved evidence | Text-only comparison |
| B1 | LLM answer using an extracted graph and evidence | Graph-only comparison |
| B2 | One generated executable SCM | Effect of formal execution |
| P | Retained generated SCMs plus evidence weights and path-coalition attribution | Full proposal |
| A1 | Same retained models with uniform evidence display weights | Evidence prioritization ablation |
| A2 | Naive sum of standalone path effects | Diagnostic for overlapping-path overcounting |

B0/B1 must receive comparable evidence and reported token budgets. Reuse the initial candidate between B2 and P; keep extraction and scoring caches shared where scientifically appropriate. Do not charge cached work twice in compute tables.

A1 does not change the equations, so assess retrieval/display ranking, not causal accuracy. A2 is a diagnostic, not a valid probability estimator. Optionally ablate evidence-guided model selection on a small frozen development-designed subset.

Use one primary generation seed on the full set. Repeat the principal generation with three seeds total on a balanced 12-SCM test subset and the application cases if feasible. Do not treat seeds, questions, paths, or paraphrases as independent narratives.

### 5.4 Metrics

- Executable/admissible model rate, before and after repair.
- Event extraction and causal-edge precision/recall where gold is available.
- Functional equivalence or withheld intervention accuracy.
- Counterfactual accuracy using shared background contexts.
- Unsupported event and unsupported mechanism rates, reported separately.
- Uncertainty/abstention performance on incomplete narratives.
- Explanation-to-trace agreement and source-reference validity.
- Attribution efficiency residual: absolute difference between the full/reference contrast and summed contributions.
- Path-ranking and reference-scenario stability.
- Segment evidence retrieval ranking, using controlled support labels; descriptive audit on GoT.
- Latency, GPU-hours, peak VRAM, tokens, retries, and cost only when actual billing data are available.

For comparisons, use paired differences and bootstrap at the independent SCM level. Present small-sample limitations. If only three literary cases are available, treat their conclusions as descriptive.

## 6. RTX 4090 inference strategy

Use the remote GPU for substantive LLM inference: extraction, synthesis, evidence assessment, repair, and explanation generation. Use CPU/vectorized NumPy for graph checks and structural evaluation unless profiling identifies a worthwhile GPU batch.

### Model selection

1. Prefer an already cached suitable instruction model and compatible serving environment.
2. Default if a fresh choice is needed: Qwen/Qwen3-14B-AWQ, a published 4-bit checkpoint.
3. Fallback: Qwen/Qwen3-8B in BF16 or a verified supported quantized format.
4. Avoid 14B BF16 on a 24 GB GPU; weights alone exceed available headroom.
5. Do not run two large model servers simultaneously on this GPU.

These are compatibility-oriented defaults, not a claim that they are the newest or best models. Verify the chosen checkpoint and installed library support. Freeze checkpoint revision, quantization, tokenizer, prompt templates, decoding settings, and dependency versions in the run manifest.

Use the existing compatible vLLM service if available. Otherwise install an isolated, tested environment or use Transformers. Bound environment troubleshooting to 45 minutes before selecting a working fallback.

Start with:

- A total context window around 8,192 tokens, counting input and output together.
- A 2,048-token maximum output for normal stages and up to 4,096 for graph/AST synthesis.
- Input trimming/chunking that reserves the configured output allowance.
- GPU memory utilization around 0.85-0.90 when using vLLM, adjusted from measured free VRAM.
- Small request concurrency, initially 1-2, then increase only after a stable pilot.
- Structured JSON outputs where supported; validate schemas regardless.
- Bounded generation with thinking mode disabled for routine extraction. If enabled for repairs, count all generated reasoning tokens in the budget.

Run a 20-request representative pilot. Measure end-to-end latency, prefill, output throughput, validity, and peak memory. Do not infer feasibility from advertised tokens per second.

Cache by model revision, prompt hash, retrieved source hashes, decoding parameters, and seed. Stream results to JSONL or SQLite after each item. Cache failed responses as well as accepted artifacts.

Initial total output-token ceiling: 1,000,000 tokens across all generation roles, reduced if pilot throughput requires it. This is an upper bound, not a target. Include synthetic-text generation and retries.

Estimate:

$$
T_{\mathrm{projected}}=
T_{\mathrm{elapsed}}
+N_{\mathrm{pending}}\widehat t_{\mathrm{request}}
+T_{\mathrm{analysis\ reserve}}
+T_{\mathrm{delivery\ reserve}}.
$$

Use conservative observed request latencies stratified by stage, and preserve at least three hours for analysis/figures plus two for final recovery. At every stage, stop adding jobs when the conservative projection exceeds the absolute deadline.

Reduce scope in this order: optional second model, extra seeds, extra paraphrases, extra alternatives, attribution precision. Preserve the three source-grounded case studies and the paired core comparison where possible. If even the minimum cannot fit, finish the largest balanced, fully evaluated subset and state the reduction.

## 7. Hard deadline, checkpointing, and remote operations

At execution start create budget.json with:

- UTC start time and absolute UTC hard deadline, exactly 24 hours later.
- Soft completion time at hour 22.
- Local monotonic timer information where supported.
- Stage budgets, token budget, per-request timeout, retries, and project process IDs.

The deadline must survive restarts and reconnects. Resuming must not reset the clock.

Suggested time allocation:

| Elapsed interval | Work | Gate |
| --- | --- | --- |
| 0-1 h | Inspect workspaces, verify connection/GPU, isolate project, launch budget monitor | Working environment |
| 1-3 h | Acquire/freeze corpus, pilot inference, finalize benchmark split and budget | Corpus and feasibility gate |
| 3-6 h | Implement schemas, evaluator, diagnostics, caching, benchmark and tests | End-to-end smoke run |
| 6-16 h | Core controlled and application inference, bounded repairs | Checkpoint continuously |
| 16-19 h | Structural queries, attribution, statistics, sensitivity | Freeze results |
| 19-22 h | Figures, source audits, manuscript draft, reproducibility checks | Target completion |
| 22-24 h | Essential recovery, final synchronization, concise handoff | Hard stop |

Independent CPU work can overlap GPU inference, but this is one elapsed-time budget, not additive per-stage allowances. Complete early if sufficient evidence is available.

Implement:

- A persistent job queue with per-job budgets and project-scoped process groups.
- A remote deadline watchdog that survives loss of the SSH connection.
- No new heavy jobs after hour 20; ensure active work leaves time for completion.
- Graceful cancellation and checkpoint at the soft deadline when unfinished.
- A hard deadline that stops only project-owned jobs.
- An emergency checkpoint that can complete within the remaining budget.
- Synchronization to local GoT-war after each phase and at least every 30 minutes during long runs.
- Heartbeat/progress artifacts every 5-10 minutes; do not leave a single opaque shell command blocking for hours.

Use the existing authenticated route. Verify nvidia-smi and free VRAM without displaying secrets. Keep credentials and private endpoint details out of reports, git, and manuscript files. Do not modify global CUDA or drivers. Use a project-specific remote directory; do not assume its absolute path.

If disconnected, retain the remote watchdog and resume using the same deadline. If a capability is unavailable, record the limitation; do not claim a protected 24-hour run without a functioning deadline mechanism.

## 8. Repository layout and code quality

All local work belongs under GoT-war. Suggested layout:

~~~text
GoT-war/
  PLAN.md
  CODEX_PROMPT.md
  README.md
  pyproject.toml
  configs/
    experiment.yaml
    models.yaml
    budget.json
  src/got_war/
    sources.py
    segmentation.py
    retrieval.py
    schemas.py
    generation.py
    structural_programs.py
    validation.py
    interventions.py
    evidence.py
    paths.py
    attribution.py
    evaluation.py
    visualization.py
    budget.py
    cli.py
  prompts/
  tests/
  data/manifests/
  data/raw/
  data/derived/
  benchmark/
  runs/<run_id>/
  results/
  figures/
  paper/
  docs/
~~~

Use clear variable names, typed data models, small modules, deterministic seeds, explicit configuration, and one documented entry point. Keep raw source material, large model weights, credentials, and bulky caches out of git. Use the existing model cache where appropriate.

Implement a CLI supporting environment checks, corpus building, model generation, evaluation, attribution, figure rendering, and resume. Expose a top-level run command that honors the persisted budget.

Do not add unnecessary frameworks, orchestration services, a database server, or a full website. SQLite/JSONL, NetworkX, NumPy, Graphviz, and the existing inference stack are sufficient.

## 9. Meaningful validation

Prioritize tests for scientific and execution correctness:

1. Known SCM interventions and factual-background reuse.
2. Logical conjunction and redundant-cause examples.
3. A shared-edge diamond where naive path addition overcounts.
4. Negative contributions and mixed-sign paths.
5. Graph/AST consistency, typing, temporal constraints, and rejection of undeclared inputs.
6. An intervention at the factual value reproduces the factual state.
7. An intervention cannot affect a non-descendant in the specified acyclic model.
8. Attribution efficiency within declared numerical tolerance.
9. Coalition cache keys deduplicate identical edge unions.
10. Reference-value sensitivity and distinction between passage removal and event intervention.
11. Resume does not repeat completed jobs or reset deadlines.
12. Simulated timeout stops project-owned tasks and preserves completed artifacts.

Use fixed seeds and exact tiny models for core tests. Do not add tests that merely mirror implementation details or keep expanding tests after the actual risks are resolved.

## 10. Figures and explanatory outputs

Required:

- Three principal network figures, each with at least 10 evidence-supported substantive nodes.
- One paired factual/counterfactual figure with identical node positions.
- One aggregate path-contribution chart including reference value, positive/negative contributions, and total.
- One sensitivity or benchmark performance figure with appropriate uncertainty.
- Two tables: method comparison and source/mechanism audit.

Use Graphviz dot or an equivalently capable layered layout and export SVG/PDF. Use standard plotting tools for numeric charts. Inspect the rendered figures at manuscript size. Do not use image generation for precise graphs or scientific plots.

Design:

- Chronological layered layout, readable labels, controlled edge crossings.
- Node type and faction context shown without requiring color alone.
- Edge labels describing generated mechanisms.
- Source/equation IDs linking graphics to audit tables.
- Edge evidence status separate from structural attribution.
- Path highlights and visible shared junctions.
- Confidence/support and causal effect never represented as the same number.
- Aggregation shown at the war outcome.
- At least approximately 9-point readable figure text at final page scale.

Do not assign every edge the sum of its path shares: shared edges would inherit duplicated values. Use a defined edge-attribution method if edge thickness encodes contribution, or use uniform edges plus separately displayed path contributions.

Optional only after core completion: a local Cytoscape.js explorer with node/edge details, source lookup, path selection, and equation inspection. It should use the same frozen result files as the paper; no deployment is required.

## 11. Reporting and manuscript preparation

Create:

- results/RESULTS.md with measured findings and limitations.
- results/metrics.csv and machine-readable per-case/per-method records.
- results/source_audit.csv and an optional unfilled human-review form.
- results/failures.jsonl with invalid generation, repair, and execution outcomes.
- runs/<run_id>/manifest.json with all hashes, versions, seeds, settings, and timing.
- docs/HANDOFF.md with completed work, blockers, resume instructions, and deadline status.
- A concise anonymous LaTeX manuscript and compiled PDF if the official template and toolchain are available within budget.

Use actual outputs for all tables and prose. Do not invent results, human participants, annotations, statistical significance, or independent verification. Distinguish algorithm correctness on controlled SCMs from causal validity in a literary interpretation.

Use the official Computing Conference template. As checked on 2026-10-12, the call for papers lists:

- Round 1 deadline: October 15, 2026, AoE.
- Round 2 deadline: December 1, 2026, AoE.
- Virtual participation for authors unable to travel.
- Anonymous submission.
- Main-text limit of 18 pages, with references/appendices subject to the stated additional allowance.
- GenAI disclosure and human responsibility for scientific content.

Recheck the live instructions before final formatting. Do not submit automatically. The researcher must review and own the scientific interpretation and manuscript.

Write novelty claims proportionately. Negative or mixed results are valid. Explain when source evidence cannot identify a mechanism or probability.

## 12. Completion criteria

The execution is complete when:

- The pipeline runs from documented commands and resumes safely.
- The existing remote RTX 4090 has performed logged substantive inference.
- All core experiments completed or a balanced, explicitly reduced subset is documented.
- Every reported application claim has a source/assumption record.
- Structural models execute and meet the relevant validity tests.
- Shared-path aggregation and its comparison baseline are explicit.
- Three suitable network figures exist, or a specific source-access limitation explains the shortfall.
- Results, scripts, figures, and a handoff are present locally in GoT-war.
- No fabricated results or claims of causal identification appear.
- The run ends within its persisted 24-hour elapsed-time ceiling.

Final Codex response should give the principal measured findings, local artifact paths, runtime/GPU usage, failures, and remaining scientific review needs.

## 13. Primary references and implementation documentation

Read and verify before citing; use the actual paper metadata for BibTeX. These sources motivate components, not proof of novelty.

1. Computing Conference 2027 call for papers:
   https://saiconference.com/Computing/CallforPapers
2. Bynum and Cho, Language Models as Causal Effect Generators, EMNLP 2025:
   https://aclanthology.org/2025.emnlp-main.107/
3. Shojaee et al., LLM-SR: Scientific Equation Discovery via Programming with Large Language Models, ICLR 2025:
   https://proceedings.iclr.cc/paper_files/paper/2025/hash/28df8e730c054c5331855fd4d5403ba9-Abstract-Conference.html
4. Li et al., Beyond LLMs: A Linguistic Approach to Causal Graph Generation from Narrative Texts, WNU 2025:
   https://aclanthology.org/2025.wnu-1.10/
5. Koupaee et al., Causal Graph based Event Reasoning using Semantic Relation Experts, ACL 2025:
   https://aclanthology.org/2025.acl-long.1269/
6. Yamin et al., LLMs Struggle to Balance Reasoning and World Knowledge in Causal Narrative Understanding, ICLR 2026:
   https://proceedings.iclr.cc/paper_files/paper/2026/hash/98741856b327ec2f9503179398da662f-Abstract-Conference.html
7. Wilmot, Shadow-Loom: Causal Reasoning over Graphical World Models of Narratives, 2026 preprint:
   https://arxiv.org/abs/2605.02475
8. Wang et al., Shapley Flow: A Graph-based Approach to Interpreting Model Predictions, AISTATS 2021:
   https://proceedings.mlr.press/v130/wang21b.html
9. Jung et al., On Measuring Causal Contributions via do-interventions, ICML 2022:
   https://proceedings.mlr.press/v162/jung22a.html
10. Ter-Minassian et al., PWSHAP: A Path-Wise Explanation Model for Targeted Variables, ICML 2023:
    https://proceedings.mlr.press/v202/ter-minassian23a.html
11. Witter et al., Exactly Computing do-Shapley Values, ICML 2026:
    https://proceedings.mlr.press/v306/witter26a.html
12. Pearl, Structural Counterfactuals: A Brief Introduction, 2013:
    https://onlinelibrary.wiley.com/doi/full/10.1111/cogs.12065
13. Qwen3 model cards:
    https://huggingface.co/Qwen/Qwen3-14B-AWQ
    https://huggingface.co/Qwen/Qwen3-8B
14. vLLM quantization and structured outputs:
    https://docs.vllm.ai/en/latest/features/quantization/
    https://docs.vllm.ai/en/latest/features/structured_outputs/
15. Graphviz and Cytoscape.js:
    https://graphviz.org/docs/layouts/dot/
    https://graphviz.org/docs/outputs/
    https://js.cytoscape.org/

## 14. First execution actions

1. Read this plan and applicable repository instructions.
2. Resolve the local GoT-war directory without creating a nested duplicate.
3. Inspect the already connected remote environment and verify the RTX 4090.
4. Establish the absolute deadline, scoped remote working directory, and checkpoints.
5. Inventory sources and cached models; run the pilot.
6. Freeze the feasible experiment configuration and begin implementation.

Proceed autonomously with routine reversible work. Ask only about a genuinely blocking ambiguity or access requirement after completing what remains possible. Do not spend the campaign repeatedly replanning.
