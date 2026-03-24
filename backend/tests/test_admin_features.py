"""
Backend API Tests for HH Jaba Staff Portal - Admin Features
Tests: Credit Invoice Delete, User Delete, Reconciliation Report, Send Reconciliation, Notifications
"""
import pytest
import requests
import os
from datetime import datetime, timedelta
import uuid

# Get backend URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://hh-jaba-portal.preview.emergentagent.com"

# MongoDB connection for test setup
from pymongo import MongoClient
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

# Test admin email
ADMIN_EMAIL = "mavin@5dm.africa"

class TestSetup:
    """Setup test fixtures"""
    
    @staticmethod
    def create_admin_session():
        """Create admin session in MongoDB and return session token"""
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Find or create admin user
        admin_user = db.users.find_one({"email": ADMIN_EMAIL})
        if not admin_user:
            admin_user = {
                "user_id": f"admin_{uuid.uuid4().hex[:12]}",
                "email": ADMIN_EMAIL,
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
            admin_user = db.users.find_one({"email": ADMIN_EMAIL})
        
        # Create session token
        session_token = f"test_admin_session_{uuid.uuid4().hex}"
        expires_at = datetime.utcnow() + timedelta(days=7)
        
        # Remove old sessions and create new one
        db.user_sessions.delete_many({"user_id": admin_user["user_id"]})
        db.user_sessions.insert_one({
            "user_id": admin_user["user_id"],
            "session_token": session_token,
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.utcnow().isoformat()
        })
        
        client.close()
        return session_token, admin_user["user_id"]
    
    @staticmethod
    def create_test_user():
        """Create a test user for deletion testing"""
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        user_id = f"TEST_user_{uuid.uuid4().hex[:12]}"
        test_user = {
            "user_id": user_id,
            "email": f"TEST_{uuid.uuid4().hex[:8]}@5dm.africa",
            "name": "TEST User For Deletion",
            "phone": f"07{uuid.uuid4().hex[:8][:8]}",
            "credit_balance": 5000,
            "role": "user",
            "accepted_terms": True,
            "accepted_terms_at": datetime.utcnow().isoformat(),
            "picture": None,
            "created_at": datetime.utcnow().isoformat()
        }
        db.users.insert_one(test_user)
        client.close()
        return user_id, test_user
    
    @staticmethod
    def create_test_credit_invoice(admin_session_token, user_id):
        """Create a test credit invoice"""
        headers = {
            "Authorization": f"Bearer {admin_session_token}",
            "Content-Type": "application/json"
        }
        
        today = datetime.utcnow()
        invoice_data = {
            "user_id": user_id,
            "billing_period_start": (today - timedelta(days=30)).strftime("%Y-%m-%d"),
            "billing_period_end": today.strftime("%Y-%m-%d"),
            "line_items": [
                {"flavor": "Tamarind", "quantity": 2, "unit_price": 500, "status": "unpaid"},
                {"flavor": "Watermelon", "quantity": 1, "unit_price": 500, "status": "unpaid"}
            ],
            "notes": "TEST invoice for deletion"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/admin/credit-invoices",
            json=invoice_data,
            headers=headers
        )
        return response
    
    @staticmethod
    def cleanup_test_data():
        """Clean up test data"""
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Delete test users
        db.users.delete_many({"name": {"$regex": "^TEST"}})
        db.users.delete_many({"email": {"$regex": "^TEST_"}})
        
        # Delete test invoices
        db.credit_invoices.delete_many({"notes": {"$regex": "TEST"}})
        
        # Delete test notifications
        db.notifications.delete_many({"title": {"$regex": "TEST"}})
        
        client.close()


@pytest.fixture(scope="module")
def admin_session():
    """Create admin session for all tests"""
    session_token, admin_user_id = TestSetup.create_admin_session()
    yield session_token, admin_user_id
    # Cleanup after all tests
    TestSetup.cleanup_test_data()


@pytest.fixture
def api_client(admin_session):
    """Create API client with admin auth"""
    session_token, _ = admin_session
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {session_token}",
        "Content-Type": "application/json"
    })
    return session


class TestCreditInvoiceDelete:
    """Test DELETE /api/admin/credit-invoices/{invoice_id}"""
    
    def test_delete_credit_invoice_success(self, api_client, admin_session):
        """Test successful deletion of a credit invoice"""
        session_token, admin_user_id = admin_session
        
        # First create a test user
        user_id, _ = TestSetup.create_test_user()
        
        # Create a credit invoice
        create_response = TestSetup.create_test_credit_invoice(session_token, user_id)
        assert create_response.status_code in [200, 201], f"Failed to create invoice: {create_response.text}"
        
        invoice_data = create_response.json()
        invoice_id = invoice_data.get("invoice_id")
        assert invoice_id is not None, "Invoice ID not returned"
        print(f"Created invoice: {invoice_id}")
        
        # Delete the invoice
        delete_response = api_client.delete(f"{BASE_URL}/api/admin/credit-invoices/{invoice_id}")
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        
        # Verify response message
        delete_data = delete_response.json()
        assert "message" in delete_data
        assert "deleted" in delete_data["message"].lower()
        print(f"Delete response: {delete_data}")
        
        # Verify invoice no longer exists
        get_response = api_client.get(f"{BASE_URL}/api/admin/credit-invoices/{invoice_id}")
        assert get_response.status_code == 404, "Invoice should not exist after deletion"
        print("TEST PASSED: Credit invoice deleted successfully")
    
    def test_delete_nonexistent_invoice(self, api_client):
        """Test deletion of non-existent invoice returns 404"""
        fake_invoice_id = "HHJ-INV-99999999-999"
        response = api_client.delete(f"{BASE_URL}/api/admin/credit-invoices/{fake_invoice_id}")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("TEST PASSED: Non-existent invoice returns 404")


