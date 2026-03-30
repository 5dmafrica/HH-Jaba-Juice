import asyncio

from fastapi.testclient import TestClient

from backend import server


client = TestClient(server.app)


def test_admin_send_credit_invoice_email(monkeypatch):
    sent_emails = []
    invoice = {
        "invoice_id": "INV-001",
        "customer_name": "Buyer One",
        "customer_email": "buyer.one@5dm.africa",
        "billing_period_start": "2026-03-01",
        "billing_period_end": "2026-03-31",
        "line_items": [{"flavor": "Tamarind", "quantity": 2, "unit_price": 500, "line_total": 1000, "status": "unpaid"}],
        "total_amount": 1000,
        "status": "unpaid",
        "payment_method": "Airtel Money",
        "payment_number": "0733878020",
        "company_email": "contact@myhappyhour.co.ke",
    }

    async def fake_get_admin_user(request):
        return {"user_id": "admin-1", "email": "admin@5dm.africa", "name": "Admin"}

    async def fake_fetchone(sql, params=None):
        if "FROM credit_invoices" in sql:
            return dict(invoice)
        return None

    async def fake_send_email(recipient_email, subject, html_content):
        sent_emails.append((recipient_email, subject, html_content))
        return {"messageId": "brevo-1"}

    monkeypatch.setattr(server, "get_admin_user", fake_get_admin_user)
    monkeypatch.setattr(server, "db_fetchone", fake_fetchone)
    monkeypatch.setattr(server, "send_email", fake_send_email)

    response = client.post("/api/admin/credit-invoices/INV-001/send-email")

    assert response.status_code == 200
    assert response.json()["recipient"] == "buyer.one@5dm.africa"
    assert sent_emails[0][0] == "buyer.one@5dm.africa"
    assert "Invoice Resent" in sent_emails[0][1]
    assert "INV-001" in sent_emails[0][2]


def test_user_send_credit_invoice_email(monkeypatch):
    sent_emails = []
    invoice = {
        "invoice_id": "INV-002",
        "user_id": "user-1",
        "customer_name": "Buyer One",
        "customer_email": "buyer.one@5dm.africa",
        "billing_period_start": "2026-03-01",
        "billing_period_end": "2026-03-31",
        "line_items": [{"flavor": "Watermelon", "quantity": 3, "unit_price": 500, "line_total": 1500, "status": "unpaid"}],
        "total_amount": 1500,
        "status": "unpaid",
        "payment_method": "Airtel Money",
        "payment_number": "0733878020",
    }

    async def fake_get_current_user(request):
        return {"user_id": "user-1", "email": "buyer.one@5dm.africa", "name": "Buyer One"}

    async def fake_fetchone(sql, params=None):
        if "FROM credit_invoices" in sql:
            return dict(invoice)
        return None

    async def fake_send_email(recipient_email, subject, html_content):
        sent_emails.append((recipient_email, subject, html_content))
        return {"messageId": "brevo-2"}

    monkeypatch.setattr(server, "get_current_user", fake_get_current_user)
    monkeypatch.setattr(server, "db_fetchone", fake_fetchone)
    monkeypatch.setattr(server, "send_email", fake_send_email)

    response = client.post("/api/users/invoices/INV-002/send-email")

    assert response.status_code == 200
    assert response.json()["recipient"] == "buyer.one@5dm.africa"
    assert sent_emails[0][0] == "buyer.one@5dm.africa"
    assert "Invoice Copy" in sent_emails[0][1]


def test_create_credit_invoice_auto_sends_email(monkeypatch):
    executed = []
    captured_invoice = {}

    async def fake_get_admin_user(request):
        return {"user_id": "admin-1", "email": "admin@5dm.africa", "name": "Admin User"}

    async def fake_fetchone(sql, params=None):
        if "SELECT * FROM users WHERE user_id=%s" in sql:
            return {
                "user_id": "user-1",
                "name": "Buyer One",
                "email": "buyer.one@5dm.africa",
                "phone": "+254700000000",
            }
        if "SELECT * FROM credit_invoices WHERE invoice_id=%s" in sql:
            return {
                "invoice_id": params[0],
                "user_id": "user-1",
                "customer_name": "Buyer One",
                "customer_email": "buyer.one@5dm.africa",
                "customer_phone": "+254700000000",
                "billing_period_start": "2026-03-01",
                "billing_period_end": "2026-03-31",
                "line_items": [{"flavor": "Tamarind", "quantity": 5, "unit_price": 500, "line_total": 2500, "status": "unpaid"}],
                "subtotal": 2500,
                "total_amount": 2500,
                "status": "unpaid",
                "payment_method": "Airtel Money",
                "payment_number": "0733878020",
                "company_email": "contact@myhappyhour.co.ke",
            }
        return None

    async def fake_execute(sql, params=None):
        executed.append((sql, params))
        return 1

    async def fake_send_credit_invoice_email(invoice, recipient_email=None, subject_prefix="Invoice Ready"):
        captured_invoice["invoice"] = dict(invoice)
        captured_invoice["subject_prefix"] = subject_prefix
        return {"messageId": "brevo-3"}

    monkeypatch.setattr(server, "get_admin_user", fake_get_admin_user)
    monkeypatch.setattr(server, "db_fetchone", fake_fetchone)
    monkeypatch.setattr(server, "db_execute", fake_execute)
    monkeypatch.setattr(server, "send_credit_invoice_email", fake_send_credit_invoice_email)

    response = client.post(
        "/api/admin/credit-invoices",
        json={
            "user_id": "user-1",
            "billing_period_start": "2026-03-01",
            "billing_period_end": "2026-03-31",
            "line_items": [{"flavor": "Tamarind", "quantity": 5, "unit_price": 500, "status": "unpaid"}],
            "notes": "Monthly invoice",
            "payment_type": "credit",
        },
    )

    assert response.status_code == 200
    assert response.json()["email_sent"] is True
    assert captured_invoice["invoice"]["customer_email"] == "buyer.one@5dm.africa"
    assert any("INSERT INTO notifications" in sql for sql, _ in executed)


