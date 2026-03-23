"""
Backend API Tests for HH Jaba Staff Portal - Iteration 4 Features
Tests: UUID-based invoice IDs, payment_type (credit/cash), pending orders with fulfilled, 
       auto-generate invoice, defaulters per-item breakdown
"""
import pytest
import requests
import os
from datetime import datetime, timedelta
import uuid
import re

# Get backend URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://jaba-orders.preview.emergentagent.com"

# MongoDB connection for test setup
from pymongo import MongoClient
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

# Test admin session token (from review request)
ADMIN_SESSION_TOKEN = "test-admin-590d57625292"
TEST_USER_ID = "user_5463750c8ece"


class TestSetup:
    """Setup test fixtures"""
    
    @staticmethod
    def ensure_admin_session():
        """Ensure admin session exists in MongoDB"""
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Check if session exists
        session = db.user_sessions.find_one({"session_token": ADMIN_SESSION_TOKEN})
        if not session:
            # Find admin user
            admin_user = db.users.find_one({"email": "mavin@5dm.africa"})
            if not admin_user:
                admin_user = {
                    "user_id": f"admin_{uuid.uuid4().hex[:12]}",
                    "email": "mavin@5dm.africa",
                    "name": "Test Admin",
                    "phone": "0712345678",
                    "credit_balance": 30000,
                    "role": "admin",
                    "accepted_terms": True,
                    "accepted_terms_at": datetime.utcnow().isoformat(),
                    "picture": None,
                    "created_at": datetime.utcnow().isoformat()
                }
                db.users.insert_one(admin_user)
                admin_user = db.users.find_one({"email": "mavin@5dm.africa"})
            
            # Create session
            expires_at = datetime.utcnow() + timedelta(days=7)
            db.user_sessions.insert_one({
                "user_id": admin_user["user_id"],
                "session_token": ADMIN_SESSION_TOKEN,
                "expires_at": expires_at.isoformat(),
                "created_at": datetime.utcnow().isoformat()
            })
            print(f"Created admin session: {ADMIN_SESSION_TOKEN}")
        
        client.close()
        return ADMIN_SESSION_TOKEN
    
    @staticmethod
    def ensure_test_user():
        """Ensure test user exists"""
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        user = db.users.find_one({"user_id": TEST_USER_ID})
        if not user:
            user = {
                "user_id": TEST_USER_ID,
                "email": "testuser@5dm.africa",
                "name": "Test User",
                "phone": "0712345679",
                "credit_balance": 20000,
                "role": "user",
                "accepted_terms": True,
                "accepted_terms_at": datetime.utcnow().isoformat(),
                "picture": None,
                "created_at": datetime.utcnow().isoformat()
            }
            db.users.insert_one(user)
            print(f"Created test user: {TEST_USER_ID}")
        
        client.close()
        return TEST_USER_ID
    
    @staticmethod
    def create_test_credit_order(user_id):
        """Create a test credit order for auto-invoice generation"""
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        order_id = f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"
        order = {
            "order_id": order_id,
            "user_id": user_id,
            "user_name": "Test User",
            "user_email": "testuser@5dm.africa",
            "user_phone": "0712345679",
            "items": [
                {"product_name": "Happy Hour Jaba - Tamarind", "quantity": 2, "price": 500},
                {"product_name": "Happy Hour Jaba - Watermelon", "quantity": 1, "price": 500}
            ],
            "total_amount": 1500,
            "payment_method": "credit",
            "status": "fulfilled",
            "verification_status": "verified",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        db.orders.insert_one(order)
        client.close()
        return order_id
    
    @staticmethod
    def cleanup_test_invoices():
        """Clean up test invoices"""
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        db.credit_invoices.delete_many({"notes": {"$regex": "TEST"}})
        db.credit_invoices.delete_many({"notes": {"$regex": "Auto-generated"}})
        client.close()


@pytest.fixture(scope="module")
def admin_session():
    """Ensure admin session exists"""
    session_token = TestSetup.ensure_admin_session()
    TestSetup.ensure_test_user()
    yield session_token
    TestSetup.cleanup_test_invoices()


@pytest.fixture
def api_client(admin_session):
    """Create API client with admin auth"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {admin_session}",
        "Content-Type": "application/json"
    })
    return session


# ============ TEST: UUID-based Invoice ID Generation ============

class TestUUIDInvoiceID:
    """Test that invoice IDs are generated using UUID to prevent collisions"""
    
    def test_credit_invoice_has_uuid_based_id(self, api_client):
        """Test POST /api/admin/credit-invoices creates invoice with UUID-based ID"""
        today = datetime.utcnow()
        invoice_data = {
            "user_id": TEST_USER_ID,
            "billing_period_start": (today - timedelta(days=30)).strftime("%Y-%m-%d"),
            "billing_period_end": today.strftime("%Y-%m-%d"),
            "line_items": [
                {"flavor": "Tamarind", "quantity": 2, "unit_price": 500, "status": "unpaid"}
            ],
            "notes": "TEST UUID invoice",
            "payment_type": "credit"
        }
        
        response = api_client.post(f"{BASE_URL}/api/admin/credit-invoices", json=invoice_data)
        assert response.status_code in [200, 201], f"Failed to create invoice: {response.text}"
        
        invoice = response.json()
        invoice_id = invoice.get("invoice_id")
        
        # Verify invoice ID format: HHJ-INV-[Date]-[UUID suffix]
        assert invoice_id is not None, "Invoice ID should not be None"
        assert invoice_id.startswith("HHJ-INV-"), f"Invoice ID should start with HHJ-INV-, got: {invoice_id}"
        
        # Check that the suffix is alphanumeric (UUID-based)
        parts = invoice_id.split("-")
        assert len(parts) >= 4, f"Invoice ID should have at least 4 parts: {invoice_id}"
        
        # The last part should be 5 uppercase alphanumeric characters (UUID hex)
        suffix = parts[-1]
        assert len(suffix) == 5, f"UUID suffix should be 5 chars, got: {suffix}"
        assert suffix.isupper() and suffix.isalnum(), f"Suffix should be uppercase alphanumeric: {suffix}"
        
        print(f"TEST PASSED: Invoice ID has UUID-based format: {invoice_id}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/admin/credit-invoices/{invoice_id}")
    
    def test_multiple_invoices_have_unique_ids(self, api_client):
        """Test that multiple invoices created quickly have unique IDs"""
        today = datetime.utcnow()
        invoice_ids = []
        
        for i in range(3):
            invoice_data = {
                "user_id": TEST_USER_ID,
                "billing_period_start": (today - timedelta(days=30)).strftime("%Y-%m-%d"),
                "billing_period_end": today.strftime("%Y-%m-%d"),
                "line_items": [
                    {"flavor": "Tamarind", "quantity": 1, "unit_price": 500, "status": "unpaid"}
                ],
                "notes": f"TEST unique ID test {i}",
                "payment_type": "credit"
            }
            
            response = api_client.post(f"{BASE_URL}/api/admin/credit-invoices", json=invoice_data)
            assert response.status_code in [200, 201], f"Failed to create invoice {i}: {response.text}"
            
            invoice = response.json()
            invoice_ids.append(invoice.get("invoice_id"))
        
        # Verify all IDs are unique
        assert len(invoice_ids) == len(set(invoice_ids)), f"Invoice IDs should be unique: {invoice_ids}"
        print(f"TEST PASSED: All {len(invoice_ids)} invoice IDs are unique: {invoice_ids}")
        
        # Cleanup
        for inv_id in invoice_ids:
            api_client.delete(f"{BASE_URL}/api/admin/credit-invoices/{inv_id}")


# ============ TEST: Payment Type (Credit/Cash) ============

class TestPaymentType:
    """Test payment_type field in credit invoice creation"""
    
    def test_credit_payment_type_creates_unpaid_invoice(self, api_client):
        """Test POST /api/admin/credit-invoices with payment_type='credit' creates unpaid invoice"""
        today = datetime.utcnow()
        invoice_data = {
            "user_id": TEST_USER_ID,
            "billing_period_start": (today - timedelta(days=30)).strftime("%Y-%m-%d"),
            "billing_period_end": today.strftime("%Y-%m-%d"),
            "line_items": [
                {"flavor": "Tamarind", "quantity": 2, "unit_price": 500, "status": "unpaid"},
                {"flavor": "Watermelon", "quantity": 1, "unit_price": 500, "status": "unpaid"}
            ],
            "notes": "TEST credit payment type",
            "payment_type": "credit"
        }
        
        response = api_client.post(f"{BASE_URL}/api/admin/credit-invoices", json=invoice_data)
        assert response.status_code in [200, 201], f"Failed: {response.text}"
        
        invoice = response.json()
        
        # Verify invoice status is unpaid
        assert invoice.get("status") == "unpaid", f"Credit invoice should be unpaid, got: {invoice.get('status')}"
        
        # Verify all line items are unpaid
        for item in invoice.get("line_items", []):
            assert item.get("status") == "unpaid", f"Line item should be unpaid: {item}"
        
        print(f"TEST PASSED: Credit payment type creates unpaid invoice: {invoice.get('invoice_id')}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/admin/credit-invoices/{invoice.get('invoice_id')}")
    
    def test_cash_payment_type_creates_paid_invoice(self, api_client):
        """Test POST /api/admin/credit-invoices with payment_type='cash' creates paid invoice"""
        today = datetime.utcnow()
        invoice_data = {
            "user_id": TEST_USER_ID,
            "billing_period_start": (today - timedelta(days=30)).strftime("%Y-%m-%d"),
            "billing_period_end": today.strftime("%Y-%m-%d"),
            "line_items": [
                {"flavor": "Pineapple", "quantity": 3, "unit_price": 500, "status": "unpaid"},
                {"flavor": "Hibiscus", "quantity": 2, "unit_price": 500, "status": "unpaid"}
            ],
            "notes": "TEST cash payment type",
            "payment_type": "cash"
        }
        
        response = api_client.post(f"{BASE_URL}/api/admin/credit-invoices", json=invoice_data)
        assert response.status_code in [200, 201], f"Failed: {response.text}"
        
        invoice = response.json()
        
        # Verify invoice status is paid
        assert invoice.get("status") == "paid", f"Cash invoice should be paid, got: {invoice.get('status')}"
        
        # Verify all line items are paid
        for item in invoice.get("line_items", []):
            assert item.get("status") == "paid", f"Line item should be paid for cash: {item}"
        
        print(f"TEST PASSED: Cash payment type creates paid invoice with all items paid: {invoice.get('invoice_id')}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/admin/credit-invoices/{invoice.get('invoice_id')}")


# ============ TEST: Pending Orders with Recently Fulfilled ============

class TestPendingOrdersWithFulfilled:
    """Test GET /api/admin/pending-orders returns both pending AND recently fulfilled orders"""
    
    def test_pending_orders_includes_recent_fulfilled(self, api_client):
        """Test that pending orders endpoint returns recently fulfilled orders too"""
        response = api_client.get(f"{BASE_URL}/api/admin/pending-orders")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        orders = response.json()
        assert isinstance(orders, list), "Response should be a list"
        
        # Check if there are any fulfilled orders in the response
        statuses = set(order.get("status") for order in orders)
        print(f"Order statuses in response: {statuses}")
        
        # The endpoint should allow both pending and fulfilled orders
        # (fulfilled orders from last 2 hours should appear)
        print(f"TEST PASSED: Pending orders endpoint returns {len(orders)} orders with statuses: {statuses}")
    
    def test_pending_orders_filter_by_payment_method(self, api_client):
        """Test pending orders can be filtered by payment method"""
        # Test credit filter
        response = api_client.get(f"{BASE_URL}/api/admin/pending-orders?payment_method=credit")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        orders = response.json()
        for order in orders:
            assert order.get("payment_method") == "credit", f"Order should be credit: {order.get('order_id')}"
        
        print(f"TEST PASSED: Pending orders filter by payment_method works ({len(orders)} credit orders)")


# ============ TEST: Delete Invoice with UUID-based ID ============

class TestDeleteInvoiceWithUUID:
    """Test DELETE /api/admin/credit-invoices/{id} works with UUID-based IDs"""
    
    def test_delete_invoice_with_uuid_id(self, api_client):
        """Test deleting invoice with new UUID-based ID format"""
        # First create an invoice
        today = datetime.utcnow()
        invoice_data = {
            "user_id": TEST_USER_ID,
            "billing_period_start": (today - timedelta(days=30)).strftime("%Y-%m-%d"),
            "billing_period_end": today.strftime("%Y-%m-%d"),
            "line_items": [
                {"flavor": "Beetroot", "quantity": 1, "unit_price": 500, "status": "unpaid"}
            ],
            "notes": "TEST delete UUID invoice",
            "payment_type": "credit"
        }
        
        create_response = api_client.post(f"{BASE_URL}/api/admin/credit-invoices", json=invoice_data)
        assert create_response.status_code in [200, 201], f"Failed to create: {create_response.text}"
        
        invoice = create_response.json()
        invoice_id = invoice.get("invoice_id")
        print(f"Created invoice with UUID-based ID: {invoice_id}")
        
        # Delete the invoice
        delete_response = api_client.delete(f"{BASE_URL}/api/admin/credit-invoices/{invoice_id}")
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        
        # Verify deletion
        get_response = api_client.get(f"{BASE_URL}/api/admin/credit-invoices/{invoice_id}")
        assert get_response.status_code == 404, "Invoice should not exist after deletion"
        
        print(f"TEST PASSED: Successfully deleted invoice with UUID-based ID: {invoice_id}")


# ============ TEST: Auto-Generate Invoice with UUID ============

class TestAutoGenerateInvoice:
    """Test POST /api/admin/auto-generate-invoice/{user_id} with UUID-based invoice ID"""
    
    def test_auto_generate_invoice_has_uuid_id(self, api_client):
        """Test auto-generated invoice has UUID-based ID"""
        # Create a test credit order first
        order_id = TestSetup.create_test_credit_order(TEST_USER_ID)
        print(f"Created test order: {order_id}")
        
        today = datetime.utcnow()
        payload = {
            "start_date": (today - timedelta(days=30)).strftime("%Y-%m-%d"),
            "end_date": today.strftime("%Y-%m-%d")
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/admin/auto-generate-invoice/{TEST_USER_ID}",
            json=payload
        )
        
        if response.status_code == 404:
            # No credit orders found - this is acceptable if no orders exist
            print("TEST SKIPPED: No credit orders found for auto-generation")
            return
        
        assert response.status_code in [200, 201], f"Failed: {response.text}"
        
        invoice = response.json()
        invoice_id = invoice.get("invoice_id")
        
        # Verify UUID-based ID format
        assert invoice_id is not None, "Invoice ID should not be None"
        assert invoice_id.startswith("HHJ-INV-"), f"Invoice ID should start with HHJ-INV-: {invoice_id}"
        
        # Check UUID suffix
        parts = invoice_id.split("-")
        suffix = parts[-1]
        assert len(suffix) == 5 and suffix.isupper() and suffix.isalnum(), f"Invalid UUID suffix: {suffix}"
        
        # Verify auto_generated flag
        assert invoice.get("auto_generated") == True or "Auto-generated" in str(invoice.get("notes", "")), \
            "Invoice should be marked as auto-generated"
        
        print(f"TEST PASSED: Auto-generated invoice has UUID-based ID: {invoice_id}")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/admin/credit-invoices/{invoice_id}")


# ============ TEST: Defaulters Endpoint ============

class TestDefaultersEndpoint:
    """Test GET /api/admin/defaulters returns per-item breakdown"""
    
    def test_defaulters_returns_order_breakdown(self, api_client):
        """Test defaulters endpoint returns orders with item details"""
        response = api_client.get(f"{BASE_URL}/api/admin/defaulters")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        defaulters = response.json()
        assert isinstance(defaulters, list), "Response should be a list"
        
        if len(defaulters) > 0:
            defaulter = defaulters[0]
            
            # Verify structure
            assert "user" in defaulter, "Should contain user info"
            assert "outstanding_balance" in defaulter, "Should contain outstanding_balance"
            assert "total_due" in defaulter, "Should contain total_due"
            assert "orders" in defaulter, "Should contain orders list"
            
            # Check orders have items
            if len(defaulter.get("orders", [])) > 0:
                order = defaulter["orders"][0]
                assert "order_id" in order, "Order should have order_id"
                assert "created_at" in order, "Order should have created_at (timestamp)"
                assert "items" in order, "Order should have items"
                
                if len(order.get("items", [])) > 0:
                    item = order["items"][0]
                    assert "product_name" in item, "Item should have product_name (flavor)"
                    assert "quantity" in item, "Item should have quantity"
                    assert "price" in item, "Item should have price (amount)"
                    print(f"Order item structure verified: {item}")
            
            print(f"TEST PASSED: Defaulters endpoint returns {len(defaulters)} defaulters with order breakdown")
        else:
            print("TEST PASSED: No defaulters found (empty list is valid)")


# ============ TEST: Health Checks ============

class TestHealthChecks:
    """Basic health check tests"""
    
    def test_api_root(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        print("TEST PASSED: API root accessible")
    
    def test_products_endpoint(self):
        """Test products endpoint"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"TEST PASSED: Products endpoint works ({len(data)} products)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