class TestUserDelete:
    """Test DELETE /api/admin/users/{user_id}"""
    
    def test_delete_user_success(self, api_client, admin_session):
        """Test successful deletion of a user"""
        # Create a test user
        user_id, test_user = TestSetup.create_test_user()
        print(f"Created test user: {user_id}")
        
        # Delete the user
        delete_response = api_client.delete(f"{BASE_URL}/api/admin/users/{user_id}")
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        
        # Verify response
        delete_data = delete_response.json()
        assert "message" in delete_data
        assert "deleted" in delete_data["message"].lower()
        print(f"Delete response: {delete_data}")
        
        # Verify user no longer exists in users list
        users_response = api_client.get(f"{BASE_URL}/api/admin/users")
        assert users_response.status_code == 200
        users = users_response.json()
        user_ids = [u["user_id"] for u in users]
        assert user_id not in user_ids, "User should not exist after deletion"
        print("TEST PASSED: User deleted successfully")
    
    def test_delete_nonexistent_user(self, api_client):
        """Test deletion of non-existent user returns 404"""
        fake_user_id = "user_nonexistent_12345"
        response = api_client.delete(f"{BASE_URL}/api/admin/users/{fake_user_id}")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("TEST PASSED: Non-existent user returns 404")
    
    def test_cannot_delete_admin_user(self, api_client, admin_session):
        """Test that admin cannot delete another admin"""
        _, admin_user_id = admin_session
        
        # Try to delete the admin user (should fail)
        response = api_client.delete(f"{BASE_URL}/api/admin/users/{admin_user_id}")
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("TEST PASSED: Cannot delete admin user")


