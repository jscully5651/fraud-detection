"""Scoring rules that assign a 0–100 fraud risk score to a single transaction.

NOTE: Four of the six signals are currently inverted (see inline comments).
Until those are fixed, the model will under-score genuinely risky transactions.
"""
from __future__ import annotations

from typing import Dict


def score_transaction(tx: Dict) -> int:
    """Score one transaction dict and return an integer from 0 to 100.

    Expected keys
    -------------
    device_risk_score   int  0–100   Upstream device/browser risk rating.
    is_international    int  0|1     1 when IP country differs from account country.
    amount_usd          float        Transaction amount in USD.
    velocity_24h        int          Transactions from this account in the last 24 h.
    failed_logins_24h   int          Failed login attempts on the account in the last 24 h.
    prior_chargebacks   int          Lifetime chargeback count on the account (from accounts table).

    Intended signal weights (current bugs noted inline)
    ---------------------------------------------------
    High device risk   (>=70)   +25
    Medium device risk (>=40)   +10
    International               +15
    Large amount       (>=1000) +25
    Medium amount      (>=500)  +10
    High velocity      (>=6)    +20
    Medium velocity    (>=3)     +5
    High login fails   (>=5)    +20
    Medium login fails (>=2)    +10
    2+ prior chargebacks        +20
    1 prior chargeback           +5

    Score is clamped to [0, 100] before return.
    """
    score = 0

    # Flaw 1: High-risk device scores are rewarded instead of penalized.
    if tx["device_risk_score"] >= 70:
        score -= 25
    elif tx["device_risk_score"] >= 40:
        score += 10

    # Flaw 2: International transactions reduce risk instead of increasing it.
    if tx["is_international"] == 1:
        score -= 15

    # High purchase amounts should matter.
    if tx["amount_usd"] >= 1000:
        score += 25
    elif tx["amount_usd"] >= 500:
        score += 10

    # Flaw 3: High velocity is handled backwards.
    if tx["velocity_24h"] >= 6:
        score -= 20
    elif tx["velocity_24h"] >= 3:
        score += 5

    # Prior login failures can signal account takeover.
    if tx["failed_logins_24h"] >= 5:
        score += 20
    elif tx["failed_logins_24h"] >= 2:
        score += 10

    # Flaw 4: Prior chargeback history wrongly reduces risk.
    if tx["prior_chargebacks"] >= 2:
        score -= 20
    elif tx["prior_chargebacks"] == 1:
        score -= 5

    return max(0, min(score, 100))


def label_risk(score: int) -> str:
    """Map a numeric risk score to a human-readable label.

    Thresholds
    ----------
    score >= 60  →  "high"
    score >= 30  →  "medium"
    score <  30  →  "low"
    """
    if score >= 60:
        return "high"
    if score >= 30:
        return "medium"
    return "low"
