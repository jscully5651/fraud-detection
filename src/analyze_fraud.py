"""Main analysis pipeline: load data, score every transaction, and print a risk summary."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from features import build_model_frame
from risk_rules import label_risk, score_transaction


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load accounts, transactions, and chargebacks CSVs from the data directory.

    Returns:
        (accounts, transactions, chargebacks) as DataFrames.
    """
    accounts = pd.read_csv(DATA_DIR / "accounts.csv")
    transactions = pd.read_csv(DATA_DIR / "transactions.csv")
    chargebacks = pd.read_csv(DATA_DIR / "chargebacks.csv")
    return accounts, transactions, chargebacks


def score_transactions(transactions: pd.DataFrame, accounts: pd.DataFrame) -> pd.DataFrame:
    """Build the model feature frame and apply scoring to every transaction row.

    Returns:
        The merged feature frame with two additional columns:
            risk_score  (int 0–100)  Raw numeric score from score_transaction().
            risk_label  (str)        "low" / "medium" / "high" from label_risk().
    """
    model_frame = build_model_frame(transactions, accounts)
    model_frame["risk_score"] = model_frame.apply(
        lambda row: score_transaction(row.to_dict()), axis=1
    )
    model_frame["risk_label"] = model_frame["risk_score"].apply(label_risk)
    return model_frame


def summarize_results(scored: pd.DataFrame, chargebacks: pd.DataFrame) -> pd.DataFrame:
    """Aggregate scored transactions by risk label and join in confirmed chargeback counts.

    Returns:
        One row per risk label with columns:
            risk_label, transactions, total_amount_usd, avg_amount_usd,
            chargebacks, chargeback_rate.
    """
    summary = (
        scored.groupby("risk_label", as_index=False)
        .agg(
            transactions=("transaction_id", "count"),
            total_amount_usd=("amount_usd", "sum"),
            avg_amount_usd=("amount_usd", "mean"),
        )
        .sort_values("risk_label")
    )

    known_fraud = scored.merge(chargebacks[["transaction_id"]], on="transaction_id", how="left", indicator=True)
    known_fraud["is_chargeback"] = (known_fraud["_merge"] == "both").astype(int)

    fraud_by_label = (
        known_fraud.groupby("risk_label", as_index=False)
        .agg(
            chargebacks=("is_chargeback", "sum")
        )
    )

    summary = summary.merge(fraud_by_label, on="risk_label", how="left")
    summary["chargeback_rate"] = summary["chargebacks"] / summary["transactions"]
    return summary


def main() -> None:
    """Run the full pipeline and print the top-10 risk table and risk band summary."""
    accounts, transactions, chargebacks = load_inputs()
    scored = score_transactions(transactions, accounts)

    print("\nTop 10 scored transactions\n")
    print(
        scored[
            [
                "transaction_id",
                "account_id",
                "amount_usd",
                "device_risk_score",
                "is_international",
                "velocity_24h",
                "prior_chargebacks",
                "risk_score",
                "risk_label",
            ]
        ]
        .sort_values(["risk_score", "amount_usd"], ascending=[False, False])
        .head(10)
        .to_string(index=False)
    )

    print("\nRisk summary\n")
    print(summarize_results(scored, chargebacks).to_string(index=False))


if __name__ == "__main__":
    main()
