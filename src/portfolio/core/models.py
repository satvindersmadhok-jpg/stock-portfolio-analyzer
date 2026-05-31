from dataclasses import dataclass
from datetime import date


@dataclass
class Transaction:
    date: date
    ticker: str
    transaction_type: str   # "BUY" | "SELL"
    quantity: float
    price: float

    @property
    def value(self) -> float:
        return self.quantity * self.price
