# External-author check (prepared, not run)

**Purpose.** Every other number in this repository comes from messages written by the person who wrote the rule
pack. This check runs the frozen systems **once** on Hinglish messages written by someone else: the hand-written part
of [`bolewara/hinglish-scam-text-dataset`](https://huggingface.co/datasets/bolewara/hinglish-scam-text-dataset)
(35 scam, 28 benign according to its card). It tests whether the rules transfer beyond their author's phrasing.

**What it is not.** The set is still synthetic, small and single-author. It is not real-world accuracy, not a
protocol test run (`EVALUATION_PROTOCOL.md` §4 requires real data) and not a comparison with the dataset author's own
model.

Code: `src/scamcheck/eval/external.py`. Tests: `tests/test_external.py`, run on an invented file of the same shape;
the real data is never downloaded by tests.

## Step 1 — licence verification (a person, not the code)

1. Read the dataset card and licence at the pinned revision
   `743799229923fc80fd7e9f2c764b5e9bd4ab3c9a`:
   https://huggingface.co/datasets/bolewara/hinglish-scam-text-dataset/tree/743799229923fc80fd7e9f2c764b5e9bd4ab3c9a
   - The card states `license: cc-by-4.0`. It says the Hinglish rows were **hand-written** by the author and the
     English rows come from the UCI SMS Spam Collection.
   - Decide whether CC BY 4.0 covers this use: local evaluation, publishing aggregate results with attribution, and
     **no** redistribution of the text.
2. If you agree, edit the `src-bolewara-hinglish` row of `data/source_register.csv` yourself:
   - `licence_verified_by`: your name;
   - `verified_on`: today's date;
   - `status`: `PERMITTED-EXTERNAL-EVAL: hand-written Hinglish part only; evaluation only; no text redistributed;
     not for test split or training`;
   - `notes`: anything you checked or doubt.

   `external-plan` and `external-run` refuse to proceed until both fields are set. This status does not touch
   `RECORDED_PERMISSIONS`, `APPROVED_CONSENT_VERSIONS` or any test-split eligibility.

## Step 2 — download (once, at the pinned revision)

The file (473 KB) also contains English rows derived from UCI SMS Spam, which may include real personal data. It goes
to `data/raw/`, which is gitignored, and no command ever writes message text out.

```bash
mkdir -p data/raw/external
curl -L -o data/raw/external/bolewara-hinglish-scam-text-dataset.json "https://huggingface.co/datasets/bolewara/hinglish-scam-text-dataset/resolve/743799229923fc80fd7e9f2c764b5e9bd4ab3c9a/data.json"
```

## Step 3 — plan (freezes everything, writes no text)

```bash
scamcheck external-plan                 # rule-only systems, or, with a model configured (SCAMCHECK_LLM_*):
scamcheck external-plan --with-llm      # also B3 and B4-with-model; pins the model id and its Ollama digest
```

With `--with-llm`, B3 and B4-with-model share one cached answer per message, so their paired comparison (the
protocol's primary B4 vs B3) measures the systems, not model noise. `external-run` then needs the same model id
and, when recorded, the same digest. Per-row model outcomes are stored as status, label and quote counts only.
Quotes themselves are message text and are never written.

It writes `reports/external/bolewara/plan.json` and appends a **PLANNED** row to `reports/test_runs.md`. The plan
records:

- the file's SHA-256, the selected row indices and a hash of them;
- a SHA-256 over the frozen code (engine, baselines, metrics, this module, normaliser) and over B2's training data,
  plus the git commit;
- the systems (B0, B1, B2, B4 in rule-only mode) and the primary metrics;
- how the result will be read, stated before it exists.

**Selection rule (fixed before the data was seen).** A row counts as Hinglish if it contains Devanagari, or at least
two distinct romanised Hindi words from `HINGLISH_MARKERS`. The card's counts (35/28) are the check: any other count
stops the plan.

**If the counts do not match:**

- Do not edit the marker list to make them match. That would be tuning a selection on data already seen.
- Record a deviation in `reports/test_runs.md` with the counts the rule found.
- Then either stop, or decide in writing how the rule will change *before* looking at any verdicts.
- Then plan again.

**What actually happened (Deviation 1, `reports/test_runs.md`).** At the pinned revision the marker rule found
14 scam / 18 benign rows. The rows are shuffled, and even a broad filter finds only 54 candidates, so the file does
not hold the 63 rows the card describes. Every candidate's language was then judged by reading it without its label:
38 are Hinglish. The confirmed list, with the not-Hinglish reasons and two judgement calls, is
`reports/external/bolewara/selection.json`. It was committed before planning and is passed with:

```bash
scamcheck external-plan --with-llm --selection reports/external/bolewara/selection.json
```

The plan records the file's hash, the card's counts and the deviation. Labels come from the dataset unchanged.

## Step 4 — commit the plan (the pre-registration record)

```bash
git add reports/external/bolewara/plan.json reports/test_runs.md
git commit -m "Pre-register external-author check"
```

`external-run` refuses if the plan is untracked or changed since its commit.

## Step 5 — run once

```bash
scamcheck external-run
```

It refuses if any of these hold:

- results already exist;
- the data file, the selected rows or any frozen file changed;
- the register no longer authorises the source.

It writes `results.json` and `results.md` in `reports/external/bolewara/` (row indices, verdicts and B4's signal ids;
no text) and appends a **RUN** row to `reports/test_runs.md`.

Run it soon after planning: any later edit to the engine blocks it, by design.

## Reading the result (stated in the plan before running)

- Report it as an external-author synthetic check only.
- Scam recall (n = 35) is interpretable under the protocol's n ≥ 30 rule. Legitimate rates (n = 28) are counts only.
- B4 runs rule-only, so it cannot say `NO_STRONG_SIGNALS`. Its legitimate items are either false alarms or `UNCLEAR`.
- If B4's recall here and its own-author recall (9/12) have non-overlapping Wilson intervals, the rules are likely
  fitted to their author's phrasing.
- Nothing is changed in response. Findings go into the next rule-pack version, which then needs a different
  evaluation set.
- Attribution in any publication: Anuj Bolewar, `bolewara/hinglish-scam-text-dataset`, CC BY 4.0.
