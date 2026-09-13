<p align="center"><img src="icon/autobounty-lockup-horizontal-light.svg" alt="AutoBounty" width="420"></p>

<p align="center"><a href="https://github.com/mpali75244/autobounty/actions/workflows/ci.yml"><img src="https://github.com/mpali75244/autobounty/actions/workflows/ci.yml/badge.svg" alt="CI"></a></p>

<p align="center"><b>Autonomous bug bounties on GenLayer</b> — severity tier assigned by AI validator consensus from the merged PR, bounty released from escrow with no human in the loop.</p>

---

## The idea in one line

An Intelligent Contract that, when a bug-fix Pull Request is merged, determines the bug's severity itself — by multi-validator AI consensus over the real issue text and the real code diff — and releases the corresponding bounty from escrow to the hunter. No manual triage, no disputable human judgment call.

## Why this is real multi-validator consensus (not a single LLM API call)

The core of GenLayer is **Optimistic Democracy + the Equivalence Principle**, and AutoBounty uses it through the official API inside `resolve_bounty` and `appeal`:

```python
result = gl.eq_principle.prompt_comparative(
    lambda: _evaluate_severity(issue_url, pr_url, rules, previous, appeal_reason),
    principle="The 'severity' field must be exactly the same value in both answers "
              "(one of: critical, high, medium, low). "
              "The 'reasoning' field is free text and may differ in wording.",
)
```

- **Leader**: fetches the issue from the GitHub API and the diff from `{pr_url}.diff`, feeds both — plus the pre-committed severity rules — to its own model, and returns `{"severity", "reasoning"}`.
- **Every validator**: independently re-fetches GitHub and re-runs its own model; it only votes to accept when the **decision field (`severity`) is identical** — the free-text reasoning may differ.
- Disagreement → the leader is rotated; the final result is only recorded (and the payout executed) by majority consensus.
- Severity rules are committed on-chain up-front and transparently — the model *applies the law*, it doesn't invent it.
- One-shot **appeal** path for the hunter: a full re-consensus with the appeal reason added to the evidence; the new result is final.

## Full flow

```
Maintainer                    Hunter                     GenLayer Consensus
    │                            │                              │
    │ create_bounty(...)         │                              │
    │ + escrow budget            │                              │
    │──────────────────────────► │                              │
    │                            │ submit_pr(pr_url)            │
    │ confirm_merge              │─────────────────────────────►│
    │─────────────────────────── │                              │
    │                            │      resolve_bounty ─────────┤─► fetch issue + diff (GitHub)
    │                            │                              │─► N independent AI validators
    │                            │        payout ───────────────┤─► severity consensus → pay tier %
    │                            │ ◄────────────────────────────│
    │                            │ appeal(reason)  [optional, once]
    │                            │      re-consensus → final    │
    │ close_bounty (leftover)    │                              │
```

## Project structure

```
contracts/AutoBounty.py     Intelligent Contract (single Python file)
tests/test_autobounty.py    9 Direct-Mode tests (no network, no Docker, millisecond-fast)
frontend/index.html         Single-file dApp built on GenLayerJS
demo/README.md              4-minute live demo script with a real repo / issue / PR
icon/                       Brand kit (SVG + PNG)
```

## Getting started

```bash
pip install -r requirements.txt
python -m pytest tests/ -v          # 9/9 passing — no Docker, no network
```

Deploy `contracts/AutoBounty.py` with the `genlayer` CLI or through **GenLayer Studio**, then paste the deployed contract address into the frontend. For a scripted deployment against a running localnet/GLSim: `python scripts/deploy.py`.

## Contract API

| Method | Caller | Behavior |
|---|---|---|
| `create_bounty(title, issue_url, rules)` payable | Maintainer | Escrows `msg.value`, validates rules sum to 100 |
| `submit_pr(bounty_id, pr_url)` | Hunter | Records PR URL from sender address |
| `confirm_merge(bounty_id)` | Maintainer | Manual merge attestation (MVP scope) |
| `resolve_bounty(bounty_id)` | Anyone | AI consensus → automatic tier-based payout |
| `appeal(bounty_id, reason)` | Hunter, once | Full re-consensus including appeal reason; final |
| `close_bounty` / `cancel_bounty` | Maintainer | Reclaim escrow leftovers |
| `get_bounty` / `get_all_bounties` | view | Frontend reads |

### Statuses

`open → pr_submitted → merged → resolved → (appealed →) resolved (final) → closed`

## Running tests

Direct Mode (in-memory, no Docker) covers the whole lifecycle with mocked GitHub web responses and mocked LLM/EqComparative verdicts — including a consensus test proving validators reject diverging severity and accept equal severity with different wording.

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

## Direct-mode compatibility fixes

`tests/conftest.py` applies three portable fixes to `genlayer-test==0.29.2` at import time (no manual site-packages edits needed, works on Linux and Windows):

1. Pins the GenVM SDK to `v0.2.16` — newer `0.3.0-rc*` releases don't ship the universal tarball that the test suite downloads.
2. Routes `ExecPromptTemplate` (the `EqComparative` verdict call inside `gl.eq_principle.prompt_comparative`) to the LLM mock machinery in Direct Mode.
3. On Windows, defers the stdin temp-file unlink that otherwise raises `PermissionError` (POSIX allows unlinking open files, Windows doesn't).

> Docs mention `Response.status_code`; the actual SDK runtime (`genvm v0.2.16`, hash-pinned in the contract header) exposes `Response.status`.

## Brand kit

`icon/` contains the logomark, horizontal/vertical lockups and monochrome variants (SVG + PNG exports in `icon/exports/`). Amber `#F5A623` on `#0A0A0A`.

## References

- [Equivalence Principle](https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle)
- [Calling LLMs](https://docs.genlayer.com/developers/intelligent-contracts/features/calling-llms)
- [Optimistic Democracy](https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy)
- [GenLayerJS](https://docs.genlayer.com/developers/decentralized-applications/genlayer-js)
