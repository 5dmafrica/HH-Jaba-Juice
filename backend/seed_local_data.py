import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pymysql
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')


def now():
    return datetime.utcnow().replace(microsecond=0)


def db_connection(database=True):
    kwargs = {
        'host': os.environ.get('MYSQL_HOST', 'localhost'),
        'port': int(os.environ.get('MYSQL_PORT', 3306)),
        'user': os.environ.get('MYSQL_USER', 'root'),
        'password': os.environ.get('MYSQL_PASSWORD', ''),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor,
        'autocommit': False,
    }
    if database:
        kwargs['database'] = os.environ.get('MYSQL_DB', 'hhjaba')
    return pymysql.connect(**kwargs)


PRODUCTS = [
    ('prod_local_tamarind', 'Happy Hour Jaba - Tamarind', 'Refreshing tamarind flavored beer', 500.0, 80, 1, '#8B4513'),
    ('prod_local_watermelon', 'Happy Hour Jaba - Watermelon', 'Sweet watermelon flavored beer', 500.0, 65, 1, '#FF1493'),
    ('prod_local_beetroot', 'Happy Hour Jaba - Beetroot', 'Earthy beetroot flavored beer', 500.0, 52, 1, '#8B0000'),
    ('prod_local_pineapple', 'Happy Hour Jaba - Pineapple', 'Tropical pineapple flavored beer', 500.0, 74, 1, '#FFD700'),
    ('prod_local_hibiscus', 'Happy Hour Jaba - Hibiscus', 'Floral hibiscus flavored beer', 500.0, 48, 1, '#DC143C'),
]

USERS = [
    ('user_local_super_admin', 'mavin@5dm.africa', 'Mavin Local', '0711000001', 30000.0, 'super_admin'),
    ('user_local_admin', 'ops.admin@5dm.africa', 'Ops Admin', '0711000002', 30000.0, 'admin'),
    ('user_local_customer_1', 'buyer.one@5dm.africa', 'Buyer One', '0711000003', 23500.0, 'user'),
    ('user_local_customer_2', 'buyer.two@5dm.africa', 'Buyer Two', '0711000004', 28500.0, 'user'),
]


def ensure_database():
    connection = db_connection(database=False)
    try:
        with connection.cursor() as cursor:
            db_name = os.environ.get('MYSQL_DB', 'hhjaba')
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        connection.commit()
    finally:
        connection.close()


def cleanup_local_rows(cursor):
    local_user_ids = [user_id for user_id, *_ in USERS]
    local_emails = [email for _, email, *_ in USERS]

    cursor.execute("DELETE FROM dispute_messages WHERE message_id LIKE 'LOCAL-%'")
    cursor.execute("DELETE FROM payment_submissions WHERE pop_id LIKE 'LOCAL-%'")
    cursor.execute("DELETE FROM notifications WHERE notification_id LIKE 'LOCAL-%'")
    cursor.execute("DELETE FROM feedback WHERE feedback_id LIKE 'LOCAL-%'")
    cursor.execute("DELETE FROM credit_invoices WHERE invoice_id LIKE 'LOCAL-%'")
    cursor.execute("DELETE FROM orders WHERE order_id LIKE 'LOCAL-%'")
    cursor.execute("DELETE FROM user_sessions WHERE user_id IN (%s,%s,%s,%s)", local_user_ids)
    cursor.execute("DELETE FROM users WHERE email IN (%s,%s,%s,%s)", local_emails)


def seed_products(cursor, timestamp):
    for product_id, name, description, price, stock, active, color in PRODUCTS:
        cursor.execute(
            """INSERT INTO products
               (product_id, name, description, price, stock, active, color, image_url, created_at, updated_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON DUPLICATE KEY UPDATE
               name=VALUES(name), description=VALUES(description), price=VALUES(price),
               stock=VALUES(stock), active=VALUES(active), color=VALUES(color), updated_at=VALUES(updated_at)""",
            (
                product_id,
                name,
                description,
                price,
                stock,
                active,
                color,
                None,
                timestamp,
                timestamp,
            )
        )


def seed_users(cursor, timestamp):
    accepted_at = timestamp - timedelta(days=14)
    for user_id, email, name, phone, credit_balance, role in USERS:
        cursor.execute(
            """INSERT INTO users
               (user_id, email, name, phone, credit_balance, role, accepted_terms, accepted_terms_at, picture, active_role, created_at, updated_at)
               VALUES (%s,%s,%s,%s,%s,%s,1,%s,%s,%s,%s,%s)""",
            (user_id, email, name, phone, credit_balance, role, accepted_at, None, role, timestamp, timestamp)
        )


