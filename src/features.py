"""Feature engineering: joins transaction and account data and adds derived columns."""
from __future__ import annotations

import pandas as pd


def build_model_frame(transactions: pd.DataFrame, accounts: pd.DataFrame) -> pd.DataFrame:
    """Merge transactions with account data and add derived feature columns.

    Args:
        transactions: Raw transaction records (one row per transaction).
        accounts:     Account metadata keyed on account_id.

    Returns:
        Merged DataFrame containing all transaction and account columns.
        Account-level fields such as prior_chargebacks are joined in here and
        are therefore available when score_transaction() receives row.to_dict().
    """
    df = transactions.merge(accounts, on="account_id", how="left")

    return df
