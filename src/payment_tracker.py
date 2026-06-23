import json
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

@dataclass
class TransactionEvent:
    id: str
    timestamp: datetime
    amount: float
    source: str

class PaymentTracker:
    def __init__(self):
        self.transactions = {}
        self.last_update = datetime.now()

    def ingest_event(self, event: Dict) -> None:
        transaction_id = event['id']
        if transaction_id in self.transactions:
            return  # Duplicate event detected and discarded
        self.transactions[transaction_id] = TransactionEvent(
            id=transaction_id,
            timestamp=datetime.strptime(event['timestamp'], '%Y-%m-%d %H:%M:%S'),
            amount=event['amount'],
            source=event['source']
        )
        self.last_update = datetime.now()

    def get_transactions(self) -> List[TransactionEvent]:
        return list(self.transactions.values())

    def is_duplicate(self, event: Dict) -> bool:
        return event['id'] in self.transactions
