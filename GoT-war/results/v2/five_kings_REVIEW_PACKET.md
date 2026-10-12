# Independent review packet: War of the Five Kings: first-season armed conflict

Status: **pending; no human adjudication is claimed**.

Read the full contextual passages in the local private HTML packet or the source links. For each item assess separately (1) event/state establishment, (2) directional causal influence, and (3) constraints on the exact function. Check time, who knew what, contradiction, and whether a statement is fact, report or belief. A function may fit the observed row without being identified.

The items below are selected by lowest directional weight then stable edge ID for a compact skeptical review, not as independent relevance gold labels. Full audits include all edges.

Additional flags in `source_inspection.json`: I03, I04, I05, I06. These targeted assistant observations are not completed independent review.

## R01: X03>W

Tywin Lannister assigns half of his forces to Jaime Lannister to attack Riverrun, Catelyn Stark's homeland, as part of a strategy to assert Lannister dominance and pressure the Stark-led coalition. → Armed conflict between the Stark-led northern/Riverlands coalition and the Lannister-controlled crown is active by the end of season 1.

Proposed equation: `and(X06, X03, eq(X08, 'agrees to allow the army to cross... in return for Robb and Arya marrying'), X09)`. Direction: unsupported; function: partially_constrained.

Sources: [screen_s01e02_s15_0](https://screenscripts.com/game-of-thrones/s01e02_the_kingsroad/#S15L1), [screen_s01e06_s1_0](https://screenscripts.com/game-of-thrones/s01e06_a_golden_crown/#S1L1), [screen_s01e06_s9_0](https://screenscripts.com/game-of-thrones/s01e06_a_golden_crown/#S9L1).

Open questions: [].

## R02: X06>W

Robb Stark formally declares war and mobilizes Northern forces under his command. → Armed conflict between the Stark-led northern/Riverlands coalition and the Lannister-controlled crown is active by the end of season 1.

Proposed equation: `and(X06, X03, eq(X08, 'agrees to allow the army to cross... in return for Robb and Arya marrying'), X09)`. Direction: unsupported; function: partially_constrained.

Sources: [screen_s01e02_s15_0](https://screenscripts.com/game-of-thrones/s01e02_the_kingsroad/#S15L1), [screen_s01e06_s1_0](https://screenscripts.com/game-of-thrones/s01e06_a_golden_crown/#S1L1), [screen_s01e06_s9_0](https://screenscripts.com/game-of-thrones/s01e06_a_golden_crown/#S9L1).

Open questions: [].

## R03: X06>X09

Robb Stark formally declares war and mobilizes Northern forces under his command. → Robb Stark takes Jaime Lannister prisoner during the events of season 1

Proposed equation: `if(eq(X06, 0), if(eq(X07, 0), if(eq(X08, 'agrees to allow the army to cross... in return for Robb and Arya marrying'), 1, 0), 0), 1)`. Direction: unsupported; function: unidentified.

Sources: [screen_s01e10_s5_0](https://screenscripts.com/game-of-thrones/s01e10_fire_and_blood/#S5L1).

Open questions: ["Is there explicit or contextual evidence that Robb's declaration of war (X06) directly enabled the capture of Jaime Lannister (X09)?"].

## R04: X07>X09

Robb sends a captured Lannister scout to falsely claim 20,000 men against Tywin → Robb Stark takes Jaime Lannister prisoner during the events of season 1

Proposed equation: `if(eq(X06, 0), if(eq(X07, 0), if(eq(X08, 'agrees to allow the army to cross... in return for Robb and Arya marrying'), 1, 0), 0), 1)`. Direction: unsupported; function: unidentified.

Sources: [screen_s01e08_s9_0](https://screenscripts.com/game-of-thrones/s01e08_the_pointy_end/#S9L1).

Open questions: ["Is there explicit or contextual evidence that Robb's deception of the Lannister scout (X07) directly enabled the capture of Jaime Lannister (X09)?"].

## R05: X08>W

Walder Frey allows Stark army passage in exchange for Robb Stark marrying one of his daughters and Arya Stark marrying one of his sons → Armed conflict between the Stark-led northern/Riverlands coalition and the Lannister-controlled crown is active by the end of season 1.

Proposed equation: `and(X06, X03, eq(X08, 'agrees to allow the army to cross... in return for Robb and Arya marrying'), X09)`. Direction: unsupported; function: partially_constrained.

Sources: [screen_s01e02_s15_0](https://screenscripts.com/game-of-thrones/s01e02_the_kingsroad/#S15L1), [screen_s01e06_s1_0](https://screenscripts.com/game-of-thrones/s01e06_a_golden_crown/#S1L1), [screen_s01e06_s9_0](https://screenscripts.com/game-of-thrones/s01e06_a_golden_crown/#S9L1).

Open questions: [].

## R06: X08>X09

Walder Frey allows Stark army passage in exchange for Robb Stark marrying one of his daughters and Arya Stark marrying one of his sons → Robb Stark takes Jaime Lannister prisoner during the events of season 1

Proposed equation: `if(eq(X06, 0), if(eq(X07, 0), if(eq(X08, 'agrees to allow the army to cross... in return for Robb and Arya marrying'), 1, 0), 0), 1)`. Direction: unsupported; function: unidentified.

Sources: [screen_s01e09_s4_0](https://screenscripts.com/game-of-thrones/s01e09_baelor/#S4L1).

Open questions: ["Is there explicit or contextual evidence that the Frey alliance conditional on marriage (X08) directly enabled the capture of Jaime Lannister (X09)?"].