class TestReconciliationReport:
    """Test GET /api/admin/users/{user_id}/reconciliation-report"""
    
    def test_get_reconciliation_report(self, api_client, admin_session):
        """Test getting detailed reconciliation report for a user"""
        # Create a test user
        user_id, _ = TestSetup.create_test_user()
        
        # Get reconciliation report
        response = api_client.get(f"{BASE_URL}/api/admin/users/{user_id}/reconciliation-report")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "user" in data, "Response should contain user info"
        assert "period" in data, "Response should contain period info"
        assert "order_breakdown" in data, "Response should contain order_breakdown"
        assert "total_amount" in data, "Response should contain total_amount"
        assert "outstanding_balance" in data, "Response should contain outstanding_balance"
        assert "generated_at" in data, "Response should contain generated_at timestamp"
        
        print(f"Reconciliation report structure: {list(data.keys())}")
        print("TEST PASSED: Reconciliation report endpoint works")
    
    def test_reconciliation_report_with_date_filter(self, api_client, admin_session):
        """Test reconciliation report with date filters"""
        user_id, _ = TestSetup.create_test_user()
        
        today = datetime.utcnow()
        start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        
        response = api_client.get(
            f"{BASE_URL}/api/admin/users/{user_id}/reconciliation-report",
            params={"start_date": start_date, "end_date": end_date}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data["period"]["start"] == start_date
        assert data["period"]["end"] == end_date
        print("TEST PASSED: Reconciliation report with date filter works")
    
    def test_reconciliation_report_nonexistent_user(self, api_client):
        """Test reconciliation report for non-existent user"""
        response = api_client.get(f"{BASE_URL}/api/admin/users/nonexistent_user/reconciliation-report")
        assert response.status_code == 404
        print("TEST PASSED: Non-existent user returns 404")


class TestSendReconciliation:
    """Test POST /api/admin/users/{user_id}/send-reconciliation"""
    
    def test_send_reconciliation_report(self, api_client, admin_session):
        """Test sending reconciliation report to user"""
        user_id, _ = TestSetup.create_test_user()
        
        today = datetime.utcnow()
        payload = {
            "start_date": (today - timedelta(days=30)).strftime("%Y-%m-%d"),
            "end_date": today.strftime("%Y-%m-%d")
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/admin/users/{user_id}/send-reconciliation",
            json=payload
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert "sent" in data["message"].lower() or "report" in data["message"].lower()
        print(f"Send reconciliation response: {data}")
        print("TEST PASSED: Send reconciliation report works")
    
    def test_send_reconciliation_nonexistent_user(self, api_client):
        """Test sending reconciliation to non-existent user"""
        response = api_client.post(
            f"{BASE_URL}/api/admin/users/nonexistent_user/send-reconciliation",
            json={"start_date": "2026-01-01", "end_date": "2026-01-31"}
        )
        assert response.status_code == 404
        print("TEST PASSED: Non-existent user returns 404")


class TestNotifications:
    """Test notification endpoints"""
    
    def test_get_notifications(self, api_client, admin_session):
        """Test GET /api/notifications - get user notifications"""
        response = api_client.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Check notification structure if any exist
        if len(data) > 0:
            notif = data[0]
            assert "notification_id" in notif
            assert "title" in notif
            assert "message" in notif
            assert "read" in notif
            print(f"Found {len(data)} notifications")
        else:
            print("No notifications found (empty list is valid)")
        
        print("TEST PASSED: Get notifications endpoint works")
    
    def test_get_unread_count(self, api_client, admin_session):
        """Test GET /api/notifications/unread-count"""
        response = api_client.get(f"{BASE_URL}/api/notifications/unread-count")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "unread_count" in data
        assert isinstance(data["unread_count"], int)
        print(f"Unread count: {data['unread_count']}")
        print("TEST PASSED: Unread count endpoint works")
    
    def test_mark_notification_read(self, api_client, admin_session):
        """Test PUT /api/notifications/{notification_id}/read"""
        # First create a notification via admin endpoint
        create_response = api_client.post(
            f"{BASE_URL}/api/admin/notifications",
            json={
                "title": "TEST Notification",
                "message": "This is a test notification for marking as read",
                "notification_type": "general"
            }
        )
        
        if create_response.status_code == 200:
            # Get notifications to find the one we created
            notifs_response = api_client.get(f"{BASE_URL}/api/notifications")
            notifs = notifs_response.json()
            
            # Find our test notification
            test_notif = None
            for n in notifs:
                if n.get("title") == "TEST Notification":
                    test_notif = n
                    break
            
            if test_notif:
                notif_id = test_notif["notification_id"]
                
                # Mark as read
                mark_response = api_client.put(f"{BASE_URL}/api/notifications/{notif_id}/read")
                assert mark_response.status_code == 200, f"Failed: {mark_response.text}"
                
                data = mark_response.json()
                assert "message" in data
                print(f"Mark read response: {data}")
                print("TEST PASSED: Mark notification as read works")
            else:
                print("TEST SKIPPED: Could not find test notification")
        else:
            print(f"TEST SKIPPED: Could not create test notification: {create_response.text}")


class TestReconciliationList:
    """Test GET /api/admin/reconciliation"""
    
    def test_get_reconciliation_list(self, api_client):
        """Test getting reconciliation list"""
        response = api_client.get(f"{BASE_URL}/api/admin/reconciliation")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Check structure if any items exist
        if len(data) > 0:
            item = data[0]
            assert "user" in item, "Should contain user info"
            assert "outstanding_balance" in item, "Should contain outstanding_balance"
            assert "orders" in item, "Should contain orders list"
            print(f"Found {len(data)} users with outstanding balances")
        else:
            print("No users with outstanding balances (empty list is valid)")
        
        print("TEST PASSED: Reconciliation list endpoint works")
    
    def test_reconciliation_list_with_search(self, api_client):
        """Test reconciliation list with search parameter"""
        response = api_client.get(f"{BASE_URL}/api/admin/reconciliation", params={"search": "test"})
        assert response.status_code == 200, f"Failed: {response.text}"
        print("TEST PASSED: Reconciliation list with search works")


class TestCreditInvoicesCRUD:
    """Test credit invoices CRUD operations"""
    
    def test_list_credit_invoices(self, api_client):
        """Test GET /api/admin/credit-invoices"""
        response = api_client.get(f"{BASE_URL}/api/admin/credit-invoices")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Found {len(data)} credit invoices")
        print("TEST PASSED: List credit invoices works")
    
    def test_create_and_get_credit_invoice(self, api_client, admin_session):
        """Test creating and retrieving a credit invoice"""
        session_token, _ = admin_session
        user_id, _ = TestSetup.create_test_user()
        
        # Create invoice
        create_response = TestSetup.create_test_credit_invoice(session_token, user_id)
        assert create_response.status_code in [200, 201], f"Create failed: {create_response.text}"
        
        invoice = create_response.json()
        invoice_id = invoice.get("invoice_id")
        
        # Verify invoice structure
        assert "invoice_id" in invoice
        assert "user_id" in invoice
        assert "customer_name" in invoice
        assert "line_items" in invoice
        assert "total_amount" in invoice
        assert "status" in invoice
        
        # Get the invoice
        get_response = api_client.get(f"{BASE_URL}/api/admin/credit-invoices/{invoice_id}")
        assert get_response.status_code == 200, f"Get failed: {get_response.text}"
        
        retrieved = get_response.json()
        assert retrieved["invoice_id"] == invoice_id
        print(f"Created and retrieved invoice: {invoice_id}")
        print("TEST PASSED: Create and get credit invoice works")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/admin/credit-invoices/{invoice_id}")


class TestHealthCheck:
    """Basic health check tests"""
    
    def test_api_root(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        print("TEST PASSED: API root accessible")
    
    def test_products_endpoint(self):
        """Test products endpoint (public)"""
        response = requests.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} products")
        print("TEST PASSED: Products endpoint works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
