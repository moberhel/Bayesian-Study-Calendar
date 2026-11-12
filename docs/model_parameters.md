# Model parameters

Every number lives in `src/study_planner/model.py` (network) or `decision.py` (utility). This page
explains what each one means and why it has the value it has. **All values are handcrafted, not fit
to data.**

## Variables

| Variable | States | Role |
|---|---|---|
| `Diff1`, `Diff2`, `Diff3` | Easy, Hard | Difficulty of three concepts. Evidence (from syllabus / self-rating). |
| `Mastery` | Low, Med, High | Latent overall mastery. Never observed directly. |
| `Quiz` | Poor, OK, Good | Noisy practice-quiz reading of `Mastery`. Evidence. |
| `DaysLeft` | Few (<=2), Some (3-6), Many (>=7) | Days until the exam. Evidence. |
| `Stress` | Low, High | Current stress (self-report / wearable). Evidence. |
| `Action` | Intense5h, Moderate3h, Light1h, Rest | **Decision node.** Set to each option in turn, never inferred. |
| `Grade` | Low (<60), Mid (60-85), High (>85) | Exam outcome. Queried. |
| `FutureStress` | Low, High | Cramming/burnout stress going into the exam. Queried. |

## Inference task

For each action `a`, with evidence `e = {Diff1..3, Quiz, DaysLeft, Stress}`:

    P(Grade | e, Action=a)          P(FutureStress | e, Action=a)

computed by exact variable elimination. Then `argmax_a U(a)`. Setting `Action` as evidence is
equivalent to `do(Action=a)` here because `Action` has no parents.

## Priors and sensors

| CPT | Values | Meaning |
|---|---|---|
| `P(Mastery \| #Hard)` | 0 hard: .10/.30/.60 ... 3 hard: .60/.30/.10 (Low/Med/High) | More hard concepts shifts probability mass toward low mastery. |
| `P(Quiz \| Mastery)` | diagonal .70 (e.g. High -> Good .70, OK .25, Poor .05) | The quiz is a ~70%-accurate sensor. |
| `DaysLeft`, `Stress` priors | uniform / .6 Low, .4 High | Irrelevant in practice: both are always observed. |

## Grade model: `P(Grade | Mastery, Action, DaysLeft)`

Effective preparedness `s = BASE[mastery] + GAIN[action] * URGENCY[days]`, mapped to grades by an
ordinal logistic: `P(>=Mid) = sigmoid((s - 0.7)/0.4)`, `P(High) = sigmoid((s - 1.9)/0.4)`.

| Constant | Values | Meaning |
|---|---|---|
| `BASE` | Low 0.0, Med 1.2, High 2.6 | Preparedness before today's action. High is set well above `T_HIGH` so an advanced student is near the ceiling and extra study has diminishing returns. |
| `GAIN` | Intense 1.0, Moderate 0.6, Light 0.25, Rest 0 | Preparedness added by today's session. |
| `URGENCY` | Many 0.8, Some 0.9, Few 1.0 | Marginal value of today's session. With time to spare a skipped session can be made up later. |
| `T_MID`, `T_HIGH`, `W` | 0.7, 1.9, 0.4 | Grade thresholds and softness. |

## FutureStress model: `P(FutureStress=High | Stress, Action, DaysLeft, Mastery)`

    z = S_B0 + S_CURRENT[stress]
        + S_FATIGUE[action] * (1 + BURNOUT_AMP * [stress == High])
        + CRAM[mastery][days] * (1 - RELIEF * GAIN[action])
    P(High) = sigmoid(z)

| Constant | Values | Meaning |
|---|---|---|
| `S_B0` | -1.0 | Baseline log-odds of high stress. |
| `S_CURRENT` | Low 0, High 1.5 | Stress persists. |
| `S_FATIGUE` | Intense +1.0, Moderate +0.1, Light -0.2, Rest -0.6 | Direct effect of the action: long sessions tire you, rest recovers. |
| `BURNOUT_AMP` | 1.5 | If already highly stressed, fatigue **and recovery** effects are 2.5x as strong. |
| `CRAM` | e.g. Low mastery: Few 2.4 / Some 1.6 / Many 1.1; High mastery: -0.2 / -0.4 / -0.6 | The last-minute-cramming term: unprepared **and** close to the deadline is the most stressful; being well prepared is calming. |
| `RELIEF` | 0.8 | Studying today shrinks the cramming term in proportion to its `GAIN`. This is what makes procrastinating costly. |

## Utility

    U(a) = E[exam score | a]  -  lambda * P(FutureStress = High | a)

`GRADE_VALUE = {Low: 50, Mid: 75, High: 95}`, `STRESS_COST` (lambda) `= 30`. Lambda is the
exchange rate: 30 points of exam score are traded against a 100% chance of high stress.

## Tuning history (why these numbers)

The first parameterisation produced a clearly bad plan, which is why the `CRAM` term and
`BURNOUT_AMP` exist:

1. **v1: stress depended on action and days additively.** Every study action raised stress, so the
   planner told even the struggling student to rest for six days and then cram on days 7-8 --
   exactly the behaviour the system is meant to prevent.
2. **v2: added the `CRAM x RELIEF` interaction.** Procrastinating now costs stress later, but the
   planner never rested, and an already-anxious student was told to do a 5-hour block on day 1.
3. **v3: added `BURNOUT_AMP` and raised `BASE[High]`.** Recovery matters more when stressed, and
   advanced students have diminishing returns from studying.
4. **lambda sweep.** At 25 the advanced student studied every day (L L M M M M M M); at 40 they never studied before
   the exam (R x 8) and the struggling student's plan flattened to M M I R M M I R. 30 gave a
   final review (R x 6, then M M) for the advanced student and a boom-and-recover pattern for the
   struggling one.

Because the constants were adjusted after looking at the resulting plans, the demo shows that the
model's logic is coherent and responsive, not that it predicts real outcomes.
