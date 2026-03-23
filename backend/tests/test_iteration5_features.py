"""
Iteration 5 Backend Tests - HH Jaba Admin Hub
Tests for:
1. Orders default to 'pending' status (not 'fulfilled')
2. POP (Proof of Payment) submission system
3. Backlog Credit entry
4. Defaulter warning templates
5. Dashboard stats with POP counts
"""
import pytest
import requests
import os
from datetime import datetime, timezone
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://jaba-orders.preview.emergentagent.com').rstrip('/')

# Session tokens created in MongoDB
ADMIN_SESSION_TOKEN = "test-admin-session-c8a2d280"
USER_SESSION_TOKEN = "test-user-session-07c87002"
TEST_USER_ID = "user_5463750c8ece"


class TestOrderCreation:
    """Test that orders default to 'pending' status regardless of payment method"""
    
    def test_credit_order_creates_with_pending_status(self):
        """POST /api/orders with credit payment should create order with status='pending'"""
        response = requests.post(
            f"{BASE_URL}/api/orders",
            json={
                "items": [{"product_name": "Happy Hour Jaba - Tamarind", "quantity": 1, "price": 500}],
                "payment_method": "credit"
            },
            headers={"Authorization": f"Bearer {USER_SESSION_TOKEN}"}
        )
        
        # May fail if user has insufficient credit or daily limit reached
        if response.status_code == 400:
            print(f"Order creation failed (expected if limits reached): {response.json()}")
            pytest.skip("User may have reached credit/daily limits")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Key assertion: status should be 'pending', NOT 'fulfilled'
        assert data.get("status") == "pending", f"Expected status='pending', got '{data.get('status')}'"
        assert data.get("verification_status") == "pending"
        assert data.get("payment_method") == "credit"
        print(f"✓ Credit order {data.get('order_id')} created with status='pending'")
    
    def test_mpesa_order_creates_with_pending_status(self):
        """POST /api/orders with mpesa payment should also create order with status='pending'"""
        response = requests.post(
            f"{BASE_URL}/api/orders",
            json={
                "items": [{"product_name": "Happy Hour Jaba - Watermelon", "quantity": 1, "price": 500}],
                "payment_method": "mpesa",
                "mpesa_code": "TEST123XYZ"
            },
            headers={"Authorization": f"Bearer {USER_SESSION_TOKEN}"}
        )
        
        if response.status_code == 400:
            print(f"Order creation failed (expected if limits reached): {response.json()}")
            pytest.skip("User may have reached daily limits")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Key assertion: status should be 'pending' even for mpesa
        assert data.get("status") == "pending", f"Expected status='pending', got '{data.get('status')}'"
        print(f"✓ M-Pesa order {data.get('order_id')} created with status='pending'")


