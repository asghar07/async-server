from enum import Enum


class PaymentPlan(str, Enum):
    FREE = "free"
    STANDARD = "standard"

    @property
    def default_credits(self) -> int:
        credit_map = {
            PaymentPlan.FREE: 3,
            PaymentPlan.STANDARD: 50,
        }
        return credit_map[self]
