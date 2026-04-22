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

## Code review findings

### Critical bugs in `src/risk_rules.py`

The review identified **four scoring signals that are inverted** — they subtract points from a transaction's risk score when they should be adding points. The practical effect is that the most dangerous transactions receive the *lowest* scores and are routed *away* from review.

| # | Signal | Current (broken) behavior | Correct behavior | Business impact |
|---|--------|--------------------------|-----------------|-----------------|
| 1 | High device risk score (≥ 70) | `score -= 25` | `score += 25` | Compromised or spoofed devices appear *safer* than clean ones |
| 2 | International transaction | `score -= 15` | `score += 15` | Cross-border transactions (elevated fraud risk) receive a discount |
| 3 | High transaction velocity (≥ 6 in 24 h) | `score -= 20` | `score += 20` | Rapid-fire transactions — a classic account-takeover pattern — are rewarded |
| 4 | Prior chargeback history | `score -= 5` or `score -= 20` | `score += 5` or `score += 20` | Accounts with a fraud history appear *less* risky |

A transaction that triggers all four worst signals (compromised device + international + high velocity + chargeback history) currently loses up to **60 points**, pushing it firmly into the **low** risk band. This is the most likely direct cause of the fraud losses reported last quarter.

The remaining scoring rules (transaction amount tiers, login failure tiers) and the label thresholds are correct.

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

## Pending work

The following fixes have been identified but are **not yet implemented** — they are awaiting review and approval:

| Task | Description |
|------|-------------|
| Fix scoring bugs | Flip the four inverted signals in `src/risk_rules.py` from `-=` to `+=` |
| Expand test suite | Add tests for all scoring branches in `tests/test_risk_rules.py` to prevent regressions |
