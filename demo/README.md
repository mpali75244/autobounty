# AutoBounty — Live Demo Script

This is the 4-minute demo path for judges. Everything below uses **real GitHub artifacts** (a real repo, a real issue, a real merged PR) so the AI validators read actual evidence, not canned text.

---

## 1. Prepare the demo repo (once, before the demo)

Create a public repo, e.g. `github.com/<you>/autobounty-demo-app`, with this file:

**`payments.py`**

```python
def apply_discount(price_cents: int, discount_pct: int) -> int:
    if discount_pct > 100:
        discount_pct = 100
    return price_cents - price_cents * discount_pct // 100
```

Wait — that one is already fixed. The **buggy version** to commit first is:

```python
def apply_discount(price_cents: int, discount_pct: int) -> int:
    return price_cents - price_cents * discount_pct // 100
```

A discount above 100% makes the function return a **negative price**, which the checkout then "charges" — a real money-loss bug.

## 2. Open the issue

Create issue #1 with this body (paste as-is):

> **Title:** Negative total possible via oversized discount code
>
> **Body:**
> `apply_discount(price_cents, discount_pct)` does not validate `discount_pct`.
> Entering `discount_pct = 150` produces a negative total, and the checkout
> charges a negative amount (pays the customer). This can be triggered by any
> user with a crafted coupon code. Expected behavior: clamp discount to 100
> or reject the transaction.

## 3. Open the hunter PR

On a branch, fix it and open PR #2:

```python
def apply_discount(price_cents: int, discount_pct: int) -> int:
    if discount_pct < 0:
        raise ValueError("discount_pct must be non-negative")
    return min(price_cents, price_cents - price_cents * discount_pct // 100)
```

**PR description:** "Clamps oversized discounts and rejects negative values. Fixes #1"

Note the two URLs — the contract fetches the issue text from the GitHub API and the merged diff from `{pr_url}.diff` itself. No oracle, no backend.

## 4. The flow in the dApp (`frontend/index.html`)

| Step | Who | Action | What to point out |
|---|---|---|---|
| 1 | Maintainer | `Create bounty`: title, issue URL, budget `10 GEN`, rules `critical 50 / high 30 / medium 15 / low 5` | Budget is **escrowed** in the contract in the same tx; rules are pre-committed and transparent |
| 2 | Hunter | `Submit PR` with the PR URL | Sender address becomes the hunter |
| 3 | Maintainer | `Confirm merge` | Manual attestation; the real gate is next |
| 4 | Anyone | `Resolve with AI` | The contract first **verifies on-chain that the PR is actually merged via the GitHub API** (validators re-check it independently), then fetches the issue + diff: each validator runs its own LLM and consensus (`gl.eq_principle.prompt_comparative`) accepts the result only when every validator reaches the **same severity tier**. The `reasoning` is stored on-chain. Merge the PR on GitHub before this step, otherwise `resolve` reverts with "pull request is not merged" |
| 5 | — | Inspect the bounty card | `resolved_severity`, payout = budget x tier %, the AI's one-paragraph justification — fully transparent |
| 6 | Hunter | `Appeal` with a reason | Contract **re-runs the whole AI consensus** with the appeal reason added to the evidence. One appeal, result is final. If severity rises, the difference is paid automatically; if it drops, the leftover is reclaimable via `Close` |

## 5. One-liner for judges

> "The maintainer never decides the payout. Pre-committed rules + independent AI validators + on-chain consensus decide it — and the hunter can appeal, once, to a fresh consensus round."

## Notes / fallbacks

- GitHub API rate limit is per-IP (60/h unauthenticated); validators each use their own IP. Fine for a demo.
- If `resolve` fails because a validator cannot reach GitHub, simply retry — Optimistic Democracy rotates the leader.
- Studio localnet has web access; if it is blocked in your environment, the same flow works on Studionet / Testnet Asimov.
