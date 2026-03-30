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
    {
        'key': 'super_admin',
        'user_id': 'user_local_super_admin',
        'email': os.environ.get('LOCAL_SUPER_ADMIN_EMAIL', 'mavin@5dm.africa'),
        'name': os.environ.get('LOCAL_SUPER_ADMIN_NAME', 'Mavin Local'),
        'phone': os.environ.get('LOCAL_SUPER_ADMIN_PHONE', '0711000001'),
        'credit_balance': 30000.0,
        'role': 'super_admin',
    },
    {
        'key': 'admin',
        'user_id': 'user_local_admin',
        'email': os.environ.get('LOCAL_ADMIN_EMAIL', 'ops.admin@5dm.africa'),
        'name': os.environ.get('LOCAL_ADMIN_NAME', 'Ops Admin'),
        'phone': os.environ.get('LOCAL_ADMIN_PHONE', '0711000002'),
        'credit_balance': 30000.0,
        'role': 'admin',
    },
    {
        'key': 'customer_primary',
        'user_id': 'user_local_customer_1',
        'email': os.environ.get('LOCAL_CUSTOMER_PRIMARY_EMAIL', 'buyer.one@5dm.africa'),
        'name': os.environ.get('LOCAL_CUSTOMER_PRIMARY_NAME', 'Buyer One'),
        'phone': os.environ.get('LOCAL_CUSTOMER_PRIMARY_PHONE', '0711000003'),
        'credit_balance': 23500.0,
        'role': 'user',
    },
    {
        'key': 'customer_secondary',
        'user_id': 'user_local_customer_2',
        'email': os.environ.get('LOCAL_CUSTOMER_SECONDARY_EMAIL', 'buyer.two@5dm.africa'),
        'name': os.environ.get('LOCAL_CUSTOMER_SECONDARY_NAME', 'Buyer Two'),
        'phone': os.environ.get('LOCAL_CUSTOMER_SECONDARY_PHONE', '0711000004'),
        'credit_balance': 28500.0,
        'role': 'user',
    },
]
USER_LOOKUP = {user['key']: user for user in USERS}


def get_seed_user(key):
    return USER_LOOKUP[key]


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
    local_user_ids = [user['user_id'] for user in USERS]
    local_emails = [user['email'] for user in USERS]
    user_placeholders = ','.join(['%s'] * len(local_user_ids))
    email_placeholders = ','.join(['%s'] * len(local_emails))

    cursor.execute("DELETE FROM dispute_messages WHERE message_id LIKE 'LOCAL-%'")
    cursor.execute("DELETE FROM payment_submissions WHERE pop_id LIKE 'LOCAL-%'")
    cursor.execute("DELETE FROM notifications WHERE notification_id LIKE 'LOCAL-%'")
    cursor.execute("DELETE FROM feedback WHERE feedback_id LIKE 'LOCAL-%'")
    cursor.execute("DELETE FROM credit_invoices WHERE invoice_id LIKE 'LOCAL-%'")
    cursor.execute("DELETE FROM orders WHERE order_id LIKE 'LOCAL-%'")
    cursor.execute(f"DELETE FROM user_sessions WHERE user_id IN ({user_placeholders})", local_user_ids)
    cursor.execute(f"DELETE FROM users WHERE email IN ({email_placeholders})", local_emails)


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
    for user in USERS:
        cursor.execute(
            """INSERT INTO users
               (user_id, email, name, phone, credit_balance, role, accepted_terms, accepted_terms_at, picture, active_role, created_at, updated_at)
               VALUES (%s,%s,%s,%s,%s,%s,1,%s,%s,%s,%s,%s)""",
            (
                user['user_id'],
                user['email'],
                user['name'],
                user['phone'],
                user['credit_balance'],
                user['role'],
                accepted_at,
                None,
                user['role'],
                timestamp,
                timestamp,
            )
        )