def seed_orders(cursor, timestamp):
    orders = [
        {
            'order_id': 'LOCAL-ORD-PENDING-01',
            'user_id': 'user_local_customer_1',
            'user_name': 'Buyer One',
            'user_email': 'buyer.one@5dm.africa',
            'user_phone': '0711000003',
            'items': [
                {'product_name': 'Happy Hour Jaba - Tamarind', 'quantity': 2, 'price': 500.0},
                {'product_name': 'Happy Hour Jaba - Pineapple', 'quantity': 1, 'price': 500.0},
            ],
            'total_amount': 1500.0,
            'payment_method': 'mpesa',
            'mpesa_code': 'LOCALPENDING01',
            'status': 'pending',
            'verification_status': 'pending',
            'created_at': timestamp - timedelta(hours=1),
        },
        {
            'order_id': 'LOCAL-ORD-FULFILLED-01',
            'user_id': 'user_local_customer_1',
            'user_name': 'Buyer One',
            'user_email': 'buyer.one@5dm.africa',
            'user_phone': '0711000003',
            'items': [
                {'product_name': 'Happy Hour Jaba - Watermelon', 'quantity': 3, 'price': 500.0},
            ],
            'total_amount': 1500.0,
            'payment_method': 'credit',
            'mpesa_code': None,
            'status': 'fulfilled',
            'verification_status': 'verified',
            'created_at': timestamp - timedelta(days=2),
        },
        {
            'order_id': 'LOCAL-ORD-CANCELLED-01',
            'user_id': 'user_local_customer_2',
            'user_name': 'Buyer Two',
            'user_email': 'buyer.two@5dm.africa',
            'user_phone': '0711000004',
            'items': [
                {'product_name': 'Happy Hour Jaba - Hibiscus', 'quantity': 1, 'price': 500.0},
            ],
            'total_amount': 500.0,
            'payment_method': 'credit',
            'mpesa_code': None,
            'status': 'cancelled',
            'verification_status': 'rejected',
            'created_at': timestamp - timedelta(days=1, hours=5),
        },
    ]

    for order in orders:
        cursor.execute(
            """INSERT INTO orders
               (order_id, user_id, user_name, user_email, user_phone, items, total_amount,
                payment_method, mpesa_code, status, verification_status, cancellation_reason,
                cancelled_by, cancelled_at, created_at, updated_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                order['order_id'],
                order['user_id'],
                order['user_name'],
                order['user_email'],
                order['user_phone'],
                json.dumps(order['items']),
                order['total_amount'],
                order['payment_method'],
                order['mpesa_code'],
                order['status'],
                order['verification_status'],
                'Stock check failed' if order['status'] == 'cancelled' else None,
                'Ops Admin' if order['status'] == 'cancelled' else None,
                order['created_at'] if order['status'] == 'cancelled' else None,
                order['created_at'],
                order['created_at'],
            )
        )


def seed_invoices(cursor, timestamp):
    invoice_1_items = [
        {
            'flavor': 'Watermelon',
            'quantity': 3,
            'unit_price': 500.0,
            'line_total': 1500.0,
            'status': 'unpaid',
            'order_id': 'LOCAL-ORD-FULFILLED-01',
            'order_date': (timestamp - timedelta(days=2)).isoformat(),
        }
    ]
    invoice_2_items = [
        {
            'flavor': 'Backlog Credit',
            'quantity': 1,
            'unit_price': 1000.0,
            'line_total': 1000.0,
            'status': 'unpaid',
        }
    ]

    cursor.execute(
        """INSERT INTO credit_invoices
           (invoice_id, user_id, customer_name, customer_email, customer_phone,
            billing_period_start, billing_period_end, line_items, subtotal, total_amount,
            total_paid, status, payment_type, notes, created_at, created_by,
            company_email, company_location, payment_method, payment_number, auto_generated, is_backlog)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            'LOCAL-INV-001',
            'user_local_customer_1',
            'Buyer One',
            'buyer.one@5dm.africa',
            '0711000003',
            (timestamp - timedelta(days=7)).date().isoformat(),
            timestamp.date().isoformat(),
            json.dumps(invoice_1_items),
            1500.0,
            1500.0,
            0.0,
            'unpaid',
            'credit',
            'Local seeded invoice from fulfilled credit order',
            timestamp - timedelta(days=1),
            'Ops Admin',
            'contact@myhappyhour.co.ke',
            'Nairobi',
            'Airtel Money',
            '0733878020',
            1,
            0,
        )
    )

    cursor.execute(
        """INSERT INTO credit_invoices
           (invoice_id, user_id, customer_name, customer_email, customer_phone,
            billing_period_start, billing_period_end, line_items, subtotal, total_amount,
            total_paid, status, payment_type, notes, created_at, created_by,
            company_email, company_location, payment_method, payment_number, auto_generated, is_backlog)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            'LOCAL-INV-002',
            'user_local_customer_2',
            'Buyer Two',
            'buyer.two@5dm.africa',
            '0711000004',
            (timestamp - timedelta(days=30)).date().isoformat(),
            (timestamp - timedelta(days=1)).date().isoformat(),
            json.dumps(invoice_2_items),
            1000.0,
            1000.0,
            0.0,
            'unpaid',
            'credit',
            'Backlog entry for reconciliation testing',
            timestamp - timedelta(days=3),
            'Ops Admin',
            'contact@myhappyhour.co.ke',
            'Nairobi',
            'Airtel Money',
            '0733878020',
            0,
            1,
        )
    )


def seed_payments_and_disputes(cursor, timestamp):
    cursor.execute(
        """INSERT INTO payment_submissions
           (pop_id, invoice_id, user_id, user_name, user_email, transaction_code,
            amount_paid, payment_method, payment_type, notes, status, submitted_at,
            admin_transaction_code, admin_amount, decline_reason, declined_at, declined_by, audit_trail)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            'LOCAL-POP-001',
            'LOCAL-INV-001',
            'user_local_customer_1',
            'Buyer One',
            'buyer.one@5dm.africa',
            'QWE123LOCAL',
            1500.0,
            'airtel_money',
            'full',
            'Customer says payment posted under finance batch 12',
            'verification_failed',
            timestamp - timedelta(hours=3),
            'LOCAL-MISMATCH',
            1400.0,
            'Amount mismatch: Customer KES 1,500 vs Admin KES 1,400',
            timestamp - timedelta(hours=2),
            'Ops Admin',
            json.dumps([]),
        )
    )

    cursor.execute(
        """INSERT INTO dispute_messages
           (message_id, pop_id, invoice_id, sender_id, sender_name, sender_role, message, created_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            'LOCAL-MSG-001',
            'LOCAL-POP-001',
            'LOCAL-INV-001',
            'user_local_customer_1',
            'Buyer One',
            'user',
            'The payment was full. Please recheck the finance ledger for Airtel reference QWE123LOCAL.',
            timestamp - timedelta(hours=2),
        )
    )


def seed_notifications(cursor, timestamp):
    notifications = [
        ('LOCAL-NOTIF-001', 'user_local_admin', 'New Order Received', 'Buyer One placed a pending local test order.', 'order', {'order_id': 'LOCAL-ORD-PENDING-01'}),
        ('LOCAL-NOTIF-002', 'user_local_super_admin', 'Payment Needs Review', 'Local seeded POP failed verification and needs review.', 'payment', {'pop_id': 'LOCAL-POP-001'}),
        ('LOCAL-NOTIF-003', 'user_local_customer_1', 'Invoice Ready', 'Your seeded invoice LOCAL-INV-001 is ready for payment.', 'invoice', {'invoice_id': 'LOCAL-INV-001'}),
        ('LOCAL-NOTIF-004', 'user_local_customer_2', 'Backlog Credit Added', 'A backlog credit invoice has been created for testing.', 'invoice', {'invoice_id': 'LOCAL-INV-002'}),
    ]

    for notification_id, user_id, title, message, notification_type, metadata in notifications:
        cursor.execute(
            """INSERT INTO notifications
               (notification_id, user_id, title, message, notification_type, `read`, created_at, created_by, metadata)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (notification_id, user_id, title, message, notification_type, 0, timestamp, 'seed_local_data', json.dumps(metadata))
        )


