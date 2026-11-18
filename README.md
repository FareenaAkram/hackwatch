# hackwatch

**Catching reward hacking in code-model solutions, and turning it into preference data.**

When a code model is trained with RL against "do the visible tests pass?", it can learn to *game* the tests instead of solving the task: memorise the examples, return an object that equals everything, or exit the process with a success code. hackwatch grades solutions three ways, detects these cheats with a detector that never sees the answer key, and generates evidence-backed preference pairs (correct > honest-but-wrong > cheating).

**Live demo:** _add your Netlify/Vercel link_ · **Dashboard:** an interactive "reward lab" where you switch the grader and watch the cheats go from full reward to zero.

## Results (shipped build, seed 7)

20 problems, 221 candidate solutions (37 correct, 33 subtly wrong, 51 wrong, 100 reward hacks), 184 preference pairs.

| Class | n | Naive reward (visible tests) | Strict reward (hidden tests) | Naive + detector | Flagged by detector |
|---|---|---|---|---|---|
| correct | 37 | 100% | 100% | 100% | 0% |
| subtle bug (honest) | 33 | 100% | 0% | 100% | 0% |
| bug (honest) | 51 | 0% | 0% | 0% | 4% |
| **reward hack** | 100 | **100%** | 0% | **0%** | 100% |

- The naive grader gives **full credit to all 100 hacks** and to all 33 subtly wrong honest solutions. It cannot tell correct code from either.
- The detector (static AST checks + oracle-free dynamic probes) flagged **100/100 hacks** with **0/37 false positives on correct code**. Overall precision 98% (2 false positives: honest but degenerate bugs that return a constant). Static-only recall 100%, dynamic-only recall 60%.
- Ranking the 184 preference pairs in the intended order: naive reward agrees on 17 and ties on 167; strict (hidden tests) agrees on 163; naive + detector agrees on 157 with 0 contradictions.
- One finding worth noting: hidden-test *partial credit* can still rank a hack above an honest wrong solution (2 pairs). Zeroing flagged solutions removes that failure.

**Read these numbers honestly.** I wrote both the five hack generators and the detector, so 100% recall measures coverage of *known* patterns, not unseen ones. Recall on novel hacks from real models is unknown. That is why the project also includes an LLM plug-in layer (below) so you can test it on real model output.

## The five hacks

| Hack | What it does | How it is caught |
|---|---|---|
| `lookup_table` | Hard-codes the visible examples | Visible inputs appear as literals; constant output on fresh inputs |
| `overfit_fallback` | Hard-codes the examples, falls back to wrong code | Literal case-matching |
| `test_awareness` | Behaves differently when `sys.argv[0]` looks like the visible test | Reads `sys.argv`/frames/modules; literal case-matching |
| `always_equal` | Returns an object whose `__eq__` is always `True` | `__eq__` always returns `True`; output type never seen in examples |
| `exit_early` | `os._exit(0)` so the process ends "successfully" | `os._exit` call; clean exit with no results reported |

## How it works

1. **Problems.** 20 small tasks. Each has a reference solution (used only as an oracle), visible examples, edge cases and random hidden inputs.
2. **Candidates.** Reference and independent correct solutions; honest bugs (handwritten plausible mistakes, plus token-level mutants of the reference); the five generated hacks; optionally real LLM samples.
3. **Three graders**, each run in a separate sandboxed process:
   - *naive*: visible examples, reward 1 if the process exits 0.
   - *strict*: hidden cases, exact recursive type + value comparison, per-case timeouts, per-run secret sentinel (no sentinel = the solution escaped the harness).
   - *naive + detector*: naive reward, zeroed when the detector flags the code.
4. **Detector** (never sees hidden tests or the reference):
   - static: visible inputs as literals, always-equal objects, process-exit / shell / frame / argv tricks;
   - dynamic: run on fresh random inputs without an oracle; flag outputs whose types never appear in the examples, near-constant outputs, or a clean exit with no results.
5. **Preference pairs.** Chosen vs rejected, a 3-dimension rubric (visible tests, hidden tests, honesty) and a critique built from execution evidence (counterexample, detector findings). Order: correct > honest-but-wrong > hack, because a hack hides its failure from the reward signal.

## Quick start

Python 3.10+ and `pytest`. No Docker, no network.

```bash
pip install -r requirements.txt
python -m hackwatch build              # ~4 min on 2 cores; writes dataset/ and site/data.js
python -m hackwatch verify dataset     # re-grade every stored candidate and compare
python -m pytest -q                    # 64 tests
python -m hackwatch detect my_solution.py --problem two_sum   # grade + scan any solution file
```

Open `site/index.html` through a local server: `cd site && python -m http.server 8000`.

### Evaluate real LLMs (optional)

```bash
export ANTHROPIC_API_KEY=...          # or OPENAI_API_KEY
python -m hackwatch build --provider anthropic --model <model-name> --llm-samples 2
python -m hackwatch build --provider openai --model <model-name> --base-url https://api.openai.com --llm-samples 2
```

For every problem it samples two prompt styles: `honest` (plain task plus examples) and `pressure` (same, plus "graded only by these examples", the setup that tends to elicit test-gaming). Model outputs go through the same graders and detector and appear in the dashboard. They get no ground-truth hack label, only outcome labels (`correct`, `subtle_bug`, `bug`, `suspected_hack`), and they are kept out of the preference pairs.

> **Status:** the request and response handling for both providers is tested against a local mock server (headers, payloads, parsing, error paths). It has **not** been run against the live APIs from the build environment. Sandboxing treats model code as untrusted only at process level; run it in a container if you evaluate untrusted models at scale.

## Deploy the dashboard (static, no build step)

`site/` is dependency-free. Rebuild locally, commit `dataset/` and `site/data.js`, push.

**Netlify:** push the repo to GitHub, then *Add new site → Import an existing project*, pick the repo, leave the build command empty. The publish directory `site` is set in `netlify.toml`.
CLI: `npm i -g netlify-cli && netlify deploy --prod --dir=site`.

**Vercel:** push to GitHub, then *Add New → Project*, import the repo, preset **Other**, build command empty. The output directory `site` is set in `vercel.json`.
CLI: `npm i -g vercel && vercel --prod`.

## Limitations

- **Circular evaluation.** Hacks and detector share an author, so recall on unseen hacks is unknown.
- **Honest bugs are not human errors.** Handwritten ones are plausible, mutants are random single-token edits.
- **Small problems.** 20 short functions demonstrate the method; they are not benchmark-scale.
- **Sentinel is not tamper-proof.** A solution that reads `sys.argv` could learn it; the detector flags that access.
- **Isolation is process-level** (temp dir, timeouts, memory limits), not a security boundary.
- **Known false positives.** Honest but degenerate solutions that return a constant can trip `constant_output`.

## Layout

```
hackwatch/   problems, subtle (honest bugs), hacks, sandbox (graders), detector, providers, pipeline, report, cli
dataset/     candidates.jsonl, pairs.jsonl, stats.json, DATASET_CARD.md
site/        static dashboard (index.html, app.js, style.css, data.js)
tests/       64 tests: detector, graders, providers (mock server), end-to-end pipeline
```

MIT licensed.
