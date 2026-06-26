import pytest
from payment_tracker import TransactionTracker, TransactionStatus, Transaction

def test_add_transaction():
    tracker = TransactionTracker()
    tx = tracker.add_transaction("Alice", "Bob", 100.0)
    
    assert tx.transaction_id.startswith("TXN-")
    assert tx.sender == "Alice"
    assert tx.recipient == "Bob"
    assert tx.amount == 100.0
    assert tx.status == TransactionStatus.PENDING
    assert len(tracker.get_all_transactions()) == 1

def test_update_status():
    tracker = TransactionTracker()
    tx = tracker.add_transaction("Alice", "Bob", 100.0)
    
    updated_tx = tracker.update_status(tx.transaction_id, TransactionStatus.COMPLETED)
    assert updated_tx.status == TransactionStatus.COMPLETED
    
    assert tracker.get_all_transactions()[0].status == TransactionStatus.COMPLETED

def test_update_nonexistent_transaction():
    tracker = TransactionTracker()
    with pytest.raises(ValueError, match="Transaction TXN-123 not found"):
        tracker.update_status("TXN-123", TransactionStatus.FAILED)

def test_get_all_transactions():
    tracker = TransactionTracker()
    tracker.add_transaction("A", "B", 100.0)
    tracker.add_transaction("C", "D", 50.0)
    
    transactions = tracker.get_all_transactions()
    assert len(transactions) == 2
    assert transactions[0].amount == 100.0
    assert transactions[1].amount == 50.0
