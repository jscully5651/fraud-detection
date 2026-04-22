# NimbusPay Fraud Detection — Code Review & Changes Log

## Overview

This document records the findings and changes made during a structured code review of the NimbusPay fraud detection system. It is intended as a reference for internal presentations and stakeholder briefings.

---

## What the system is supposed to do

The fraud detection system scores every payment transaction on a scale of 0–100 using a set of rule-based risk signals. Each transaction is then labelled **low**, **medium**, or **high** risk. The fraud operations team uses this output to:

- Prioritize which transactions to manually review
- Block or flag high-risk activity before losses occur
- Measure fraud exposure (dollar volume and chargeback rate) by risk tier

---

## How the scoring works

Think of the fraud score like a warning light on a dashboard — the higher the number, the more red flags the system has found on that transaction. Every transaction starts at zero and accumulates points as risk signals are detected. The final score is capped at 100, and the score determines which risk tier the transaction lands in.

### The six risk signals

**1. Device risk**
Before a transaction is processed, a third-party fraud provider analyses the device and browser used to initiate it — checking for known fraud devices, emulators, VPNs, and browser fingerprint anomalies — and returns a device risk score from 0 to 100. A high device risk score (70 or above) adds **25 points**; a medium score (40–69) adds **10 points**.

**2. Geography**
When the IP address of the transaction is in a different country from the account's registered country, the transaction is flagged as international and adds **15 points**. Cross-border transactions carry a statistically higher fraud rate and are a common pattern in card-not-present fraud.

**3. Transaction amount**
Larger purchases represent greater potential loss and are weighted accordingly. Transactions of **$1,000 or more** add **25 points**; transactions of **$500–$999** add **10 points**.

**4. Velocity**
The number of transactions made from the same account in the past 24 hours. Fraudsters and account-takeover attackers often make many rapid purchases to maximise damage before a card is cancelled. **6 or more** transactions in 24 hours adds **20 points**; **3 to 5** adds **5 points**.

**5. Login pressure**
Repeated failed login attempts on an account in the last 24 hours signal a possible account-takeover attempt via credential stuffing or brute force. **5 or more** failed logins adds **20 points**; **2 to 4** adds **10 points**.

**6. Prior chargeback history**
An account that has had fraudulent transactions confirmed in the past is more likely to be compromised again — either through a repeat attack or an ongoing undetected breach. **2 or more** prior chargebacks adds **20 points**; **1** prior chargeback adds **5 points**.

### Risk tiers

Once scored, every transaction is placed into one of three tiers:

| Tier | Score range | Intended action |
|------|-------------|-----------------|
| **Low** | 0 – 29 | No significant red flags. Normal processing. |
| **Medium** | 30 – 59 | Moderate concern. Candidate for step-up authentication or secondary review. |
| **High** | 60 – 100 | Multiple serious risk signals. Strong candidate for manual review, block, or challenge. |

The maximum possible score under normal circumstances is **125 points** (all six signals at maximum), which is clamped to 100. In practice a score above 70 indicates a transaction that has triggered several major signals simultaneously.

---

## Code review findings

### Critical bugs in `src/risk_rules.py` *(now fixed)*

The review identified **four scoring signals that were inverted** — they subtracted points from a transaction's risk score when they should have been adding points. The practical effect was that the most dangerous transactions received the *lowest* scores and were routed *away* from review.

| # | Signal | Broken behavior | Correct behavior | Business impact |
|---|--------|----------------|-----------------|-----------------|
| 1 | High device risk score (≥ 70) | `score -= 25` | `score += 25` | Compromised or spoofed devices appeared *safer* than clean ones |
| 2 | International transaction | `score -= 15` | `score += 15` | Cross-border transactions (elevated fraud risk) received a discount |
| 3 | High transaction velocity (≥ 6 in 24 h) | `score -= 20` | `score += 20` | Rapid-fire transactions — a classic account-takeover pattern — were rewarded |
| 4 | Prior chargeback history | `score -= 5` or `score -= 20` | `score += 5` or `score += 20` | Accounts with a fraud history appeared *less* risky |

