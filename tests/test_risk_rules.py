from risk_rules import label_risk, score_transaction

# Baseline transaction: all signals at neutral values, scores exactly 0.
BASE_TX = {
    "device_risk_score": 10,
    "is_international": 0,
    "amount_usd": 100,
    "velocity_24h": 1,
    "failed_logins_24h": 0,
    "prior_chargebacks": 0,
}


def _tx(**overrides):
    """Return a copy of BASE_TX with specific fields replaced."""
    return {**BASE_TX, **overrides}


# ---------------------------------------------------------------------------
# Baseline
# ---------------------------------------------------------------------------

def test_baseline_scores_zero():
    assert score_transaction(BASE_TX) == 0


# ---------------------------------------------------------------------------
# Label thresholds
# ---------------------------------------------------------------------------

def test_label_risk_thresholds():
    assert label_risk(10) == "low"
    assert label_risk(35) == "medium"
    assert label_risk(75) == "high"


def test_label_risk_boundaries():
    assert label_risk(29) == "low"
    assert label_risk(30) == "medium"
    assert label_risk(59) == "medium"
    assert label_risk(60) == "high"


# ---------------------------------------------------------------------------
# Amount
# ---------------------------------------------------------------------------

def test_large_amount_adds_risk():
    tx = {
        "device_risk_score": 10,
        "is_international": 0,
        "amount_usd": 1200,
        "velocity_24h": 1,
        "failed_logins_24h": 0,
        "prior_chargebacks": 0,
    }
    assert score_transaction(tx) >= 25


def test_large_amount():
    assert score_transaction(_tx(amount_usd=1000)) == 25
    assert score_transaction(_tx(amount_usd=2500)) == 25


def test_medium_amount():
    assert score_transaction(_tx(amount_usd=500)) == 10
    assert score_transaction(_tx(amount_usd=999)) == 10


def test_small_amount_no_points():
    assert score_transaction(_tx(amount_usd=499)) == 0


# ---------------------------------------------------------------------------
# Device risk
# ---------------------------------------------------------------------------

def test_high_device_risk():
    assert score_transaction(_tx(device_risk_score=70)) == 25
    assert score_transaction(_tx(device_risk_score=95)) == 25


def test_medium_device_risk():
    assert score_transaction(_tx(device_risk_score=40)) == 10
    assert score_transaction(_tx(device_risk_score=69)) == 10


def test_low_device_risk_no_points():
    assert score_transaction(_tx(device_risk_score=39)) == 0


# ---------------------------------------------------------------------------
# International
# ---------------------------------------------------------------------------

def test_international_adds_risk():
    assert score_transaction(_tx(is_international=1)) == 15


def test_domestic_no_points():
    assert score_transaction(_tx(is_international=0)) == 0


# ---------------------------------------------------------------------------
# Velocity
# ---------------------------------------------------------------------------

def test_high_velocity():
    assert score_transaction(_tx(velocity_24h=6)) == 20
    assert score_transaction(_tx(velocity_24h=12)) == 20


def test_medium_velocity():
    assert score_transaction(_tx(velocity_24h=3)) == 5
    assert score_transaction(_tx(velocity_24h=5)) == 5


def test_low_velocity_no_points():
    assert score_transaction(_tx(velocity_24h=2)) == 0


# ---------------------------------------------------------------------------
# Login failures
# ---------------------------------------------------------------------------

def test_high_login_failures():
    assert score_transaction(_tx(failed_logins_24h=5)) == 20
    assert score_transaction(_tx(failed_logins_24h=10)) == 20


def test_medium_login_failures():
    assert score_transaction(_tx(failed_logins_24h=2)) == 10
    assert score_transaction(_tx(failed_logins_24h=4)) == 10


def test_low_login_failures_no_points():
    assert score_transaction(_tx(failed_logins_24h=1)) == 0


# ---------------------------------------------------------------------------
# Prior chargebacks
# ---------------------------------------------------------------------------

def test_multiple_prior_chargebacks():
    assert score_transaction(_tx(prior_chargebacks=2)) == 20
    assert score_transaction(_tx(prior_chargebacks=5)) == 20


def test_single_prior_chargeback():
    assert score_transaction(_tx(prior_chargebacks=1)) == 5


def test_no_prior_chargebacks_no_points():
    assert score_transaction(_tx(prior_chargebacks=0)) == 0


# ---------------------------------------------------------------------------
# Score bounds
# ---------------------------------------------------------------------------

def test_score_clamped_at_100():
    # All signals at maximum: 25+15+25+20+20+20 = 125, clamped to 100.
    tx = _tx(
        device_risk_score=90,
        is_international=1,
        amount_usd=2000,
        velocity_24h=10,
        failed_logins_24h=8,
        prior_chargebacks=3,
    )
    assert score_transaction(tx) == 100


def test_score_not_negative():
    assert score_transaction(BASE_TX) >= 0
