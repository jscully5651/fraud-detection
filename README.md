# NimbusPay Fraud Detection

NimbusPay is a digital payments company. This system scores payment transactions for fraud risk so the fraud operations team can prioritize reviews, block high-risk activity, and measure fraud loss exposure by risk tier.

## Quick start

```bash
pip install -r requirements.txt
python src/analyze_fraud.py
pytest
```

## What the system does

1. Loads three data files: account metadata, transaction records, and confirmed chargebacks.
2. Merges transactions with account data to build a feature frame.
3. Scores every transaction 0–100 using a rule-based model (`src/risk_rules.py`).
4. Labels each transaction **low** / **medium** / **high** risk.
5. Prints the top-10 riskiest transactions and a summary table showing transaction counts, dollar volumes, and chargeback rates by risk band.

## Data inputs

| File | Description |
|------|-------------|
| `data/accounts.csv` | Customer account metadata: country, KYC level, account age, prior chargebacks, VIP flag |
| `data/transactions.csv` | Transaction records: amount, merchant category, channel, device risk score, IP country, velocity, failed logins |
| `data/chargebacks.csv` | Confirmed fraud chargebacks: transaction ID, date, reason, loss amount |

## Scoring model

Each transaction accumulates points based on risk signals. The final score is clamped to [0, 100].

| Signal | Condition | Points |
|--------|-----------|--------|
| Device risk | score >= 70 | +25 |
| Device risk | score >= 40 | +10 |
| International transaction | is_international == 1 | +15 |
| Large amount | >= $1,000 | +25 |
| Medium amount | >= $500 | +10 |
| High velocity | >= 6 transactions in 24 h | +20 |
| Medium velocity | >= 3 transactions in 24 h | +5 |
| High login failures | >= 5 in 24 h | +20 |
| Medium login failures | >= 2 in 24 h | +10 |
| Prior chargebacks | >= 2 | +20 |
| Prior chargeback | == 1 | +5 |

**Risk labels:**

| Label | Score range |
|-------|-------------|
| low | 0 – 29 |
| medium | 30 – 59 |
| high | 60 – 100 |

## Known issues

Four scoring signals are currently inverted in `src/risk_rules.py` — they subtract points where they should add them. This causes the model to under-score genuinely risky transactions (compromised devices, international origin, high velocity, and prior chargeback history). See inline comments in that file for details. Fixes are pending review.

## Project structure

```
src/
  analyze_fraud.py   Main pipeline: load → score → summarize → print
  features.py        Feature engineering (merge + derived columns)
  risk_rules.py      Scoring logic and risk label thresholds
tests/
  test_risk_rules.py Unit tests for scoring and labeling functions
data/
  accounts.csv
  transactions.csv
  chargebacks.csv
```