def seed_orders(cursor, timestamp):
    customer_primary = get_seed_user('customer_primary')
    customer_secondary = get_seed_user('customer_secondary')
    admin = get_seed_user('admin')
    orders = [
        {
            'order_id': 'LOCAL-ORD-PENDING-01',
            'user_id': customer_primary['user_id'],
            'user_name': customer_primary['name'],
            'user_email': customer_primary['email'],
            'user_phone': customer_primary['phone'],
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
            'user_id': customer_primary['user_id'],
            'user_name': customer_primary['name'],
            'user_email': customer_primary['email'],
            'user_phone': customer_primary['phone'],
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
            'user_id': customer_secondary['user_id'],
            'user_name': customer_secondary['name'],
            'user_email': customer_secondary['email'],
            'user_phone': customer_secondary['phone'],
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
                admin['name'] if order['status'] == 'cancelled' else None,
                order['created_at'] if order['status'] == 'cancelled' else None,
                order['created_at'],
                order['created_at'],
            )
        )


def seed_invoices(cursor, timestamp):
    customer_primary = get_seed_user('customer_primary')
    customer_secondary = get_seed_user('customer_secondary')
    admin = get_seed_user('admin')
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
            customer_primary['user_id'],
            customer_primary['name'],
            customer_primary['email'],
            customer_primary['phone'],
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
            admin['name'],
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
            customer_secondary['user_id'],
            customer_secondary['name'],
            customer_secondary['email'],
            customer_secondary['phone'],
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
            admin['name'],
            'contact@myhappyhour.co.ke',
            'Nairobi',
            'Airtel Money',
            '0733878020',
            0,
            1,
        )
    )


def seed_payments_and_disputes(cursor, timestamp):
    customer_primary = get_seed_user('customer_primary')
    admin = get_seed_user('admin')
    cursor.execute(
        """INSERT INTO payment_submissions
           (pop_id, invoice_id, user_id, user_name, user_email, transaction_code,
            amount_paid, payment_method, payment_type, notes, status, submitted_at,
            admin_transaction_code, admin_amount, decline_reason, declined_at, declined_by, audit_trail)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            'LOCAL-POP-001',
            'LOCAL-INV-001',
            customer_primary['user_id'],
            customer_primary['name'],
            customer_primary['email'],
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
            admin['name'],
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
            customer_primary['user_id'],
            customer_primary['name'],
            'user',
            'The payment was full. Please recheck the finance ledger for Airtel reference QWE123LOCAL.',
            timestamp - timedelta(hours=2),
        )
    )


def seed_notifications(cursor, timestamp):
    customer_primary = get_seed_user('customer_primary')
    customer_secondary = get_seed_user('customer_secondary')
    admin = get_seed_user('admin')
    super_admin = get_seed_user('super_admin')
    notifications = [
        ('LOCAL-NOTIF-001', admin['user_id'], 'New Order Received', f"{customer_primary['name']} placed a pending local test order.", 'order', {'order_id': 'LOCAL-ORD-PENDING-01'}),
        ('LOCAL-NOTIF-002', super_admin['user_id'], 'Payment Needs Review', 'Local seeded POP failed verification and needs review.', 'payment', {'pop_id': 'LOCAL-POP-001'}),
        ('LOCAL-NOTIF-003', customer_primary['user_id'], 'Invoice Ready', 'Your seeded invoice LOCAL-INV-001 is ready for payment.', 'invoice', {'invoice_id': 'LOCAL-INV-001'}),
        ('LOCAL-NOTIF-004', customer_secondary['user_id'], 'Backlog Credit Added', 'A backlog credit invoice has been created for testing.', 'invoice', {'invoice_id': 'LOCAL-INV-002'}),
    ]

    for notification_id, user_id, title, message, notification_type, metadata in notifications:
        cursor.execute(
            """INSERT INTO notifications
               (notification_id, user_id, title, message, notification_type, `read`, created_at, created_by, metadata)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (notification_id, user_id, title, message, notification_type, 0, timestamp, 'seed_local_data', json.dumps(metadata))
        )


def seed_feedback(cursor, timestamp):
    customer_secondary = get_seed_user('customer_secondary')
    cursor.execute(
        """INSERT INTO feedback
           (feedback_id, user_id, user_name, user_email, subject, message, status, created_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            'LOCAL-FB-001',
            customer_secondary['user_id'],
            customer_secondary['name'],
            customer_secondary['email'],
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
    for user in USERS:
        print(f"  {user['role']}: {user['email']}")


if __name__ == '__main__':
    main()