A transaction triggering all four worst signals (compromised device + international + high velocity + chargeback history) was losing up to **60 points**, pushing it firmly into the **low** risk band. This is the most likely direct cause of the fraud losses reported last quarter. All four have been corrected.

The remaining scoring rules (transaction amount tiers, login failure tiers) and the label thresholds were correct and unchanged.

### Insufficient test coverage in `tests/test_risk_rules.py`

The test file contained only **2 tests** at the time of review. None of the four bugged signals had a test, which is why the bugs survived undetected. A complete test suite should cover every scoring branch including each of the four signals above.

### No `.gitignore`

The repository had no `.gitignore`, causing Python bytecode cache directories (`__pycache__`) to appear as untracked files.

---

## Changes made

### 1. Code documentation (committed: `7903111`)

**What changed:** Added docstrings and module-level descriptions to all three source files, and expanded the README from a 12-line placeholder to a full reference document.

**Files affected:**
- `src/risk_rules.py` — module docstring noting the four inverted signals; full docstring for `score_transaction()` listing every input key and intended weight; docstring for `label_risk()` with threshold table
- `src/features.py` — module docstring; docstring for `build_model_frame()` covering inputs, outputs, derived columns, and the account-join dependency
- `src/analyze_fraud.py` — module docstring; docstrings for all four functions
- `README.md` — expanded to cover business purpose, pipeline steps, data input descriptions, complete scoring model table, risk label thresholds, known issues, and project structure

**Why:** The codebase had almost no documentation. Without it, a new analyst or engineer had no way to understand the intended scoring logic, what data each function expects, or why the output looked wrong. The docstrings also make the four known bugs immediately visible to anyone reading the code.

### 2. `.gitignore` added (committed: `dca9bfe`)

**What changed:** Created a standard Python `.gitignore` covering `__pycache__`, compiled bytecode, virtual environments, build artifacts, test cache, and common IDE/OS files.

**Why:** Without it, running the code caused untracked files to appear in git status on every session, creating noise and risk of accidentally committing build artifacts.

---

### 3. Bug fixes — four inverted scoring signals (committed: pending push)

**What changed:** Corrected the four sign errors in `src/risk_rules.py`. Each of the four broken signals was changed from `-=` to `+=`. Inline `# Flaw` comments and the bug-warning module docstring were removed now that the code is correct.

**Files affected:**
- `src/risk_rules.py` — lines for device risk, international, velocity, and chargeback history

**Why:** These were the direct cause of the system scoring dangerous transactions as low-risk. With the fixes in place, a transaction carrying all four worst signals now accumulates up to **80 points** (from those four signals alone) rather than losing 60, correctly landing in the **high** risk band.

---

### 4. Expanded test suite (committed: pending push)

**What changed:** Rewrote `tests/test_risk_rules.py`, growing it from 2 tests to 23. A `BASE_TX` constant defines a neutral transaction that scores exactly zero, and a `_tx(**overrides)` helper allows each test to isolate a single signal cleanly.

**Coverage added:**

| Group | Tests |
|-------|-------|
| Baseline | Confirms all-neutral transaction scores 0 |
| Label thresholds | Mid-range and exact boundary values for low/medium/high |
| Amount | Large (≥$1,000), medium ($500–$999), and below-threshold |
| Device risk | High (≥70), medium (40–69), and below-threshold |
| International | Flag set and unset |
| Velocity | High (≥6), medium (3–5), and below-threshold |
| Login failures | High (≥5), medium (2–4), and below-threshold |
| Prior chargebacks | Multiple (≥2), single, and none |
| Score bounds | Clamped at 100 when signals sum above it; never negative |

**Why:** The original 2 tests covered only label thresholds and a loose check on large amounts. None of the four previously-bugged signals had a test, which is why those bugs went undetected. The new suite will catch any future sign reversal or weight change immediately.

---

## Pending work

None. All identified issues have been resolved.