def seed_feedback(cursor, timestamp):
    cursor.execute(
        """INSERT INTO feedback
           (feedback_id, user_id, user_name, user_email, subject, message, status, created_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            'LOCAL-FB-001',
            'user_local_customer_2',
            'Buyer Two',
            'buyer.two@5dm.africa',
            'Packaging feedback',
            'Seeded note: packaging looked great, but delivery timing needs work.',
            'new',
            timestamp - timedelta(hours=4),
        )
    )


def seed_domains(cursor, timestamp):
    cursor.execute(
        """INSERT INTO approved_domains (domain, is_active, added_by, created_at, updated_at)
           VALUES (%s,1,%s,%s,%s)
           ON DUPLICATE KEY UPDATE is_active=1, updated_at=VALUES(updated_at), disabled_by=NULL, disabled_at=NULL""",
        ('5dm.africa', 'seed_local_data', timestamp, timestamp)
    )


def main():
    ensure_database()
    connection = db_connection(database=True)
    timestamp = now()

    try:
        with connection.cursor() as cursor:
            cleanup_local_rows(cursor)
            seed_domains(cursor, timestamp)
            seed_products(cursor, timestamp)
            seed_users(cursor, timestamp)
            seed_orders(cursor, timestamp)
            seed_invoices(cursor, timestamp)
            seed_payments_and_disputes(cursor, timestamp)
            seed_notifications(cursor, timestamp)
            seed_feedback(cursor, timestamp)
        connection.commit()
    finally:
        connection.close()

    print('Seeded local data successfully.')
    print('Dev login emails:')
    print('  super admin: mavin@5dm.africa')
    print('  admin: ops.admin@5dm.africa')
    print('  customer: buyer.one@5dm.africa')


if __name__ == '__main__':
    main()