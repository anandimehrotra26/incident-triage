"""Single source of truth for categories, routing and the cost model.

All cost numbers are ASSUMPTIONS (abstract "cost units", CU). They encode the
*relative* pain of different mistakes. A real client must replace them with
their own figures; every evaluation script re-reads this file, so changing a
number here and re-running reproduces the analysis under the new requirement.
"""
from dataclasses import dataclass, replace

# ---------------------------------------------------------------- categories
BASE_CATEGORIES = [
    "accident_injury",
    "hazmat_spill",
    "theft_security",
    "cargo_damage",
    "delay_late",
    "vehicle_breakdown",
    "customs_documentation",
    "misdelivery_lost",
    "unclear_other",
]
NEW_CATEGORY = "cold_chain_excursion"  # introduced in the "changed requirement" experiment

# category -> team queue. unclear_other always goes to a human.
ROUTE_TABLE = {
    "accident_injury": "safety_emergency",
    "hazmat_spill": "hazmat_response",
    "theft_security": "security_ops",
    "cargo_damage": "claims",
    "delay_late": "dispatch",
    "vehicle_breakdown": "fleet_maintenance",
    "customs_documentation": "customs_compliance",
    "misdelivery_lost": "customer_service",
    "unclear_other": "human_review",
    "cold_chain_excursion": "quality_assurance",
}

# Misrouting these to the wrong team is much worse (people / environment / assets at risk).
SAFETY_CRITICAL = {"accident_injury", "hazmat_spill", "theft_security"}

HUMAN_REVIEW = "unclear_other"  # predicted label that means "a human must look"


# ---------------------------------------------------------------- cost model
@dataclass(frozen=True)
class CostModel:
    miss_urgent: float = 100.0          # truly urgent report routed as standard priority
    false_urgent: float = 5.0           # non-urgent report escalated (wastes on-call attention)
    wrong_team: float = 8.0             # wrong team gets a normal report (rework + delay)
    wrong_team_critical: float = 25.0   # true category is safety critical and goes to the wrong team
    human_review: float = 4.0           # one human looks at a report (abstention or unclear_other)
    abstain_urgent_delay: float = 10.0  # urgent report sits in the review queue NOT flagged urgent

    def with_(self, **kw):
        return replace(self, **kw)


BASE_COSTS = CostModel()
# "Stricter penalty for missing urgent cases" scenario used in change_request.py
STRICT_COSTS = BASE_COSTS.with_(miss_urgent=300.0)

# ---------------------------------------------------------------- run settings
SEED = 42
TEST_SIZE = 0.20
VAL_SIZE = 0.20

# Assumptions used ONLY to translate measured CPU time into money in the business summary.
ASSUMED_CPU_USD_PER_HOUR = 0.05   # ballpark for a small cloud vCPU; replace with your own number
ASSUMED_HUMAN_REVIEW_MINUTES = 2.0
ASSUMED_HUMAN_USD_PER_HOUR = 30.0  # replace with the client's loaded labour rate
