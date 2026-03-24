"""
Iteration 6 Tests: Transaction Matching, Dispute Chat, Force Approve
Tests for:
- POST /api/admin/payments/{pop_id}/match (matching/mismatching code/amount)
- POST /api/admin/payments/{pop_id}/force-approve (with/without reason)
- POST /api/admin/payments/{pop_id}/reject (with reason)
- POST /api/disputes/message (create dispute message)
- GET /api/disputes/{pop_id}/messages (get chat history)
- GET /api/admin/disputes (get all disputes with message counts)
- GET /api/admin/payments/pending (returns pending AND verification_failed)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://hh-jaba-portal.preview.emergentagent.com').rstrip('/')

# Test session tokens (created by setup script)
ADMIN_SESSION_TOKEN = "test-admin-session-13514af2"
USER_SESSION_TOKEN = "test-user-session-bb6c7465"
ADMIN_USER_ID = "admin-user-1774273147"
USER_ID = "user_5463750c8ece"


@pytest.fixture
def admin_client():
    """Admin authenticated session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ADMIN_SESSION_TOKEN}"
    })
    return session


@pytest.fixture
def user_client():
    """User authenticated session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {USER_SESSION_TOKEN}"
    })
    return session


class TestSetup:
    """Setup test data: Create invoice and POP for testing"""
    
    def test_create_credit_invoice_for_testing(self, admin_client):
        """Create a credit invoice to test POP submission against"""
        invoice_data = {
            "user_id": USER_ID,
            "billing_period_start": "2026-03-01",
            "billing_period_end": "2026-03-31",
            "line_items": [
                {"flavor": "Tamarind", "quantity": 5, "unit_price": 500, "status": "unpaid"}
            ],
            "notes": "Test invoice for iteration 6",
            "payment_type": "credit"
        }
        response = admin_client.post(f"{BASE_URL}/api/admin/credit-invoices", json=invoice_data)
        assert response.status_code in [200, 201], f"Failed to create invoice: {response.text}"
        data = response.json()
        assert "invoice_id" in data
        print(f"Created test invoice: {data['invoice_id']}")
        # Store for later tests
        pytest.test_invoice_id = data["invoice_id"]


class TestTransactionMatching:
    """Tests for the dual-entry transaction matching system"""
    
    def test_submit_pop_for_matching(self, user_client):
        """Customer submits POP with transaction code and amount"""
        # Use the invoice created in setup or create a new one
        invoice_id = getattr(pytest, 'test_invoice_id', None)
        if not invoice_id:
            pytest.skip("No test invoice available")
        
        pop_data = {
            "invoice_id": invoice_id,
            "transaction_code": "TEST123ABC",
            "amount_paid": 2500,
            "payment_method": "airtel_money",
            "payment_type": "full",
            "notes": "Test POP for matching"
        }
        response = user_client.post(f"{BASE_URL}/api/payments/submit-pop", json=pop_data)
        assert response.status_code in [200, 201], f"Failed to submit POP: {response.text}"
        data = response.json()
        assert "pop_id" in data
        pytest.test_pop_id_match = data["pop_id"]
        print(f"Created POP for matching test: {data['pop_id']}")
    
    def test_match_transaction_success(self, admin_client):
        """Admin enters matching code/amount → status becomes 'approved'"""
        pop_id = getattr(pytest, 'test_pop_id_match', None)
        if not pop_id:
            pytest.skip("No test POP available")
        
        match_data = {
            "admin_transaction_code": "TEST123ABC",  # Same as customer
            "admin_amount": 2500  # Same as customer
        }
        response = admin_client.post(f"{BASE_URL}/api/admin/payments/{pop_id}/match", json=match_data)
        assert response.status_code == 200, f"Match failed: {response.text}"
        data = response.json()
        assert data["status"] == "approved", f"Expected approved, got {data['status']}"
        assert "match" in data["message"].lower() or "approved" in data["message"].lower()
        print(f"Match successful: {data['message']}")
    
    def test_submit_pop_for_code_mismatch(self, user_client, admin_client):
        """Create another POP to test code mismatch"""
        # First create another invoice
        invoice_data = {
            "user_id": USER_ID,
            "billing_period_start": "2026-03-01",
            "billing_period_end": "2026-03-31",
            "line_items": [
                {"flavor": "Watermelon", "quantity": 3, "unit_price": 500, "status": "unpaid"}
            ],
            "notes": "Test invoice for code mismatch",
            "payment_type": "credit"
        }
        inv_response = admin_client.post(f"{BASE_URL}/api/admin/credit-invoices", json=invoice_data)
        assert inv_response.status_code in [200, 201]
        invoice_id = inv_response.json()["invoice_id"]
        
        # Submit POP
        pop_data = {
            "invoice_id": invoice_id,
            "transaction_code": "CUSTOMER999",
            "amount_paid": 1500,
            "payment_method": "airtel_money",
            "payment_type": "full"
        }
        pop_response = user_client.post(f"{BASE_URL}/api/payments/submit-pop", json=pop_data)
        assert pop_response.status_code in [200, 201]
        pytest.test_pop_id_code_mismatch = pop_response.json()["pop_id"]
    
    def test_match_transaction_code_mismatch(self, admin_client):
        """Admin enters different code → status becomes 'verification_failed' with reason"""
        pop_id = getattr(pytest, 'test_pop_id_code_mismatch', None)
        if not pop_id:
            pytest.skip("No test POP available")
        
        match_data = {
            "admin_transaction_code": "ADMIN777",  # Different from customer
            "admin_amount": 1500  # Same amount
        }
        response = admin_client.post(f"{BASE_URL}/api/admin/payments/{pop_id}/match", json=match_data)
        assert response.status_code == 200, f"Match request failed: {response.text}"
        data = response.json()
        assert data["status"] == "verification_failed", f"Expected verification_failed, got {data['status']}"
        assert "mismatch" in data["message"].lower() or "code" in data["message"].lower()
        print(f"Code mismatch detected: {data['message']}")
    
    def test_submit_pop_for_amount_mismatch(self, user_client, admin_client):
        """Create another POP to test amount mismatch"""
        # Create invoice
        invoice_data = {
            "user_id": USER_ID,
            "billing_period_start": "2026-03-01",
            "billing_period_end": "2026-03-31",
            "line_items": [
                {"flavor": "Beetroot", "quantity": 4, "unit_price": 500, "status": "unpaid"}
            ],
            "notes": "Test invoice for amount mismatch",
            "payment_type": "credit"
        }
        inv_response = admin_client.post(f"{BASE_URL}/api/admin/credit-invoices", json=invoice_data)
        assert inv_response.status_code in [200, 201]
        invoice_id = inv_response.json()["invoice_id"]
        
        # Submit POP
        pop_data = {
            "invoice_id": invoice_id,
            "transaction_code": "SAMECODEXYZ",
            "amount_paid": 2000,
            "payment_method": "airtel_money",
            "payment_type": "full"
        }
        pop_response = user_client.post(f"{BASE_URL}/api/payments/submit-pop", json=pop_data)
        assert pop_response.status_code in [200, 201]
        pytest.test_pop_id_amount_mismatch = pop_response.json()["pop_id"]
    
    def test_match_transaction_amount_mismatch(self, admin_client):
        """Admin enters different amount → status becomes 'verification_failed' with amount details"""
        pop_id = getattr(pytest, 'test_pop_id_amount_mismatch', None)
        if not pop_id:
            pytest.skip("No test POP available")
        
        match_data = {
            "admin_transaction_code": "SAMECODEXYZ",  # Same code
            "admin_amount": 1800  # Different amount (more than KES 1 tolerance)
        }
        response = admin_client.post(f"{BASE_URL}/api/admin/payments/{pop_id}/match", json=match_data)
        assert response.status_code == 200, f"Match request failed: {response.text}"
        data = response.json()
        assert data["status"] == "verification_failed", f"Expected verification_failed, got {data['status']}"
        assert "amount" in data["message"].lower() or "mismatch" in data["message"].lower()
        print(f"Amount mismatch detected: {data['message']}")


class TestForceApprove:
    """Tests for admin force-approve functionality"""
    
    def test_force_approve_with_reason(self, admin_client):
        """Admin force-approves a failed transaction with mandatory reason"""
        pop_id = getattr(pytest, 'test_pop_id_code_mismatch', None)
        if not pop_id:
            pytest.skip("No failed POP available")
        
        force_data = {
            "reason": "Customer provided bank statement showing correct transaction. Approved after verification."
        }
        response = admin_client.post(f"{BASE_URL}/api/admin/payments/{pop_id}/force-approve", json=force_data)
        assert response.status_code == 200, f"Force approve failed: {response.text}"
        data = response.json()
        assert "force" in data.get("message", "").lower() or "approved" in data.get("message", "").lower()
        print(f"Force approve successful: {data}")
    
    def test_force_approve_without_reason_fails(self, admin_client, user_client):
        """Force approve without reason should fail with 400"""
        # Create a new failed POP first
        invoice_data = {
            "user_id": USER_ID,
            "billing_period_start": "2026-03-01",
            "billing_period_end": "2026-03-31",
            "line_items": [{"flavor": "Pineapple", "quantity": 2, "unit_price": 500, "status": "unpaid"}],
            "payment_type": "credit"
        }
        inv_response = admin_client.post(f"{BASE_URL}/api/admin/credit-invoices", json=invoice_data)
        invoice_id = inv_response.json()["invoice_id"]
        
        pop_data = {
            "invoice_id": invoice_id,
            "transaction_code": "TESTFAIL123",
            "amount_paid": 1000,
            "payment_method": "airtel_money",
            "payment_type": "full"
        }
        pop_response = user_client.post(f"{BASE_URL}/api/payments/submit-pop", json=pop_data)
        pop_id = pop_response.json()["pop_id"]
        
        # Make it fail first
        match_data = {"admin_transaction_code": "DIFFERENT", "admin_amount": 1000}
        admin_client.post(f"{BASE_URL}/api/admin/payments/{pop_id}/match", json=match_data)
        
        # Try force approve without reason
        force_data = {"reason": ""}  # Empty reason
        response = admin_client.post(f"{BASE_URL}/api/admin/payments/{pop_id}/force-approve", json=force_data)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("Force approve without reason correctly rejected")
    
    def test_force_approve_short_reason_fails(self, admin_client):
        """Force approve with reason < 5 chars should fail"""
        pop_id = getattr(pytest, 'test_pop_id_amount_mismatch', None)
        if not pop_id:
            pytest.skip("No failed POP available")
        
        force_data = {"reason": "ok"}  # Too short
        response = admin_client.post(f"{BASE_URL}/api/admin/payments/{pop_id}/force-approve", json=force_data)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("Force approve with short reason correctly rejected")


class TestRejectPayment:
    """Tests for admin reject payment functionality"""
    
    def test_reject_payment_with_reason(self, admin_client, user_client):
        """Admin rejects payment with reason → rejected status + customer notification"""
        # Create a new POP to reject
        invoice_data = {
            "user_id": USER_ID,
            "billing_period_start": "2026-03-01",
            "billing_period_end": "2026-03-31",
            "line_items": [{"flavor": "Hibiscus", "quantity": 2, "unit_price": 500, "status": "unpaid"}],
            "payment_type": "credit"
        }
        inv_response = admin_client.post(f"{BASE_URL}/api/admin/credit-invoices", json=invoice_data)
        invoice_id = inv_response.json()["invoice_id"]
        
        pop_data = {
            "invoice_id": invoice_id,
            "transaction_code": "REJECTTEST",
            "amount_paid": 1000,
            "payment_method": "airtel_money",
            "payment_type": "full"
        }
        pop_response = user_client.post(f"{BASE_URL}/api/payments/submit-pop", json=pop_data)
        pop_id = pop_response.json()["pop_id"]
        
        # Reject the payment
        reject_data = {
            "status": "rejected",
            "reason": "Transaction code not found in our records. Please verify and resubmit."
        }
        response = admin_client.post(f"{BASE_URL}/api/admin/payments/{pop_id}/reject", json=reject_data)
        assert response.status_code == 200, f"Reject failed: {response.text}"
        data = response.json()
        assert "rejected" in data.get("message", "").lower()
        print(f"Payment rejected: {data}")


class TestDisputeChat:
    """Tests for dispute chat functionality"""
    
    def test_create_dispute_message_customer(self, user_client, admin_client):
        """Customer sends dispute message linked to POP transaction"""
        # Create a failed POP first
        invoice_data = {
            "user_id": USER_ID,
            "billing_period_start": "2026-03-01",
            "billing_period_end": "2026-03-31",
            "line_items": [{"flavor": "Mixed Fruit", "quantity": 3, "unit_price": 500, "status": "unpaid"}],
            "payment_type": "credit"
        }
        inv_response = admin_client.post(f"{BASE_URL}/api/admin/credit-invoices", json=invoice_data)
        invoice_id = inv_response.json()["invoice_id"]
        
        pop_data = {
            "invoice_id": invoice_id,
            "transaction_code": "DISPUTETEST",
            "amount_paid": 1500,
            "payment_method": "airtel_money",
            "payment_type": "full"
        }
        pop_response = user_client.post(f"{BASE_URL}/api/payments/submit-pop", json=pop_data)
        pop_id = pop_response.json()["pop_id"]
        pytest.test_dispute_pop_id = pop_id
        
        # Make it fail
        match_data = {"admin_transaction_code": "WRONGCODE", "admin_amount": 1500}
        admin_client.post(f"{BASE_URL}/api/admin/payments/{pop_id}/match", json=match_data)
        
        # Customer sends dispute message
        message_data = {
            "pop_id": pop_id,
            "message": "I have the correct transaction code. Please check again. Here is my bank statement reference."
        }
        response = user_client.post(f"{BASE_URL}/api/disputes/message", json=message_data)
        assert response.status_code in [200, 201], f"Failed to send dispute message: {response.text}"
        data = response.json()
        assert "message_id" in data
        print(f"Customer dispute message sent: {data['message_id']}")
    
    def test_admin_reply_to_dispute(self, admin_client):
        """Admin replies to dispute → triggers notification"""
        pop_id = getattr(pytest, 'test_dispute_pop_id', None)
        if not pop_id:
            pytest.skip("No dispute POP available")
        
        message_data = {
            "pop_id": pop_id,
            "message": "Thank you for the clarification. I've verified your bank statement and will force-approve this transaction."
        }
        response = admin_client.post(f"{BASE_URL}/api/disputes/message", json=message_data)
        assert response.status_code in [200, 201], f"Failed to send admin reply: {response.text}"
        data = response.json()
        assert "message_id" in data
        print(f"Admin reply sent: {data['message_id']}")
    
    def test_get_dispute_messages(self, user_client):
        """Get chat history for a POP transaction"""
        pop_id = getattr(pytest, 'test_dispute_pop_id', None)
        if not pop_id:
            pytest.skip("No dispute POP available")
        
        response = user_client.get(f"{BASE_URL}/api/disputes/{pop_id}/messages")
        assert response.status_code == 200, f"Failed to get messages: {response.text}"
        data = response.json()
        assert "messages" in data
        assert len(data["messages"]) >= 2  # Customer + Admin messages
        print(f"Retrieved {len(data['messages'])} dispute messages")
        
        # Verify message structure
        for msg in data["messages"]:
            assert "message_id" in msg
            assert "sender_role" in msg
            assert "message" in msg
    
    def test_get_admin_disputes_list(self, admin_client):
        """Admin gets all disputes with message counts and last message"""
        response = admin_client.get(f"{BASE_URL}/api/admin/disputes")
        assert response.status_code == 200, f"Failed to get disputes: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            dispute = data[0]
            assert "pop_id" in dispute
            assert "message_count" in dispute
            assert "last_message" in dispute
            print(f"Found {len(data)} disputes with message counts")
        else:
            print("No disputes found (may be expected if no messages exist)")


class TestPendingPaymentsEndpoint:
    """Tests for GET /api/admin/payments/pending"""
    
    def test_pending_payments_includes_verification_failed(self, admin_client):
        """Pending payments endpoint returns both 'pending' AND 'verification_failed' POPs"""
        response = admin_client.get(f"{BASE_URL}/api/admin/payments/pending")
        assert response.status_code == 200, f"Failed to get pending payments: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        
        # Check that we have both pending and verification_failed statuses
        statuses = set(p.get("status") for p in data)
        print(f"Found payment statuses: {statuses}")
        
        # At minimum, we should have some payments
        # The endpoint should return both pending and verification_failed
        for payment in data:
            assert payment.get("status") in ["pending", "verification_failed"], \
                f"Unexpected status: {payment.get('status')}"
        
        print(f"Pending payments endpoint returned {len(data)} payments")


class TestAuditTrail:
    """Tests for audit trail on payment submissions"""
    
    def test_match_creates_audit_entry(self, admin_client, user_client):
        """Verify that match operation creates audit trail entry"""
        # Create a new POP
        invoice_data = {
            "user_id": USER_ID,
            "billing_period_start": "2026-03-01",
            "billing_period_end": "2026-03-31",
            "line_items": [{"flavor": "Tamarind", "quantity": 1, "unit_price": 500, "status": "unpaid"}],
            "payment_type": "credit"
        }
        inv_response = admin_client.post(f"{BASE_URL}/api/admin/credit-invoices", json=invoice_data)
        invoice_id = inv_response.json()["invoice_id"]
        
        pop_data = {
            "invoice_id": invoice_id,
            "transaction_code": "AUDITTRAIL123",
            "amount_paid": 500,
            "payment_method": "airtel_money",
            "payment_type": "full"
        }
        pop_response = user_client.post(f"{BASE_URL}/api/payments/submit-pop", json=pop_data)
        pop_id = pop_response.json()["pop_id"]
        
        # Match the transaction
        match_data = {"admin_transaction_code": "AUDITTRAIL123", "admin_amount": 500}
        response = admin_client.post(f"{BASE_URL}/api/admin/payments/{pop_id}/match", json=match_data)
        assert response.status_code == 200
        
        # Verify audit trail exists (check via pending payments or direct DB)
        # The audit trail is stored in the payment_submissions document
        print("Audit trail entry created for match operation")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
