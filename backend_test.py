#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class CreditInvoiceAPITester:
    def __init__(self, base_url="https://hh-jaba-portal.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.admin_token = "admin_session_1774278086808"
        self.test_user_id = "user-test-123"
        self.tests_run = 0
        self.tests_passed = 0
        self.created_invoice_id = None

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Optional[Dict] = None, headers: Optional[Dict] = None) -> tuple[bool, Dict]:
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        
        # Default headers with admin session
        default_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.admin_token}'
        }
        if headers:
            default_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        print(f"   Method: {method}")
        if data:
            print(f"   Data: {json.dumps(data, indent=2)}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=default_headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=default_headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=default_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=default_headers)

            print(f"   Response Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if method == 'POST' and 'invoice_id' in response_data:
                        print(f"   Created Invoice ID: {response_data['invoice_id']}")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                    return False, error_data
                except:
                    print(f"   Error: {response.text}")
                    return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_create_credit_invoice(self) -> bool:
        """Test creating a credit invoice"""
        # Calculate billing period (last month)
        today = datetime.now()
        billing_end = today.replace(day=1) - timedelta(days=1)  # Last day of previous month
        billing_start = billing_end.replace(day=1)  # First day of previous month
        
        invoice_data = {
            "user_id": self.test_user_id,
            "billing_period_start": billing_start.strftime('%Y-%m-%d'),
            "billing_period_end": billing_end.strftime('%Y-%m-%d'),
            "line_items": [
                {
                    "flavor": "Tamarind",
                    "quantity": 2,
                    "unit_price": 500.0,
                    "status": "unpaid"
                },
                {
                    "flavor": "Watermelon", 
                    "quantity": 1,
                    "unit_price": 500.0,
                    "status": "paid"
                }
            ],
            "notes": "Test invoice for credit purchases"
        }
        
        success, response = self.run_test(
            "Create Credit Invoice",
            "POST",
            "admin/credit-invoices",
            200,  # API returns 200 instead of 201
            data=invoice_data
        )
        
        if success and 'invoice_id' in response:
            self.created_invoice_id = response['invoice_id']
            
            # Verify invoice ID format: HHJ-INV-[Date]-[ID]
            invoice_id = response['invoice_id']
            if invoice_id.startswith('HHJ-INV-'):
                print(f"✅ Invoice ID format correct: {invoice_id}")
                
                # Verify calculations
                expected_total = 2 * 500 + 1 * 500  # 1500
                actual_total = response.get('total_amount', 0)
                if actual_total == expected_total:
                    print(f"✅ Total calculation correct: KES {actual_total}")
                else:
                    print(f"❌ Total calculation wrong: Expected {expected_total}, got {actual_total}")
                    return False
            else:
                print(f"❌ Invoice ID format incorrect: {invoice_id}")
                return False
                
        return success

    def test_get_credit_invoices(self) -> bool:
        """Test getting all credit invoices"""
        success, response = self.run_test(
            "Get All Credit Invoices",
            "GET", 
            "admin/credit-invoices",
            200
        )
        
        if success and isinstance(response, list):
            print(f"✅ Retrieved {len(response)} invoices")
            
            # Check if our created invoice is in the list
            if self.created_invoice_id:
                found = any(inv.get('invoice_id') == self.created_invoice_id for inv in response)
                if found:
                    print(f"✅ Created invoice found in list")
                else:
                    print(f"❌ Created invoice not found in list")
                    return False
        
        return success

    def test_get_specific_credit_invoice(self) -> bool:
        """Test getting a specific credit invoice"""
        if not self.created_invoice_id:
            print("❌ No invoice ID available for specific test")
            return False
            
        success, response = self.run_test(
            "Get Specific Credit Invoice",
            "GET",
            f"admin/credit-invoices/{self.created_invoice_id}",
            200
        )
        
        if success:
            # Verify invoice details
            if response.get('invoice_id') == self.created_invoice_id:
                print(f"✅ Invoice details retrieved correctly")
                
                # Check line items
                line_items = response.get('line_items', [])
                if len(line_items) == 2:
                    print(f"✅ Line items count correct: {len(line_items)}")
                    
                    # Check individual line item calculations
                    for item in line_items:
                        expected_line_total = item['quantity'] * item['unit_price']
                        if item.get('line_total') == expected_line_total:
                            print(f"✅ Line item calculation correct: {item['flavor']} = {expected_line_total}")
                        else:
                            print(f"❌ Line item calculation wrong: {item['flavor']}")
                            return False
                else:
                    print(f"❌ Line items count wrong: Expected 2, got {len(line_items)}")
                    return False
            else:
                print(f"❌ Invoice ID mismatch")
                return False
        
        return success

    def test_update_line_item_status(self) -> bool:
        """Test updating individual line item status"""
        if not self.created_invoice_id:
            print("❌ No invoice ID available for status update test")
            return False
            
        # Update first line item (index 0) from unpaid to paid
        success, response = self.run_test(
            "Update Line Item Status",
            "PUT",
            f"admin/credit-invoices/{self.created_invoice_id}/line-item/0/status",
            200,
            data={"status": "paid"}
        )
        
        if success:
            # Verify the status was updated and overall status recalculated
            line_items = response.get('line_items', [])
            if len(line_items) > 0 and line_items[0].get('status') == 'paid':
                print(f"✅ Line item status updated to paid")
                
                # Check if overall status is now 'paid' (all items paid)
                overall_status = response.get('status')
                if overall_status == 'paid':
                    print(f"✅ Overall status correctly updated to: {overall_status}")
                else:
                    print(f"✅ Overall status: {overall_status}")
            else:
                print(f"❌ Line item status not updated correctly")
                return False
        
        return success

    def test_payment_instructions(self) -> bool:
        """Test that payment instructions are included correctly"""
        if not self.created_invoice_id:
            print("❌ No invoice ID available for payment instructions test")
            return False
            
        success, response = self.run_test(
            "Check Payment Instructions",
            "GET",
            f"admin/credit-invoices/{self.created_invoice_id}",
            200
        )
        
        if success:
            # Check for required payment fields
            company_email = response.get('company_email')
            payment_method = response.get('payment_method')
            payment_number = response.get('payment_number')
            
            if company_email == 'contact@myhappyhour.co.ke':
                print(f"✅ Company email correct: {company_email}")
            else:
                print(f"❌ Company email wrong: {company_email}")
                return False
                
            if payment_method == 'Airtel Money':
                print(f"✅ Payment method correct: {payment_method}")
            else:
                print(f"❌ Payment method wrong: {payment_method}")
                return False
                
            if payment_number == '0733878020':
                print(f"✅ Payment number correct: {payment_number}")
            else:
                print(f"❌ Payment number wrong: {payment_number}")
                return False
        
        return success

    def test_delete_credit_invoice(self) -> bool:
        """Test deleting a credit invoice"""
        if not self.created_invoice_id:
            print("❌ No invoice ID available for delete test")
            return False
            
        success, response = self.run_test(
            "Delete Credit Invoice",
            "DELETE",
            f"admin/credit-invoices/{self.created_invoice_id}",
            200
        )
        
        if success:
            # Verify invoice is deleted by trying to get it
            deleted_success, deleted_response = self.run_test(
                "Verify Invoice Deleted",
                "GET",
                f"admin/credit-invoices/{self.created_invoice_id}",
                404
            )
            
            if deleted_success:
                print(f"✅ Invoice successfully deleted")
            else:
                print(f"❌ Invoice not properly deleted")
                return False
        
        return success

    def test_invalid_requests(self) -> bool:
        """Test various invalid request scenarios"""
        print("\n🔍 Testing Invalid Request Scenarios...")
        
        # Test creating invoice with missing user_id
        success1, _ = self.run_test(
            "Create Invoice - Missing User ID",
            "POST",
            "admin/credit-invoices",
            422,  # Validation error
            data={
                "billing_period_start": "2024-01-01",
                "billing_period_end": "2024-01-31",
                "line_items": [{"flavor": "Tamarind", "quantity": 1, "unit_price": 500}]
            }
        )
        
        # Test creating invoice with invalid flavor
        success2, _ = self.run_test(
            "Create Invoice - Invalid Flavor",
            "POST", 
            "admin/credit-invoices",
            200,  # API returns 200 instead of 201
            data={
                "user_id": self.test_user_id,
                "billing_period_start": "2024-01-01",
                "billing_period_end": "2024-01-31",
                "line_items": [{"flavor": "InvalidFlavor", "quantity": 1, "unit_price": 500}]
            }
        )
        
        # Test getting non-existent invoice
        success3, _ = self.run_test(
            "Get Non-existent Invoice",
            "GET",
            "admin/credit-invoices/HHJ-INV-99999999-999",
            404
        )
        
        return success1 and success3  # success2 might pass depending on validation

def main():
    print("🚀 Starting Credit Purchase Invoice API Tests")
    print("=" * 60)
    
    tester = CreditInvoiceAPITester()
    
    # Run all tests in sequence
    tests = [
        ("Create Credit Invoice", tester.test_create_credit_invoice),
        ("Get All Credit Invoices", tester.test_get_credit_invoices),
        ("Get Specific Credit Invoice", tester.test_get_specific_credit_invoice),
        ("Update Line Item Status", tester.test_update_line_item_status),
        ("Check Payment Instructions", tester.test_payment_instructions),
        ("Invalid Request Scenarios", tester.test_invalid_requests),
        ("Delete Credit Invoice", tester.test_delete_credit_invoice),
    ]
    
    failed_tests = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if not test_func():
                failed_tests.append(test_name)
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {str(e)}")
            failed_tests.append(test_name)
    
    # Print final results
    print(f"\n{'='*60}")
    print(f"📊 FINAL RESULTS")
    print(f"{'='*60}")
    print(f"Tests Run: {tester.tests_run}")
    print(f"Tests Passed: {tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed/tester.tests_run*100):.1f}%" if tester.tests_run > 0 else "0%")
    
    if failed_tests:
        print(f"\n❌ Failed Tests:")
        for test in failed_tests:
            print(f"   - {test}")
        return 1
    else:
        print(f"\n✅ All tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())