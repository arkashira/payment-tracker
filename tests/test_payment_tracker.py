import pytest
from payment_tracker import PaymentTracker, TransactionEvent

@pytest.fixture
def payment_tracker():
    return PaymentTracker()

def test_ingest_event(payment_tracker):
    event = {
        'id': '123',
        'timestamp': '2022-01-01 12:00:00',
        'amount': 10.99,
        'source': 'Stripe'
    }
    payment_tracker.ingest_event(event)
    assert len(payment_tracker.get_transactions()) == 1

def test_duplicate_event(payment_tracker):
    event = {
        'id': '123',
        'timestamp': '2022-01-01 12:00:00',
        'amount': 10.99,
        'source': 'Stripe'
    }
    payment_tracker.ingest_event(event)
    payment_tracker.ingest_event(event)
    assert len(payment_tracker.get_transactions()) == 1

def test_get_transactions(payment_tracker):
    event1 = {
        'id': '123',
        'timestamp': '2022-01-01 12:00:00',
        'amount': 10.99,
        'source': 'Stripe'
    }
    event2 = {
        'id': '456',
        'timestamp': '2022-01-01 12:01:00',
        'amount': 5.99,
        'source': 'PayPal'
    }
    payment_tracker.ingest_event(event1)
    payment_tracker.ingest_event(event2)
    transactions = payment_tracker.get_transactions()
    assert len(transactions) == 2
    assert transactions[0].id == '123'
    assert transactions[1].id == '456'

def test_is_duplicate(payment_tracker):
    event = {
        'id': '123',
        'timestamp': '2022-01-01 12:00:00',
        'amount': 10.99,
        'source': 'Stripe'
    }
    payment_tracker.ingest_event(event)
    assert payment_tracker.is_duplicate(event) is True
    new_event = {
        'id': '456',
        'timestamp': '2022-01-01 12:01:00',
        'amount': 5.99,
        'source': 'PayPal'
    }
    assert payment_tracker.is_duplicate(new_event) is False
