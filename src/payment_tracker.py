from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict

class TransactionStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Transaction:
    transaction_id: str
    sender: str
    recipient: str
    amount: float
    status: TransactionStatus

class TransactionTracker:
    def __init__(self):
        self._transactions: List[Transaction] = []
        self._next_id = 1

    def add_transaction(self, sender: str, recipient: str, amount: float) -> Transaction:
        transaction_id = f"TXN-{self._next_id}"
        self._next_id += 1
        transaction = Transaction(
            transaction_id=transaction_id,
            sender=sender,
            recipient=recipient,
            amount=amount,
            status=TransactionStatus.PENDING
        )
        self._transactions.append(transaction)
        return transaction

    def update_status(self, transaction_id: str, new_status: TransactionStatus) -> Transaction:
        for transaction in self._transactions:
            if transaction.transaction_id == transaction_id:
                transaction.status = new_status
                return transaction
        raise ValueError(f"Transaction {transaction_id} not found")

    def get_all_transactions(self) -> List[Transaction]:
        return self._transactions.copy()