def test_match_transaction_failure_sends_decline_email(monkeypatch):
    sent_emails = []
    executed = []
    pop = {
        "pop_id": "POP-1",
        "invoice_id": "INV-003",
        "user_id": "user-1",
        "user_name": "Buyer One",
        "user_email": "buyer.one@5dm.africa",
        "transaction_code": "CUSTOMER123",
        "amount_paid": 2000,
        "status": "pending",
    }

    async def fake_get_admin_user(request):
        return {"user_id": "admin-1", "email": "admin@5dm.africa", "name": "Admin User"}

    async def fake_fetchone(sql, params=None):
        if "FROM payment_submissions" in sql:
            return dict(pop)
        return None

    async def fake_execute(sql, params=None):
        executed.append((sql, params))
        return 1

    async def fake_send_email(recipient_email, subject, html_content):
        sent_emails.append((recipient_email, subject, html_content))
        return {"messageId": "brevo-4"}

    monkeypatch.setattr(server, "get_admin_user", fake_get_admin_user)
    monkeypatch.setattr(server, "db_fetchone", fake_fetchone)
    monkeypatch.setattr(server, "db_execute", fake_execute)
    monkeypatch.setattr(server, "send_email", fake_send_email)

    response = client.post(
        "/api/admin/payments/POP-1/match",
        json={"admin_transaction_code": "ADMIN999", "admin_amount": 1800},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "verification_failed"
    assert sent_emails[0][0] == "buyer.one@5dm.africa"
    assert "Payment Verification Failed" in sent_emails[0][1]
    assert "Code mismatch" in sent_emails[0][2]
    assert any("verification_failed" in sql for sql, _ in executed)


def test_apply_approved_payment_sends_email(monkeypatch):
    sent_emails = []
    executed = []

    async def fake_fetchone(sql, params=None):
        if "FROM credit_invoices WHERE invoice_id=%s" in sql:
            return {"invoice_id": "INV-004", "total_amount": 2500}
        if "SUM(verified_amount)" in sql:
            return {"total": 2500}
        if "SELECT credit_balance FROM users" in sql:
            return {"credit_balance": 28000}
        return None

    async def fake_execute(sql, params=None):
        executed.append((sql, params))
        return 1

    async def fake_send_email(recipient_email, subject, html_content):
        sent_emails.append((recipient_email, subject, html_content))
        return {"messageId": "brevo-5"}

    monkeypatch.setattr(server, "db_fetchone", fake_fetchone)
    monkeypatch.setattr(server, "db_execute", fake_execute)
    monkeypatch.setattr(server, "send_email", fake_send_email)

    asyncio.run(
        server._apply_approved_payment(
            {
                "pop_id": "POP-2",
                "invoice_id": "INV-004",
                "user_id": "user-1",
                "user_name": "Buyer One",
                "user_email": "buyer.one@5dm.africa",
            },
            2500,
            "Approved after manual review",
        )
    )

    assert any("UPDATE credit_invoices SET status=%s, total_paid=%s" in sql for sql, _ in executed)
    assert sent_emails[0][0] == "buyer.one@5dm.africa"
    assert "Payment Approved" in sent_emails[0][1]
    assert "Approved after manual review" in sent_emails[0][2]


def test_create_notification_sends_push_offer_email(monkeypatch):
    sent_emails = []
    executed = []

    async def fake_get_admin_user(request):
        return {"user_id": "admin-1", "email": "admin@5dm.africa", "name": "Admin User"}

    async def fake_fetchone(sql, params=None):
        if "SELECT user_id, email, name FROM users WHERE user_id=%s" in sql:
            return {"user_id": "user-1", "email": "buyer.one@5dm.africa", "name": "Buyer One"}
        return None

    async def fake_execute(sql, params=None):
        executed.append((sql, params))
        return 1

    async def fake_send_email(recipient_email, subject, html_content):
        sent_emails.append((recipient_email, subject, html_content))
        return {"messageId": "brevo-6"}

    monkeypatch.setattr(server, "get_admin_user", fake_get_admin_user)
    monkeypatch.setattr(server, "db_fetchone", fake_fetchone)
    monkeypatch.setattr(server, "db_execute", fake_execute)
    monkeypatch.setattr(server, "send_email", fake_send_email)

    response = client.post(
        "/api/admin/notifications",
        json={
            "title": "Weekend Offer",
            "message": "Get 10% off your next order.",
            "notification_type": "offer",
            "target_users": ["user-1"],
        },
    )

    assert response.status_code == 200
    assert sent_emails[0][0] == "buyer.one@5dm.africa"
    assert sent_emails[0][1] == "Weekend Offer - HH Jaba"
    assert "Get 10% off your next order." in sent_emails[0][2]
    assert any("INSERT INTO notifications" in sql for sql, _ in executed)