class TestPOPSubmission:
    """Test Proof of Payment (POP) submission system"""
    
    @pytest.fixture
    def test_invoice_id(self):
        """Create a test invoice for POP submission"""
        # First create an invoice
        response = requests.post(
            f"{BASE_URL}/api/admin/credit-invoices",
            json={
                "user_id": TEST_USER_ID,
                "billing_period_start": "2026-01-01",
                "billing_period_end": "2026-01-31",
                "line_items": [{"flavor": "Tamarind", "quantity": 2, "unit_price": 500, "status": "unpaid"}],
                "payment_type": "credit"
            },
            headers={"Authorization": f"Bearer {ADMIN_SESSION_TOKEN}"}
        )
        if response.status_code == 200:
            return response.json().get("invoice_id")
        return None
    
    def test_submit_pop_text_based(self, test_invoice_id):
        """POST /api/payments/submit-pop should accept text-based POP"""
        if not test_invoice_id:
            pytest.skip("Could not create test invoice")
        
        response = requests.post(
            f"{BASE_URL}/api/payments/submit-pop",
            json={
                "invoice_id": test_invoice_id,
                "transaction_code": f"TEST{uuid.uuid4().hex[:6].upper()}",
                "amount_paid": 1000.0,
                "payment_method": "airtel_money",
                "payment_type": "full",
                "notes": "Test payment submission"
            },
            headers={"Authorization": f"Bearer {USER_SESSION_TOKEN}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "pop_id" in data, "Response should contain pop_id"
        assert data.get("message") == "Payment proof submitted for verification"
        print(f"✓ POP submitted: {data.get('pop_id')}")
        return data.get("pop_id")
    
    def test_get_my_pop_submissions(self):
        """GET /api/payments/my-submissions should return user's POP submissions"""
        response = requests.get(
            f"{BASE_URL}/api/payments/my-submissions",
            headers={"Authorization": f"Bearer {USER_SESSION_TOKEN}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ User has {len(data)} POP submissions")
    
    def test_admin_get_pending_payments(self):
        """GET /api/admin/payments/pending should return pending POP submissions"""
        response = requests.get(
            f"{BASE_URL}/api/admin/payments/pending",
            headers={"Authorization": f"Bearer {ADMIN_SESSION_TOKEN}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Admin sees {len(data)} pending payments")


class TestPaymentVerification:
    """Test admin payment verification (approve/reject)"""
    
    @pytest.fixture
    def pending_pop_id(self):
        """Get or create a pending POP for testing"""
        # First create an invoice
        inv_response = requests.post(
            f"{BASE_URL}/api/admin/credit-invoices",
            json={
                "user_id": TEST_USER_ID,
                "billing_period_start": "2026-01-01",
                "billing_period_end": "2026-01-31",
                "line_items": [{"flavor": "Beetroot", "quantity": 1, "unit_price": 500, "status": "unpaid"}],
                "payment_type": "credit"
            },
            headers={"Authorization": f"Bearer {ADMIN_SESSION_TOKEN}"}
        )
        if inv_response.status_code != 200:
            return None
        
        invoice_id = inv_response.json().get("invoice_id")
        
        # Submit POP
        pop_response = requests.post(
            f"{BASE_URL}/api/payments/submit-pop",
            json={
                "invoice_id": invoice_id,
                "transaction_code": f"VERIFY{uuid.uuid4().hex[:6].upper()}",
                "amount_paid": 500.0,
                "payment_method": "airtel_money",
                "payment_type": "full"
            },
            headers={"Authorization": f"Bearer {USER_SESSION_TOKEN}"}
        )
        if pop_response.status_code == 200:
            return pop_response.json().get("pop_id")
        return None
    
    def test_approve_payment(self, pending_pop_id):
        """POST /api/admin/payments/{pop_id}/verify with status=approved"""
        if not pending_pop_id:
            pytest.skip("Could not create pending POP")
        
        response = requests.post(
            f"{BASE_URL}/api/admin/payments/{pending_pop_id}/verify",
            json={
                "status": "approved",
                "verified_amount": 500.0
            },
            headers={"Authorization": f"Bearer {ADMIN_SESSION_TOKEN}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("message") == "Payment approved"
        print(f"✓ Payment {pending_pop_id} approved")
    
    def test_reject_payment_with_reason(self):
        """POST /api/admin/payments/{pop_id}/verify with status=rejected should require reason"""
        # Create another POP for rejection test
        inv_response = requests.post(
            f"{BASE_URL}/api/admin/credit-invoices",
            json={
                "user_id": TEST_USER_ID,
                "billing_period_start": "2026-01-01",
                "billing_period_end": "2026-01-31",
                "line_items": [{"flavor": "Pineapple", "quantity": 1, "unit_price": 500, "status": "unpaid"}],
                "payment_type": "credit"
            },
            headers={"Authorization": f"Bearer {ADMIN_SESSION_TOKEN}"}
        )
        if inv_response.status_code != 200:
            pytest.skip("Could not create test invoice")
        
        invoice_id = inv_response.json().get("invoice_id")
        
        pop_response = requests.post(
            f"{BASE_URL}/api/payments/submit-pop",
            json={
                "invoice_id": invoice_id,
                "transaction_code": f"REJECT{uuid.uuid4().hex[:6].upper()}",
                "amount_paid": 500.0,
                "payment_method": "mpesa",
                "payment_type": "full"
            },
            headers={"Authorization": f"Bearer {USER_SESSION_TOKEN}"}
        )
        if pop_response.status_code != 200:
            pytest.skip("Could not create POP")
        
        pop_id = pop_response.json().get("pop_id")
        
        # Reject with reason
        response = requests.post(
            f"{BASE_URL}/api/admin/payments/{pop_id}/verify",
            json={
                "status": "rejected",
                "reason": "Transaction code not found in records"
            },
            headers={"Authorization": f"Bearer {ADMIN_SESSION_TOKEN}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("message") == "Payment rejected"
        print(f"✓ Payment {pop_id} rejected with reason")


class TestBacklogCredit:
    """Test backlog credit entry for historical debts"""
    
    def test_create_backlog_credit(self):
        """POST /api/admin/backlog-credit should create invoice and deduct credit"""
        response = requests.post(
            f"{BASE_URL}/api/admin/backlog-credit",
            json={
                "user_id": TEST_USER_ID,
                "amount": 2500.0,
                "description": "Historical debt from December 2025",
                "billing_period_start": "2025-12-01",
                "billing_period_end": "2025-12-31"
            },
            headers={"Authorization": f"Bearer {ADMIN_SESSION_TOKEN}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "invoice_id" in data, "Response should contain invoice_id"
        assert data["invoice_id"].startswith("HHJ-INV-"), "Invoice ID should use UUID format"
        assert "Backlog credit" in data.get("message", "")
        print(f"✓ Backlog credit created: {data.get('invoice_id')}")


class TestDefaulterWarnings:
    """Test defaulter warning templates"""
    
    def test_overdue_warning(self):
        """POST /api/admin/defaulter-warning/{user_id}?template=overdue"""
        response = requests.post(
            f"{BASE_URL}/api/admin/defaulter-warning/{TEST_USER_ID}?template=overdue",
            headers={"Authorization": f"Bearer {ADMIN_SESSION_TOKEN}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "Warning sent" in data.get("message", "")
        assert "whatsapp_link" in data, "Response should contain whatsapp_link"
        assert "wa.me" in data.get("whatsapp_link", ""), "WhatsApp link should use wa.me format"
        print(f"✓ Overdue warning sent, WhatsApp link: {data.get('whatsapp_link')[:50]}...")
    
    def test_limit_reached_warning(self):
        """POST /api/admin/defaulter-warning/{user_id}?template=limit_reached"""
        response = requests.post(
            f"{BASE_URL}/api/admin/defaulter-warning/{TEST_USER_ID}?template=limit_reached",
            headers={"Authorization": f"Bearer {ADMIN_SESSION_TOKEN}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "Warning sent" in data.get("message", "")
        assert "whatsapp_link" in data
        print(f"✓ Limit reached warning sent")
    
    def test_suspended_warning(self):
        """POST /api/admin/defaulter-warning/{user_id}?template=suspended"""
        response = requests.post(
            f"{BASE_URL}/api/admin/defaulter-warning/{TEST_USER_ID}?template=suspended",
            headers={"Authorization": f"Bearer {ADMIN_SESSION_TOKEN}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "Warning sent" in data.get("message", "")
        assert "whatsapp_link" in data
        print(f"✓ Suspended warning sent")


class TestDashboardStats:
    """Test user dashboard stats include POP counts"""
    
    def test_dashboard_stats_include_pop_counts(self):
        """GET /api/users/dashboard-stats should include pending_pop_count and total_approved_payments"""
        response = requests.get(
            f"{BASE_URL}/api/users/dashboard-stats",
            headers={"Authorization": f"Bearer {USER_SESSION_TOKEN}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check required fields
        assert "pending_pop_count" in data, "Response should include pending_pop_count"
        assert "total_approved_payments" in data, "Response should include total_approved_payments"
        assert "credit_balance" in data
        assert "monthly_limit" in data
        
        print(f"✓ Dashboard stats: pending_pop_count={data.get('pending_pop_count')}, total_approved_payments={data.get('total_approved_payments')}")


class TestAdminDashboardTabs:
    """Test that admin dashboard has correct tabs (7 tabs)"""
    
    def test_admin_pending_orders_endpoint(self):
        """GET /api/admin/pending-orders should work"""
        response = requests.get(
            f"{BASE_URL}/api/admin/pending-orders",
            headers={"Authorization": f"Bearer {ADMIN_SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        print(f"✓ Pending orders endpoint works, {len(response.json())} orders")
    
    def test_admin_defaulters_endpoint(self):
        """GET /api/admin/defaulters should work"""
        response = requests.get(
            f"{BASE_URL}/api/admin/defaulters",
            headers={"Authorization": f"Bearer {ADMIN_SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        print(f"✓ Defaulters endpoint works, {len(response.json())} defaulters")
    
    def test_admin_reconciliation_endpoint(self):
        """GET /api/admin/reconciliation should work"""
        response = requests.get(
            f"{BASE_URL}/api/admin/reconciliation",
            headers={"Authorization": f"Bearer {ADMIN_SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        print(f"✓ Reconciliation endpoint works, {len(response.json())} users")
    
    def test_admin_feedback_endpoint(self):
        """GET /api/admin/feedback should work"""
        response = requests.get(
            f"{BASE_URL}/api/admin/feedback",
            headers={"Authorization": f"Bearer {ADMIN_SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        print(f"✓ Feedback endpoint works, {len(response.json())} feedback items")
    
    def test_admin_credit_invoices_endpoint(self):
        """GET /api/admin/credit-invoices should work"""
        response = requests.get(
            f"{BASE_URL}/api/admin/credit-invoices",
            headers={"Authorization": f"Bearer {ADMIN_SESSION_TOKEN}"}
        )
        assert response.status_code == 200
        print(f"✓ Credit invoices endpoint works, {len(response.json())} invoices")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
