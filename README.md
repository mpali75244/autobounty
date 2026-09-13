<p align="center"><img src="icon/autobounty-lockup-horizontal-light.svg" alt="AutoBounty" width="420"></p>

<p align="center"><a href="https://github.com/mpali75244/autobounty/actions/workflows/ci.yml"><img src="https://github.com/mpali75244/autobounty/actions/workflows/ci.yml/badge.svg" alt="CI"></a></p>

<p align="center"><b>Autonomous bug bounties on GenLayer</b> — severity tier assigned by AI validator consensus from the merged PR, bounty released from escrow with no human in the loop.</p>

<p align="center"><a href="#فارسی">فارسی</a> · <a href="#english">English</a></p>

---

## فارسی

### ایده در یک خط

یک Intelligent Contract که وقتی PR رفع باگ مرج می‌شود، خودش (با اجماع چند والیدیتور AI) شدت باگ را از روی ایشو و دیف واقعی کد تعیین می‌کند و پول جایزه را از اسکرو — بدون دخالت انسان — به هانتر می‌پردازد.

### چرا از اجماع چند-والیدیتوری واقعی استفاده کرده‌ایم (نه یک API call ساده)

هسته‌ی تکنولوژی GenLayer یعنی **Optimistic Democracy + Equivalence Principle**. در `resolve_bounty` و `appeal` از همان API رسمی استفاده شده:

```python
result = gl.eq_principle.prompt_comparative(
    lambda: _evaluate_severity(issue_url, pr_url, rules, previous, appeal_reason),
    principle="The 'severity' field must be exactly the same value in both answers "
              "(one of: critical, high, medium, low). "
              "The 'reasoning' field is free text and may differ in wording.",
)
```

- **Leader**: ایشو را از GitHub API و دیف را از `{pr_url}.diff` می‌خواند، با قوانین ازپیش‌تعریف‌شده به مدل خودش می‌دهد و `{"severity", "reasoning"}` برمی‌گرداند.
- **هر والیدیتور**: مستقل، دوباره GitHub را می‌خوانَد و مدلِ خودش را اجرا می‌کند؛ فقط وقتی رأی می‌دهد که **فیلد تصمیم (`severity`) عین هم باشد** — wording می‌تواند فرق کند.
- عدم توافق → رهبر rotate می‌شود؛ نتیجه‌ی نهایی فقط با اکثریت ثبت و پرداخت اجرا می‌شود.
- قوانین سطح‌بندی از قبل و شفاف روی زنجیره‌اند؛ مدل «قانون اجرا می‌کند»، نه قضاوت دلبخواهی.
- مسیر **appeal** (یک‌بار برای هانتر): بازسازی کامل اجماع با شواهد بیشتر، نتیجه‌ی نهایی.

### فلوی کامل

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

### ساختار پروژه

```
contracts/autobounty.py     قرارداد Intelligent Contract (تک‌فایل پایتون)
tests/test_autobounty.py    ۹ تست Direct Mode (بدون شبکه، میلی‌ثانیه‌ای)
frontend/index.html         dApp تک‌فایلی با GenLayerJS
demo/README.md              سناریوی دموی ۴ دقیقه‌ای با ریپو/ایشو/PR واقعی
icon/                       کیت برند (SVG + PNG)
```

### راه‌اندازی

```bash
pip install -r requirements.txt
python -m pytest tests/ -v          # ۹/۹ پاس — بدون داکر و بدون شبکه
```

استقرار: با `genlayer` CLI یا از طریق **GenLayer Studio** فایل `contracts/autobounty.py` را deploy کنید، آدرس قرارداد را در فرانت‌اند وارد کنید.

### متدهای قرارداد

| متد | کی؟ | توضیح |
|---|---|---|
| `create_bounty(title, issue_url, rules)` **payable** | Maintainer | قفل بودجه + قوانین شفاف (درصدها باید ۱۰۰ جمع شود) |
| `submit_pr(bounty_id, pr_url)` | Hunter | ثبت PR توسط ارسال‌کننده |
| `confirm_merge(bounty_id)` | Maintainer | تأیید دستی مرج (MVP) |
| `resolve_bounty(bounty_id)` | هر کسی | اجماع AI → پرداخت خودکار tier % |
| `appeal(bounty_id, reason)` | Hunter (یک‌بار) | اجماع مجدد با شواهد بیشتر → نهایی |
| `close_bounty` / `cancel_bounty` | Maintainer | بازگرداندن باقیمانده اسکرو |
| `get_bounty` / `get_all_bounties` | view | خواندنی برای فرانت‌اند |

---

## English

AutoBounty is an Intelligent Contract for GenLayer that automates bug-bounty adjudication: the maintainer escrows a budget with transparent severity rules up-front; when the fixing PR is merged, independent AI validators read the actual GitHub issue and the merged diff, reach consensus on the severity tier via the Equivalence Principle (`gl.eq_principle.prompt_comparative`), and the contract pays out the corresponding percentage to the hunter — with a one-shot, evidence-aware appeal path.

**Judge pitch:** not a single LLM API call — every transaction's validator set independently re-fetches the evidence and re-runs its own model; only an identical decision field (`severity`) reaches consensus. Pre-committed rules mean the AI applies the law, it doesn't invent it. One appeal is honored with a fresh consensus round. Fully transparent: the AI's reasoning is stored on-chain.

### Contract API

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

### Running tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

Direct Mode (in-memory, no Docker) covers the whole lifecycle with mocked GitHub web responses and mocked LLM/EqComparative verdicts — including a consensus test proving validators reject diverging severity and accept equal severity with different wording.

### Brand kit

`icon/` contains the logomark, horizontal/vertical lockups and monochrome variants (SVG + PNG exports in `icon/exports/`). Amber `#F5A623` on `#0A0A0A`.

### References

- Equivalence Principle: https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle
- Calling LLMs: https://docs.genlayer.com/developers/intelligent-contracts/features/calling-llms
- Optimistic Democracy: https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy
- GenLayerJS: https://docs.genlayer.com/developers/decentralized-applications/genlayer-js

### Direct-mode compatibility fixes

`tests/conftest.py` applies three portable fixes to `genlayer-test==0.29.2` at import time (no manual site-packages edits needed, works on Linux and Windows):

1. Pins the GenVM SDK to `v0.2.16` — newer `0.3.0-rc*` releases don't ship the universal tarball that the test suite downloads.
2. Routes `ExecPromptTemplate` (the `EqComparative` verdict call inside `gl.eq_principle.prompt_comparative`) to the LLM mock machinery in Direct Mode.
3. On Windows, defers the stdin temp-file unlink that otherwise raises `PermissionError` (POSIX allows unlinking open files, Windows doesn't).

> Docs mention `Response.status_code`; the actual SDK runtime (`genvm v0.2.16`, hash-pinned in the contract header) exposes `Response.status`.
