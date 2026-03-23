import requests
import sys
import json
from datetime import datetime
import time

class HHJabaAPITester:
    def __init__(self, base_url="https://jaba-admin-hub.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.session_token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.session_token:
            test_headers['Authorization'] = f'Bearer {self.session_token}'
        
        if headers:
            test_headers.update(headers)

        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            
            if not success:
                details += f", Expected: {expected_status}"
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    details += f", Response: {response.text[:100]}"

            self.log_test(name, success, details)
            
            if success:
                try:
                    return response.json()
                except:
                    return {}
            return None

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return None

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root API Endpoint", "GET", "", 200)

    def test_products_api(self):
        """Test products API (should return 5 flavors)"""
        result = self.run_test("Products API", "GET", "products", 200)
        if result and isinstance(result, list):
            if len(result) == 5:
                self.log_test("Products Count (5 flavors)", True)
                # Check if all products are KES 500
                all_500 = all(product.get('price') == 500.0 for product in result)
                self.log_test("All Products KES 500", all_500, "" if all_500 else "Some products not KES 500")
            else:
                self.log_test("Products Count (5 flavors)", False, f"Found {len(result)} products, expected 5")
        return result

    def create_test_session(self):
        """Create test user and session using MongoDB"""
        print("\n🔧 Creating test user and session...")
        
        import subprocess
        
        # Create test user and session
        mongo_script = f"""
use('test_database');
var userId = 'test-user-{int(time.time())}';
var sessionToken = 'test_session_{int(time.time())}';
var email = 'test.user.{int(time.time())}@5dm.africa';

// Create user
db.users.insertOne({{
  user_id: userId,
  email: email,
  name: 'Test User',
  phone: '0712345678',
  credit_balance: 10000,
  role: 'user',
  accepted_terms: true,
  accepted_terms_at: new Date(),
  picture: 'https://via.placeholder.com/150',
  created_at: new Date()
}});

// Create session
db.user_sessions.insertOne({{
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
}});

print('SESSION_TOKEN:' + sessionToken);
print('USER_ID:' + userId);
print('EMAIL:' + email);
"""
        
        try:
            result = subprocess.run(['mongosh', '--eval', mongo_script], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                output = result.stdout
                for line in output.split('\n'):
                    if line.startswith('SESSION_TOKEN:'):
                        self.session_token = line.split(':', 1)[1]
                    elif line.startswith('USER_ID:'):
                        self.user_id = line.split(':', 1)[1]
                
                if self.session_token and self.user_id:
                    self.log_test("Create Test User & Session", True, f"User ID: {self.user_id}")
                    return True
                else:
                    self.log_test("Create Test User & Session", False, "Failed to extract session token or user ID")
                    return False
            else:
                self.log_test("Create Test User & Session", False, f"MongoDB error: {result.stderr}")
                return False
                
        except Exception as e:
            self.log_test("Create Test User & Session", False, f"Exception: {str(e)}")
            return False

    def test_auth_me(self):
        """Test auth/me endpoint"""
        return self.run_test("Auth Me Endpoint", "GET", "auth/me", 200)

    def test_credit_balance(self):
        """Test credit balance endpoint"""
        return self.run_test("Credit Balance", "GET", "users/credit-balance", 200)

    def test_create_order_credit(self):
        """Test order creation with credit payment"""
        order_data = {
            "items": [
                {
                    "product_name": "Happy Hour Jaba - Tamarind",
                    "quantity": 2,
                    "price": 500.0
                }
            ],
            "payment_method": "credit"
        }
        return self.run_test("Create Order (Credit)", "POST", "orders", 200, order_data)

    def test_create_order_mpesa(self):
        """Test order creation with M-Pesa payment"""
        order_data = {
            "items": [
                {
                    "product_name": "Happy Hour Jaba - Watermelon",
                    "quantity": 1,
                    "price": 500.0
                }
            ],
            "payment_method": "mpesa",
            "mpesa_code": "TEST123ABC"
        }
        return self.run_test("Create Order (M-Pesa)", "POST", "orders", 200, order_data)

    def test_order_history(self):
        """Test order history endpoint"""
        return self.run_test("Order History", "GET", "orders", 200)

    def create_admin_session(self):
        """Create admin user session for admin tests"""
        print("\n🔧 Creating admin user session...")
        
        import subprocess
        
        mongo_script = f"""
use('test_database');
var adminUserId = 'admin-user-{int(time.time())}';
var adminSessionToken = 'admin_session_{int(time.time())}';
var adminEmail = 'mavin@5dm.africa';

// Create admin user
db.users.insertOne({{
  user_id: adminUserId,
  email: adminEmail,
  name: 'Admin User',
  phone: '0712345679',
  credit_balance: 10000,
  role: 'admin',
  accepted_terms: true,
  accepted_terms_at: new Date(),
  picture: 'https://via.placeholder.com/150',
  created_at: new Date()
}});

// Create admin session
db.user_sessions.insertOne({{
  user_id: adminUserId,
  session_token: adminSessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
}});

print('ADMIN_SESSION_TOKEN:' + adminSessionToken);
print('ADMIN_USER_ID:' + adminUserId);
"""
        
        try:
            result = subprocess.run(['mongosh', '--eval', mongo_script], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                output = result.stdout
                admin_token = None
                for line in output.split('\n'):
                    if line.startswith('ADMIN_SESSION_TOKEN:'):
                        admin_token = line.split(':', 1)[1]
                
                if admin_token:
                    self.log_test("Create Admin Session", True)
                    return admin_token
                else:
                    self.log_test("Create Admin Session", False, "Failed to extract admin session token")
                    return None
            else:
                self.log_test("Create Admin Session", False, f"MongoDB error: {result.stderr}")
                return None
                
        except Exception as e:
            self.log_test("Create Admin Session", False, f"Exception: {str(e)}")
            return None

    def test_admin_endpoints(self):
        """Test admin-only endpoints"""
        admin_token = self.create_admin_session()
        if not admin_token:
            return
        
        # Temporarily switch to admin token
        original_token = self.session_token
        self.session_token = admin_token
        
        # Test admin endpoints
        self.run_test("Admin Pending Orders", "GET", "admin/pending-orders", 200)
        self.run_test("Admin All Products", "GET", "products/all", 200)
        self.run_test("Admin Reconciliation", "GET", "admin/reconciliation", 200)
        self.run_test("Admin Defaulters", "GET", "admin/defaulters", 200)
        self.run_test("Admin Users", "GET", "admin/users", 200)
        self.run_test("Admin Manual Invoices", "GET", "admin/manual-invoices", 200)
        
        # Restore original token
        self.session_token = original_token

    def test_profile_setup(self):
        """Test profile setup endpoint"""
        profile_data = {
            "phone": "0712345678",
            "accept_terms": True
        }
        return self.run_test("Profile Setup", "POST", "users/profile-setup", 200, profile_data)

    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting HH Jaba Staff Portal API Tests")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Basic API tests
        self.test_root_endpoint()
        products = self.test_products_api()
        
        # Create test session for authenticated tests
        if not self.create_test_session():
            print("❌ Cannot proceed without test session")
            return self.get_summary()
        
        # Authenticated user tests
        self.test_auth_me()
        self.test_credit_balance()
        self.test_profile_setup()
        
        # Order tests
        self.test_create_order_credit()
        self.test_create_order_mpesa()
        self.test_order_history()
        
        # Admin tests
        self.test_admin_endpoints()
        
        return self.get_summary()

    def get_summary(self):
        """Get test summary"""
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
        else:
            print("⚠️  Some tests failed")
            failed_tests = [r for r in self.test_results if not r['success']]
            for test in failed_tests:
                print(f"   - {test['test']}: {test['details']}")
        
        return {
            "total_tests": self.tests_run,
            "passed_tests": self.tests_passed,
            "success_rate": (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0,
            "test_results": self.test_results
        }

def main():
    tester = HHJabaAPITester()
    summary = tester.run_all_tests()
    return 0 if summary["success_rate"] == 100 else 1

if __name__ == "__main__":
    sys.exit(main())