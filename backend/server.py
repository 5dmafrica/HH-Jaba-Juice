from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import aiomysql
import json
import os
import logging
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import httpx
import secrets
import html
from urllib.parse import urlencode

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MySQL connection pool (initialized on startup)
pool = None

# Brevo setup
BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@yourdomain.com')
SENDER_NAME = os.environ.get('SENDER_NAME', 'HH Jaba')

# Google OAuth
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', '')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
ENABLE_DEV_AUTH = os.environ.get('ENABLE_DEV_AUTH', '0').strip().lower() in ('1', 'true', 'yes', 'on')
COOKIE_SECURE = os.environ.get('COOKIE_SECURE', '1' if FRONTEND_URL.startswith('https://') else '0').strip().lower() in ('1', 'true', 'yes', 'on')
COOKIE_SAMESITE = os.environ.get('COOKIE_SAMESITE', 'none' if COOKIE_SECURE else 'lax').strip().lower()

# Auth bootstrap configuration
DEFAULT_APPROVED_DOMAINS = [
    domain.strip().lower()
    for domain in os.environ.get('APPROVED_EMAIL_DOMAINS', '5dm.africa').split(',')
    if domain.strip()
]
BOOTSTRAP_SUPER_ADMIN_EMAIL = os.environ.get('SUPER_ADMIN_EMAIL', 'mavin@5dm.africa').strip().lower()
ROLE_ORDER = {
    'user': 0,
    'admin': 1,
    'super_admin': 2,
}

# Credit and Order Limits
MONTHLY_CREDIT_LIMIT = 30000  # KES 30,000 per customer
DAILY_ORDER_LIMIT = 10  # 10 bottles per day
WEEKLY_CREDIT_LIMIT = 10  # 10 bottles per week on credit
UNIT_PRICE = 500  # KES 500 per bottle

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== MODELS =====

class UserBase(BaseModel):
    user_id: str
    email: str
    name: str
    phone: Optional[str] = None
    credit_balance: float = 10000.0
    role: str = "user"
    accepted_terms: bool = False
    accepted_terms_at: Optional[datetime] = None
    picture: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class UserCreate(BaseModel):
    phone: str

class ProfileSetup(BaseModel):
    phone: str
    accept_terms: bool

class Product(BaseModel):
    product_id: str
    name: str
    description: str
    price: float
    stock: int
    active: bool = True
    color: str
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class OrderItem(BaseModel):
    product_name: str
    quantity: int
    price: float

class OrderCreate(BaseModel):
    items: List[OrderItem]
    payment_method: str  # 'credit' or 'mpesa'
    mpesa_code: Optional[str] = None

class Order(BaseModel):
    order_id: str
    user_id: str
    items: List[OrderItem]
    total_amount: float
    payment_method: str
    mpesa_code: Optional[str] = None
    status: str = "pending"
    verification_status: str = "pending"
    receipt_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class ManualInvoice(BaseModel):
    invoice_id: str
    user_id: Optional[str] = None
    customer_name: Optional[str] = None
    amount: float
    description: str
    payment_method: str
    mpesa_code: Optional[str] = None
    product_name: Optional[str] = None
    quantity: Optional[int] = None
    status: str = "pending"
    created_at: datetime

class ManualInvoiceCreate(BaseModel):
    user_id: Optional[str] = None
    customer_name: Optional[str] = None
    amount: float
    description: str
    payment_method: str
    mpesa_code: Optional[str] = None
    product_name: Optional[str] = None
    quantity: Optional[int] = None

class StockUpdate(BaseModel):
    stock: int
    manufacturing_date: Optional[str] = None
    batch_id: Optional[str] = None
    increment: bool = True  # If True, add to existing stock; if False, set absolute value

class OrderCancellation(BaseModel):
    reason: str

class FeedbackCreate(BaseModel):
    message: str
    subject: Optional[str] = None

class NotificationCreate(BaseModel):
    title: str
    message: str
    notification_type: str = "general"
    target_users: Optional[List[str]] = None

class ApprovedDomainCreate(BaseModel):
    domain: str

class UserRoleUpdate(BaseModel):
    role: str

class POPSubmission(BaseModel):
    invoice_id: str
    transaction_code: str
    amount_paid: float
    payment_method: str = "airtel_money"
    payment_type: str = "full"
    notes: Optional[str] = None

class PaymentVerification(BaseModel):
    status: str
    verified_amount: Optional[float] = None
    reason: Optional[str] = None

class TransactionMatch(BaseModel):
    admin_transaction_code: str
    admin_amount: float

class ForceApproval(BaseModel):
    reason: str

class DisputeMessage(BaseModel):
    message: str
    pop_id: str

class StartingCreditEntry(BaseModel):
    user_id: str
    amount: float
    description: str
    billing_period_start: Optional[str] = None
    billing_period_end: Optional[str] = None

# Backward-compatible alias used by older backlog-credit clients.
BacklogCreditEntry = StartingCreditEntry

class CreditInvoiceLineItem(BaseModel):
    flavor: str
    quantity: int
    unit_price: float = 500.0
    status: str = "unpaid"
    order_id: Optional[str] = None
    order_date: Optional[str] = None

class CreditInvoiceCreate(BaseModel):
    user_id: str
    billing_period_start: str
    billing_period_end: str
    line_items: List[CreditInvoiceLineItem]
    notes: Optional[str] = None
    payment_type: str = "credit"

class CreditInvoice(BaseModel):
    invoice_id: str
    user_id: str
    customer_name: str
    customer_email: str
    customer_phone: Optional[str] = None
    billing_period_start: str
    billing_period_end: str
    line_items: List[dict]
    subtotal: float
    total_amount: float
    status: str = "unpaid"
    notes: Optional[str] = None
    created_at: str
    created_by: str


# ===== DB HELPERS =====

def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

def _serialize(value) -> str:
    """Serialize Python object to JSON string for MySQL JSON columns."""
    return json.dumps(value, default=str)

def _parse_json_cols(row: dict) -> dict:
    """Parse JSON columns in a result row back to Python objects."""
    if not row:
        return row
    json_cols = {'items', 'line_items', 'audit_trail', 'metadata'}
    for col in json_cols:
        if col in row and isinstance(row[col], str):
            try:
                row[col] = json.loads(row[col])
            except Exception:
                pass
    # Convert datetime objects to ISO strings for JSON serialization
    for key, val in row.items():
        if isinstance(val, datetime):
            row[key] = val.isoformat()
    return row

def _parse_rows(rows: list) -> list:
    return [_parse_json_cols(dict(r)) for r in rows]

async def db_fetchone(sql: str, params=None) -> Optional[dict]:
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql, params or ())
            row = await cur.fetchone()
            return _parse_json_cols(dict(row)) if row else None

async def db_fetchall(sql: str, params=None) -> list:
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql, params or ())
            rows = await cur.fetchall()
            return _parse_rows(rows)

async def db_execute(sql: str, params=None) -> int:
    """Execute INSERT/UPDATE/DELETE. Returns affected row count."""
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params or ())
            await conn.commit()
            return cur.rowcount

async def db_count(sql: str, params=None) -> int:
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql, params or ())
            row = await cur.fetchone()
            return int(list(row.values())[0]) if row else 0

def _normalize_domain(value: str) -> str:
    return (value or '').strip().lower().lstrip('@')

def _get_email_domain(email: str) -> str:
    if '@' not in (email or ''):
        return ''
    return _normalize_domain(email.split('@', 1)[1])

def get_effective_role(user: Optional[dict]) -> str:
    if not user:
        return 'user'
    role = user.get('effective_role') or user.get('active_role') or user.get('role') or 'user'
    return role if role in ROLE_ORDER else 'user'

def has_effective_role(user: Optional[dict], *roles: str) -> bool:
    return get_effective_role(user) in roles

def is_actual_super_admin(user: Optional[dict]) -> bool:
    return bool(user and user.get('role') == 'super_admin')

async def get_privileged_users() -> list:
    return await db_fetchall(
        "SELECT * FROM users WHERE role IN ('admin','super_admin') ORDER BY created_at ASC"
    )

async def get_dev_auth_users() -> list:
    return await db_fetchall(
        """SELECT user_id, email, name, role
           FROM users
           WHERE email LIKE %s
           ORDER BY CASE role
               WHEN 'user' THEN 0
               WHEN 'admin' THEN 1
               WHEN 'super_admin' THEN 2
               ELSE 3
           END,
           created_at ASC,
           name ASC""",
        ('%@%',)
    )

async def is_email_domain_approved(email: str) -> bool:
    domain = _get_email_domain(email)
    if not domain:
        return False
    approved = await db_fetchone(
        "SELECT domain FROM approved_domains WHERE domain=%s AND is_active=1",
        (domain,)
    )
    return approved is not None

async def create_admin_audit_log(actor: dict, action: str, target_type: str, target_id: str, details: Optional[dict] = None):
    if not actor:
        return
    await db_execute(
        """INSERT INTO admin_audit_log
           (audit_id, actor_user_id, actor_email, action, target_type, target_id, details, created_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            f"AUD-{uuid.uuid4().hex[:10].upper()}",
            actor.get('user_id', ''),
            actor.get('email', ''),
            action,
            target_type,
            target_id,
            _serialize(details or {}),
            _now(),
        )
    )

async def ensure_management_tables():
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """CREATE TABLE IF NOT EXISTS approved_domains (
                       domain VARCHAR(191) PRIMARY KEY,
                       is_active TINYINT(1) DEFAULT 1,
                       added_by VARCHAR(255),
                       disabled_by VARCHAR(255),
                       created_at DATETIME NOT NULL,
                       updated_at DATETIME,
                       disabled_at DATETIME,
                       INDEX idx_active (is_active)
                   )"""
            )
            await cur.execute(
                """CREATE TABLE IF NOT EXISTS admin_audit_log (
                       audit_id VARCHAR(50) PRIMARY KEY,
                       actor_user_id VARCHAR(50) NOT NULL,
                       actor_email VARCHAR(191),
                       action VARCHAR(100) NOT NULL,
                       target_type VARCHAR(50) NOT NULL,
                       target_id VARCHAR(191) NOT NULL,
                       details JSON,
                       created_at DATETIME NOT NULL,
                       INDEX idx_actor (actor_user_id),
                       INDEX idx_action (action),
                       INDEX idx_target (target_type, target_id),
                       INDEX idx_created (created_at)
                   )"""
            )
            await conn.commit()

async def create_session_token(user_id: str) -> str:
    session_token = secrets.token_urlsafe(64)
    now = _now()
    expires_at = now + timedelta(days=7)
    await db_execute("DELETE FROM user_sessions WHERE user_id=%s", (user_id,))
    await db_execute(
        "INSERT INTO user_sessions (user_id, session_token, expires_at, created_at) VALUES (%s,%s,%s,%s)",
        (user_id, session_token, expires_at, now)
    )
    logger.info(f"Session created for user_id={user_id}")
    return session_token

def build_session_response(session_token: str, redirect_url: Optional[str] = None):
    response = RedirectResponse(url=redirect_url or f"{FRONTEND_URL}/auth/callback", status_code=302)
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
        max_age=7 * 24 * 60 * 60,
    )
    return response

async def seed_approved_domains():
    now = _now()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            for domain in DEFAULT_APPROVED_DOMAINS or ['5dm.africa']:
                await cur.execute(
                    """INSERT IGNORE INTO approved_domains
                       (domain, is_active, added_by, created_at, updated_at)
                       VALUES (%s,1,%s,%s,%s)""",
                    (_normalize_domain(domain), 'system', now, now)
                )
            await conn.commit()


# ===== AUTH HELPERS =====

async def get_session_token(request: Request) -> Optional[str]:
    """Extract session token from cookie or Authorization header."""
    session_token = request.cookies.get("session_token")
    if session_token:
        return session_token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    return None

async def get_current_user(request: Request) -> dict:
    """Get current authenticated user."""
    session_token = await get_session_token(request)
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = await db_fetchone(
        "SELECT * FROM user_sessions WHERE token_prefix=LEFT(%s,191)", (session_token,)
    )
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")

    expires_at = session.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if isinstance(expires_at, datetime) and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    user = await db_fetchone(
        "SELECT * FROM users WHERE user_id=%s", (session["user_id"],)
    )
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    active_role = user.get("role") or "user"
    if is_actual_super_admin(user):
        session_role = session.get("impersonated_role")
        stored_active_role = user.get("active_role")
        if session_role in ROLE_ORDER:
            active_role = session_role
        elif stored_active_role in ROLE_ORDER:
            active_role = stored_active_role

    user["active_role"] = active_role
    user["effective_role"] = active_role

    return user

async def get_admin_user(request: Request) -> dict:
    """Get current user and verify admin/super_admin role."""
    user = await get_current_user(request)
    if not has_effective_role(user, "admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

async def get_super_admin_user(request: Request) -> dict:
    """Get current user and verify actual super admin role."""
    user = await get_current_user(request)
    if not is_actual_super_admin(user):
        raise HTTPException(status_code=403, detail="Super admin access required")
    return user


# ===== EMAIL SERVICE =====

async def send_email(recipient_email: str, subject: str, html_content: str):
    """Send email using Brevo (Sendinblue) API."""
    if not BREVO_API_KEY:
        logger.warning("Brevo API key not configured, skipping email")
        return None

    payload = {
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "to": [{"email": recipient_email}],
        "subject": subject,
        "htmlContent": html_content
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                json=payload,
                headers={
                    "api-key": BREVO_API_KEY,
                    "Content-Type": "application/json"
                }
            )
        if response.status_code in (200, 201):
            logger.info(f"Email sent to {recipient_email}")
            return response.json()
        else:
            logger.error(f"Brevo error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return None


def _format_email_currency(amount) -> str:
    try:
        return f"KES {float(amount or 0):,.2f}"
    except (TypeError, ValueError):
        return f"KES {amount}"


def _format_email_date(value) -> str:
    if not value:
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%b %d, %Y")

    text = str(value)
    for candidate in (text.replace("Z", "+00:00"), text):
        try:
            return datetime.fromisoformat(candidate).strftime("%b %d, %Y")
        except ValueError:
            continue

    return text.split("T")[0]


def _build_email_shell(title: str, greeting_name: str, intro_html: str, details_html: str = "", closing_html: str = "") -> str:
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto;padding:20px;">
        <div style="background:#22c55e;padding:20px;text-align:center;">
            <h1 style="color:#000;margin:0;">HH Jaba</h1>
        </div>
        <div style="padding:24px;background:#f9f9f9;">
            <h2 style="color:#333;margin-top:0;">{title}</h2>
            <p>Hi {html.escape(greeting_name or 'Customer')},</p>
            {intro_html}
            {details_html}
            {closing_html}
        </div>
        <div style="padding:12px 10px;text-align:center;color:#666;font-size:12px;">
            <p style="margin:0;">Happy Hour Jaba - 5DM Africa, Nairobi</p>
            <p style="margin:6px 0 0 0;">contact@myhappyhour.co.ke</p>
        </div>
    </div>
    """


def _build_detail_grid(rows: List[tuple[str, str]]) -> str:
    if not rows:
        return ""

    details = "".join(
        f"""
        <tr>
            <td style='padding:10px 12px;border-bottom:1px solid #e5e7eb;color:#666;width:40%;'>{html.escape(label)}</td>
            <td style='padding:10px 12px;border-bottom:1px solid #e5e7eb;font-weight:600;'>{value}</td>
        </tr>
        """
        for label, value in rows
    )
    return f"""
    <div style="background:#fff;border:2px solid #000;margin:20px 0;">
        <table style="width:100%;border-collapse:collapse;">{details}</table>
    </div>
    """


def get_credit_invoice_html(invoice: dict) -> str:
    line_items = invoice.get("line_items", []) or []
    items_html = "".join(
        f"""
        <tr>
            <td style='padding:10px;border-bottom:1px solid #ddd;'>{html.escape(str(item.get('flavor', 'Item')))}</td>
            <td style='padding:10px;border-bottom:1px solid #ddd;text-align:center;'>{int(item.get('quantity', 0) or 0)}</td>
            <td style='padding:10px;border-bottom:1px solid #ddd;text-align:right;'>{_format_email_currency(item.get('unit_price', 0))}</td>
            <td style='padding:10px;border-bottom:1px solid #ddd;text-align:right;'>{_format_email_currency(item.get('line_total', 0))}</td>
            <td style='padding:10px;border-bottom:1px solid #ddd;text-align:center;'>{html.escape(str(item.get('status', 'unpaid')).upper())}</td>
        </tr>
        """
        for item in line_items
    )

    payment_method = invoice.get("payment_method") or "Airtel Money"
    payment_number = invoice.get("payment_number") or "0733878020"
    company_email = invoice.get("company_email") or "contact@myhappyhour.co.ke"
    billing_period = f"{_format_email_date(invoice.get('billing_period_start'))} - {_format_email_date(invoice.get('billing_period_end'))}"

    details_html = f"""
    <div style="background:#fff;border:2px solid #000;margin:20px 0;overflow:hidden;">
        <table style="width:100%;border-collapse:collapse;">
            <tr style="background:#22c55e;">
                <th style="padding:10px;text-align:left;">Flavor</th>
                <th style="padding:10px;text-align:center;">Qty</th>
                <th style="padding:10px;text-align:right;">Unit Price</th>
                <th style="padding:10px;text-align:right;">Amount</th>
                <th style="padding:10px;text-align:center;">Status</th>
            </tr>
            {items_html}
        </table>
    </div>
    """

    summary_html = _build_detail_grid([
        ("Invoice ID", html.escape(str(invoice.get("invoice_id", "-")))),
        ("Billing Period", html.escape(billing_period)),
        ("Invoice Status", html.escape(str(invoice.get("status", "unpaid")).upper())),
        ("Total Amount", _format_email_currency(invoice.get("total_amount", 0))),
        ("Payment Method", html.escape(str(payment_method))),
        ("Payment Number", html.escape(str(payment_number))),
    ])

    return _build_email_shell(
        "Invoice Ready",
        invoice.get("customer_name") or "Customer",
        f"""
        <p>Your HH Jaba invoice is ready for payment.</p>
        <p>Please use the details below when making your payment. If you have already paid, you can upload proof of payment from your invoices page.</p>
        """,
        details_html + summary_html,
        f"""
        <p><strong>Need help?</strong> Contact us via {html.escape(company_email)}.</p>
        """
    )


async def send_credit_invoice_email(invoice: dict, recipient_email: Optional[str] = None, subject_prefix: str = "Invoice Ready"):
    recipient = recipient_email or invoice.get("customer_email")
    if not recipient:
        logger.warning("Credit invoice %s has no recipient email; skipping invoice email", invoice.get("invoice_id"))
        return None

    subject = f"{subject_prefix} - HH Jaba {invoice.get('invoice_id', '')}".strip()
    return await send_email(recipient, subject, get_credit_invoice_html(invoice))


def get_transactional_update_html(recipient_name: str, title: str, intro_html: str, rows: Optional[List[tuple[str, str]]] = None, closing_html: str = "") -> str:
    return _build_email_shell(title, recipient_name, intro_html, _build_detail_grid(rows or []), closing_html)

def get_order_confirmation_html(order: dict, user: dict) -> str:
    """Generate order confirmation email HTML."""
    items_html = "".join([
        f"<tr><td style='padding:8px;border-bottom:1px solid #ddd;'>{item['product_name']}</td>"
        f"<td style='padding:8px;border-bottom:1px solid #ddd;text-align:center;'>{item['quantity']}</td>"
        f"<td style='padding:8px;border-bottom:1px solid #ddd;text-align:right;'>KES {item['price'] * item['quantity']:.2f}</td></tr>"
        for item in order['items']
    ])

    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
        <div style="background:#22c55e;padding:20px;text-align:center;">
            <h1 style="color:#000;margin:0;">HH Jaba</h1>
        </div>
        <div style="padding:20px;background:#f9f9f9;">
            <h2 style="color:#333;">Order Confirmed!</h2>
            <p>Hi {user.get('name', 'Customer')},</p>
            <p>Your order has been placed successfully.</p>
            <table style="width:100%;border-collapse:collapse;margin:20px 0;">
                <tr style="background:#22c55e;">
                    <th style="padding:10px;text-align:left;">Flavor</th>
                    <th style="padding:10px;text-align:center;">Qty</th>
                    <th style="padding:10px;text-align:right;">Amount</th>
                </tr>
                {items_html}
            </table>
            <p style="font-size:18px;font-weight:bold;">Total: KES {order['total_amount']:.2f}</p>
            <p>Payment Method: {order['payment_method'].upper()}</p>
            {f"<p>M-Pesa Code: {order['mpesa_code']}</p>" if order.get('mpesa_code') else ""}
            <p>Order ID: {order['order_id']}</p>
        </div>
        <div style="padding:10px;text-align:center;color:#666;font-size:12px;">
            <p>5DM Africa - Happy Hour Jaba</p>
        </div>
    </div>
    """


# ===== INITIALIZE PRODUCTS =====

async def initialize_products():
    """Initialize default products if none exist (idempotent via INSERT IGNORE)."""
    count = await db_count("SELECT COUNT(*) FROM products")
    if count >= 5:
        return
    if count == 0:
        now = _now()
        products = [
            ("prod_" + uuid.uuid4().hex[:12], "Happy Hour Jaba - Tamarind",  "Refreshing tamarind flavored beer",  500.0, 100, 1, "#8B4513", "https://images.unsplash.com/photo-1763178947953-ae2fdb2410f7?auto=format&fit=crop&w=600&q=80"),
            ("prod_" + uuid.uuid4().hex[:12], "Happy Hour Jaba - Watermelon", "Sweet watermelon flavored beer",     500.0, 100, 1, "#FF1493", "https://images.unsplash.com/photo-1769777134533-41f68b35df0e?auto=format&fit=crop&w=600&q=80"),
            ("prod_" + uuid.uuid4().hex[:12], "Happy Hour Jaba - Beetroot",   "Earthy beetroot flavored beer",      500.0, 100, 1, "#8B0000", "https://images.pexels.com/photos/5668199/pexels-photo-5668199.jpeg?auto=compress&cs=tinysrgb&h=650&w=940"),
            ("prod_" + uuid.uuid4().hex[:12], "Happy Hour Jaba - Pineapple",  "Tropical pineapple flavored beer",   500.0, 100, 1, "#FFD700", "https://images.pexels.com/photos/21576286/pexels-photo-21576286.jpeg?auto=compress&cs=tinysrgb&h=650&w=940"),
            ("prod_" + uuid.uuid4().hex[:12], "Happy Hour Jaba - Hibiscus",   "Floral hibiscus flavored beer",      500.0, 100, 1, "#DC143C", "https://images.unsplash.com/photo-1763178947953-ae2fdb2410f7?auto=format&fit=crop&w=600&q=80"),
        ]
        for p in products:
            await db_execute(
                """INSERT IGNORE INTO products
                   (product_id, name, description, price, stock, active, color, image_url, created_at, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (*p, now, now)
            )
        logger.info("Initialized 5 default products")


# ===== AUTH ROUTES =====

@api_router.get("/auth/google")
async def google_login():
    """Redirect user to Google OAuth consent screen."""
    if ENABLE_DEV_AUTH:
        return RedirectResponse(url=f"{FRONTEND_URL}/?error=dev_auth_enabled", status_code=302)

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return RedirectResponse(url=google_auth_url, status_code=302)


@api_router.get("/auth/google/callback")
async def google_callback(request: Request, code: str = None, error: str = None):
    """Handle Google OAuth callback, create session, redirect to frontend."""
    frontend_error_url = f"{FRONTEND_URL}/?error="

    if error:
        logger.warning(f"Google OAuth error: {error}")
        return RedirectResponse(url=frontend_error_url + "google_auth_denied", status_code=302)

    if not code:
        return RedirectResponse(url=frontend_error_url + "missing_code", status_code=302)

    try:
        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                }
            )
            if token_response.status_code != 200:
                logger.error(f"Token exchange failed: {token_response.text}")
                return RedirectResponse(url=frontend_error_url + "token_exchange_failed", status_code=302)
            tokens = token_response.json()

            userinfo_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {tokens['access_token']}"}
            )
            if userinfo_response.status_code != 200:
                logger.error(f"Userinfo failed: {userinfo_response.text}")
                return RedirectResponse(url=frontend_error_url + "userinfo_failed", status_code=302)
            userinfo = userinfo_response.json()

        email = userinfo.get("email", "").strip().lower()
        name = userinfo.get("name", "")
        picture = userinfo.get("picture", "")
        logger.info(f"Google OAuth: email={email}")

        if not await is_email_domain_approved(email):
            return RedirectResponse(url=frontend_error_url + "unauthorized_domain", status_code=302)

        now = _now()
        existing_user = await db_fetchone("SELECT * FROM users WHERE email=%s", (email,))

        if existing_user:
            await db_execute(
                "UPDATE users SET name=%s, picture=%s, updated_at=%s WHERE email=%s",
                (name, picture, now, email)
            )
            user_id = existing_user["user_id"]
        else:
            user_id = f"user_{uuid.uuid4().hex[:12]}"
            role = "super_admin" if email == BOOTSTRAP_SUPER_ADMIN_EMAIL else "user"
            await db_execute(
                """INSERT INTO users
                   (user_id, email, name, phone, credit_balance, role, accepted_terms, accepted_terms_at, picture, created_at, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (user_id, email, name, None, float(MONTHLY_CREDIT_LIMIT), role, 0, None, picture, now, now)
            )

        session_token = await create_session_token(user_id)
        return build_session_response(session_token)

    except Exception as e:
        logger.error(f"Google callback exception: {e}", exc_info=True)
        return RedirectResponse(url=frontend_error_url + "server_error", status_code=302)

@api_router.get("/dev/users")
async def get_dev_users():
    """List current dev-auth login candidates when ENABLE_DEV_AUTH is enabled."""
    if not ENABLE_DEV_AUTH:
        raise HTTPException(status_code=404, detail="Dev auth is disabled")

    users = await get_dev_auth_users()
    approved_users = [user for user in users if await is_email_domain_approved(user.get("email", ""))]

    return [
        {
            "user_id": user["user_id"],
            "email": user["email"],
            "name": user.get("name") or user["email"],
            "role": user.get("role", "user"),
        }
        for user in approved_users
    ]

@api_router.get("/dev/login")
async def dev_login(email: Optional[str] = None):
    """Create a local dev session without OAuth when ENABLE_DEV_AUTH is enabled."""
    if not ENABLE_DEV_AUTH:
        raise HTTPException(status_code=404, detail="Dev auth is disabled")

    normalized_email = (email or '').strip().lower()
    if not normalized_email:
        dev_users = await get_dev_auth_users()
        approved_users = [user for user in dev_users if await is_email_domain_approved(user.get("email", ""))]
        if not approved_users:
            raise HTTPException(status_code=404, detail="No dev users available. Seed local data first.")
        normalized_email = approved_users[0]["email"]

    if not await is_email_domain_approved(normalized_email):
        raise HTTPException(status_code=403, detail="Unauthorized domain")

    user = await db_fetchone("SELECT * FROM users WHERE email=%s", (normalized_email,))
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Seed local data first.")

    session_token = await create_session_token(user["user_id"])
    return build_session_response(session_token)

@api_router.get("/auth/me")
async def get_me(request: Request):
    """Get current authenticated user."""
    user = await get_current_user(request)
    return user

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user and clear session."""
    session_token = await get_session_token(request)
    if session_token:
        await db_execute("DELETE FROM user_sessions WHERE token_prefix=LEFT(%s,191)", (session_token,))
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out successfully"}


# ===== USER ROUTES =====

@api_router.post("/users/profile-setup")
async def setup_profile(profile: ProfileSetup, request: Request):
    """Complete user profile setup with phone and T&C acceptance."""
    user = await get_current_user(request)

    if not profile.accept_terms:
        raise HTTPException(status_code=400, detail="You must accept the terms and conditions")

    phone = profile.phone.strip()
    if phone.startswith("+254"):
        phone = "0" + phone[4:]
    elif phone.startswith("254"):
        phone = "0" + phone[3:]

    if not (phone.startswith("07") or phone.startswith("01")) or len(phone) != 10:
        raise HTTPException(status_code=400, detail="Invalid Kenyan phone number format")

    existing = await db_fetchone(
        "SELECT user_id FROM users WHERE phone=%s AND user_id != %s", (phone, user["user_id"])
    )
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    now = _now()
    await db_execute(
        "UPDATE users SET phone=%s, accepted_terms=1, accepted_terms_at=%s, updated_at=%s WHERE user_id=%s",
        (phone, now, now, user["user_id"])
    )

    return await db_fetchone("SELECT * FROM users WHERE user_id=%s", (user["user_id"],))

@api_router.get("/users/credit-balance")
async def get_credit_balance(request: Request):
    """Get user's current credit balance."""
    user = await get_current_user(request)
    return {"credit_balance": user.get("credit_balance", 0)}


# ===== PRODUCT ROUTES =====

@api_router.get("/products")
async def get_products():
    """Get all active products."""
    return await db_fetchall("SELECT * FROM products WHERE active=1 ORDER BY name")

@api_router.get("/products/all")
async def get_all_products(request: Request):
    """Get all products (admin only)."""
    await get_admin_user(request)
    return await db_fetchall("SELECT * FROM products ORDER BY name")


@api_router.get("/admin/stock-entries")
async def get_stock_entries(request: Request, product_id: Optional[str] = None, limit: int = 200):
    """Get stock addition history entries (admin only)."""
    await get_admin_user(request)

    safe_limit = max(1, min(limit, 1000))
    if product_id:
        return await db_fetchall(
            "SELECT * FROM stock_entries WHERE product_id=%s ORDER BY created_at DESC LIMIT %s",
            (product_id, safe_limit)
        )

    return await db_fetchall(
        "SELECT * FROM stock_entries ORDER BY created_at DESC LIMIT %s",
        (safe_limit,)
    )

@api_router.put("/products/{product_id}/stock")
async def update_stock(product_id: str, stock_update: StockUpdate, request: Request):
    """Update product stock (admin only)."""
    await get_admin_user(request)

    product = await db_fetchone("SELECT * FROM products WHERE product_id=%s", (product_id,))
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    now = _now()

    extra_fields = ""
    extra_params = []
    if stock_update.manufacturing_date:
        extra_fields += ", last_manufacturing_date=%s"
        extra_params.append(stock_update.manufacturing_date)
    if stock_update.batch_id:
        extra_fields += ", last_batch_id=%s"
        extra_params.append(stock_update.batch_id)

    if stock_update.increment:
        await db_execute(
            f"UPDATE products SET stock=stock+%s, updated_at=%s{extra_fields} WHERE product_id=%s",
            (stock_update.stock, now, *extra_params, product_id)
        )
        await db_execute(
            """INSERT INTO stock_entries
               (entry_id, product_id, product_name, quantity_added, manufacturing_date, batch_id, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (
                f"STK-{uuid.uuid4().hex[:8].upper()}",
                product_id,
                product.get("name"),
                stock_update.stock,
                stock_update.manufacturing_date,
                stock_update.batch_id,
                now
            )
        )
    else:
        await db_execute(
            f"UPDATE products SET stock=%s, updated_at=%s{extra_fields} WHERE product_id=%s",
            (stock_update.stock, now, *extra_params, product_id)
        )

    return await db_fetchone("SELECT * FROM products WHERE product_id=%s", (product_id,))

@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, request: Request):
    """Deactivate a product (admin only)."""
    await get_admin_user(request)

    rows = await db_execute(
        "UPDATE products SET active=0, stock=0, updated_at=%s WHERE product_id=%s",
        (_now(), product_id)
    )
    if rows == 0:
        raise HTTPException(status_code=404, detail="Product not found")

    return {"message": "Product deactivated"}


# ===== ORDER ROUTES =====

@api_router.post("/orders")
async def create_order(order_data: OrderCreate, request: Request):
    """Create a new order."""
    user = await get_current_user(request)

    if not user.get("accepted_terms") or not user.get("phone"):
        raise HTTPException(status_code=400, detail="Please complete your profile setup first")

    total_quantity = sum(item.quantity for item in order_data.items)
    total_amount = sum(item.quantity * item.price for item in order_data.items)

    if total_quantity == 0:
        raise HTTPException(status_code=400, detail="Order must have at least one item")

    if total_quantity > DAILY_ORDER_LIMIT:
        raise HTTPException(status_code=400, detail=f"Maximum {DAILY_ORDER_LIMIT} bottles per order")

    # Daily limit check
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_orders = await db_fetchall(
        "SELECT items FROM orders WHERE user_id=%s AND created_at>=%s AND status != 'cancelled'",
        (user["user_id"], today_start.replace(tzinfo=None))
    )
    today_bottles = sum(
        sum(item.get("quantity", 0) for item in order.get("items", []))
        for order in today_orders
    )

    if today_bottles + total_quantity > DAILY_ORDER_LIMIT and not has_effective_role(user, "super_admin"):
        raise HTTPException(
            status_code=400,
            detail=f"Daily limit of {DAILY_ORDER_LIMIT} bottles reached. You've ordered {today_bottles} today."
        )

    # Credit-specific limit checks
    if order_data.payment_method == "credit":
        if user.get("credit_balance", 0) < total_amount:
            raise HTTPException(status_code=400, detail="Insufficient credit balance")

        month_start = today_start.replace(day=1)
        month_credit_total = await db_fetchone(
            "SELECT COALESCE(SUM(total_amount),0) as total FROM orders WHERE user_id=%s AND payment_method='credit' AND created_at>=%s AND status != 'cancelled'",
            (user["user_id"], month_start.replace(tzinfo=None))
        )
        month_credit_used = float(month_credit_total.get("total", 0) or 0)

        if month_credit_used + total_amount > MONTHLY_CREDIT_LIMIT and not has_effective_role(user, "super_admin"):
            raise HTTPException(
                status_code=400,
                detail=f"Monthly credit limit of KES {MONTHLY_CREDIT_LIMIT:,} reached. You've used KES {month_credit_used:,} this month."
            )

        week_start = today_start - timedelta(days=today_start.weekday())
        week_orders = await db_fetchall(
            "SELECT items FROM orders WHERE user_id=%s AND payment_method='credit' AND created_at>=%s AND status != 'cancelled'",
            (user["user_id"], week_start.replace(tzinfo=None))
        )
        week_bottles = sum(
            sum(item.get("quantity", 0) for item in order.get("items", []))
            for order in week_orders
        )
        if week_bottles + total_quantity > WEEKLY_CREDIT_LIMIT:
            raise HTTPException(
                status_code=400,
                detail=f"Weekly credit limit of {WEEKLY_CREDIT_LIMIT} bottles reached. You've used {week_bottles} on credit this week."
            )

        await db_execute(
            "UPDATE users SET credit_balance=credit_balance-%s WHERE user_id=%s",
            (total_amount, user["user_id"])
        )

    if order_data.payment_method == "mpesa":
        if not order_data.mpesa_code or len(order_data.mpesa_code) < 5:
            raise HTTPException(status_code=400, detail="Valid M-Pesa transaction code required")

    order_id = f"ORD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"
    now = _now()
    items_json = _serialize([item.model_dump() for item in order_data.items])

    await db_execute(
        """INSERT INTO orders
           (order_id, user_id, user_name, user_email, user_phone, items, total_amount,
            payment_method, mpesa_code, status, verification_status, created_at, updated_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending','pending',%s,%s)""",
        (
            order_id,
            user["user_id"],
            user.get("name", ""),
            user.get("email", ""),
            user.get("phone", ""),
            items_json,
            total_amount,
            order_data.payment_method,
            order_data.mpesa_code if order_data.payment_method == "mpesa" else None,
            now, now
        )
    )

    # Decrement stock
    for item in order_data.items:
        await db_execute(
            "UPDATE products SET stock=stock-%s WHERE name=%s",
            (item.quantity, item.product_name)
        )

    order_doc = await db_fetchone("SELECT * FROM orders WHERE order_id=%s", (order_id,))

    await send_email(
        user.get("email", ""),
        f"Order Confirmed - HH Jaba #{order_id}",
        get_order_confirmation_html(order_doc, user)
    )

    admins = await get_privileged_users()
    items_summary = ", ".join([
        f"{item.product_name.replace('Happy Hour Jaba - ', '')} x{item.quantity}"
        for item in order_data.items
    ])
    for admin in admins:
        await db_execute(
            """INSERT INTO notifications
               (notification_id, user_id, title, message, notification_type, `read`, created_at, metadata)
               VALUES (%s,%s,%s,%s,'order',0,%s,%s)""",
            (
                f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
                admin["user_id"],
                "New Order Received",
                f"Order #{order_id} from {user.get('name', 'Customer')}: {items_summary}. Total: KES {total_amount:,}. Payment: {order_data.payment_method.upper()}",
                now,
                _serialize({
                    "order_id": order_id,
                    "customer_name": user.get("name"),
                    "total_amount": total_amount,
                    "payment_method": order_data.payment_method
                })
            )
        )

    return order_doc

@api_router.get("/orders")
async def get_user_orders(
    request: Request,
    payment_method: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
):
    """Get user's order history with filters."""
    user = await get_current_user(request)

    sql = "SELECT * FROM orders WHERE user_id=%s"
    params = [user["user_id"]]

    if payment_method and payment_method != "all":
        sql += " AND payment_method=%s"
        params.append(payment_method)
    if status and status != "all":
        sql += " AND status=%s"
        params.append(status)
    if from_date:
        sql += " AND created_at>=%s"
        params.append(from_date)
    if to_date:
        sql += " AND created_at<=%s"
        params.append(to_date)

    sql += " ORDER BY created_at DESC"
    return await db_fetchall(sql, params)

@api_router.get("/orders/{order_id}")
async def get_order(order_id: str, request: Request):
    """Get specific order details."""
    user = await get_current_user(request)

    order = await db_fetchone(
        "SELECT * FROM orders WHERE order_id=%s AND user_id=%s", (order_id, user["user_id"])
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# ===== ADMIN ORDER ROUTES =====

@api_router.get("/admin/pending-orders")
async def get_pending_orders(request: Request, payment_method: Optional[str] = None):
    """Get all pending orders (admin only)."""
    await get_admin_user(request)

    sql = "SELECT * FROM orders WHERE status='pending'"
    params = []
    if payment_method and payment_method != "all":
        sql += " AND payment_method=%s"
        params.append(payment_method)
    sql += " ORDER BY created_at DESC"
    return await db_fetchall(sql, params)

@api_router.post("/admin/orders/{order_id}/fulfill")
async def fulfill_order(order_id: str, request: Request):
    """Mark order as fulfilled (admin only)."""
    await get_admin_user(request)

    order = await db_fetchone("SELECT * FROM orders WHERE order_id=%s", (order_id,))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    await db_execute(
        "UPDATE orders SET status='fulfilled', verification_status='verified', updated_at=%s WHERE order_id=%s",
        (_now(), order_id)
    )

    user = await db_fetchone("SELECT * FROM users WHERE user_id=%s", (order["user_id"],))
    if user:
        await send_email(
            user.get("email", ""),
            f"Order Fulfilled - HH Jaba #{order_id}",
            f"""
            <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
                <div style="background:#22c55e;padding:20px;text-align:center;">
                    <h1 style="color:#000;margin:0;">HH Jaba</h1>
                </div>
                <div style="padding:20px;background:#f9f9f9;">
                    <h2 style="color:#333;">Order Fulfilled!</h2>
                    <p>Hi {user.get('name', 'Customer')},</p>
                    <p>Your order #{order_id} has been fulfilled. Thank you!</p>
                </div>
            </div>
            """
        )

    return await db_fetchone("SELECT * FROM orders WHERE order_id=%s", (order_id,))

@api_router.post("/admin/orders/{order_id}/cancel")
async def cancel_order(order_id: str, cancellation: OrderCancellation, request: Request):
    """Cancel an order with mandatory reason (admin only)."""
    admin = await get_admin_user(request)

    if not cancellation.reason or len(cancellation.reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Cancellation reason is required (minimum 5 characters)")

    order = await db_fetchone("SELECT * FROM orders WHERE order_id=%s", (order_id,))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Refund credit if credit payment
    if order.get("payment_method") == "credit":
        await db_execute(
            "UPDATE users SET credit_balance=credit_balance+%s WHERE user_id=%s",
            (order["total_amount"], order["user_id"])
        )

    # Restore stock
    for item in order.get("items", []):
        await db_execute(
            "UPDATE products SET stock=stock+%s WHERE name=%s",
            (item["quantity"], item["product_name"])
        )

    now = _now()
    await db_execute(
        """UPDATE orders SET status='cancelled', verification_status='rejected',
           cancellation_reason=%s, cancelled_by=%s, cancelled_at=%s, updated_at=%s
           WHERE order_id=%s""",
        (cancellation.reason, admin.get("name", admin.get("email")), now, now, order_id)
    )

    await db_execute(
        """INSERT INTO notifications
           (notification_id, user_id, title, message, notification_type, `read`, created_at)
           VALUES (%s,%s,%s,%s,'order',0,%s)""",
        (
            f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
            order["user_id"],
            "Order Cancelled",
            f"Your order #{order_id} has been cancelled. Reason: {cancellation.reason}",
            now
        )
    )

    user = await db_fetchone("SELECT * FROM users WHERE user_id=%s", (order["user_id"],))
    if user and user.get("email"):
        await send_email(
            user["email"],
            f"Order Cancelled - HH Jaba #{order_id}",
            get_transactional_update_html(
                user.get("name", "Customer"),
                "Order Cancelled",
                f"""
                <p>Your order <strong>#{html.escape(order_id)}</strong> has been cancelled.</p>
                <p>The reason provided by the admin team is shown below.</p>
                """,
                [
                    ("Order ID", html.escape(order_id)),
                    ("Payment Method", html.escape(str(order.get("payment_method", "")).upper())),
                    ("Order Total", _format_email_currency(order.get("total_amount", 0))),
                    ("Cancellation Reason", html.escape(cancellation.reason)),
                ],
                "<p>If you need help with a replacement order, reply to this email or contact support.</p>"
            )
        )

    return {"message": "Order cancelled", "reason": cancellation.reason}

@api_router.post("/admin/orders/{order_id}/reject")
async def reject_order(order_id: str, request: Request):
    """Reject an order (admin only)."""
    await get_admin_user(request)

    order = await db_fetchone("SELECT * FROM orders WHERE order_id=%s", (order_id,))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.get("payment_method") == "credit":
        await db_execute(
            "UPDATE users SET credit_balance=credit_balance+%s WHERE user_id=%s",
            (order["total_amount"], order["user_id"])
        )

    for item in order.get("items", []):
        await db_execute(
            "UPDATE products SET stock=stock+%s WHERE name=%s",
            (item["quantity"], item["product_name"])
        )

    await db_execute(
        "UPDATE orders SET status='cancelled', verification_status='rejected', updated_at=%s WHERE order_id=%s",
        (_now(), order_id)
    )

    now = _now()
    await db_execute(
        """INSERT INTO notifications
           (notification_id, user_id, title, message, notification_type, `read`, created_at)
           VALUES (%s,%s,%s,%s,'order',0,%s)""",
        (
            f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
            order["user_id"],
            "Order Rejected",
            f"Your order #{order_id} was rejected after review. Any held inventory and credit have been released.",
            now
        )
    )

    user = await db_fetchone("SELECT * FROM users WHERE user_id=%s", (order["user_id"],))
    if user and user.get("email"):
        await send_email(
            user["email"],
            f"Order Rejected - HH Jaba #{order_id}",
            get_transactional_update_html(
                user.get("name", "Customer"),
                "Order Rejected",
                f"""
                <p>Your order <strong>#{html.escape(order_id)}</strong> was rejected after review.</p>
                <p>Any reserved credit or stock has been released back to your account.</p>
                """,
                [
                    ("Order ID", html.escape(order_id)),
                    ("Payment Method", html.escape(str(order.get("payment_method", "")).upper())),
                    ("Order Total", _format_email_currency(order.get("total_amount", 0))),
                ],
                "<p>Please submit a new order if you still need stock, or contact support if this looks incorrect.</p>"
            )
        )

    return {"message": "Order rejected and refunded"}


# ===== RECONCILIATION & ADMIN USER ROUTES =====

@api_router.get("/admin/reconciliation")
async def get_reconciliation(request: Request, search: Optional[str] = None):
    """Get users with outstanding credit balances (admin only)."""
    await get_admin_user(request)

    sql = "SELECT * FROM users WHERE credit_balance < %s"
    params = [MONTHLY_CREDIT_LIMIT]
    if search:
        sql += " AND (name LIKE %s OR email LIKE %s OR phone LIKE %s)"
        like = f"%{search}%"
        params += [like, like, like]

    users = await db_fetchall(sql, params)

    result = []
    for user in users:
        outstanding = MONTHLY_CREDIT_LIMIT - float(user.get("credit_balance", MONTHLY_CREDIT_LIMIT))
        if outstanding > 0:
            orders = await db_fetchall(
                "SELECT * FROM orders WHERE user_id=%s AND payment_method='credit' AND status != 'cancelled' ORDER BY created_at DESC",
                (user["user_id"],)
            )
            total_pending = sum(float(o.get("total_amount", 0)) for o in orders if o.get("status") == "pending")
            result.append({
                "user": user,
                "outstanding_balance": outstanding,
                "total_pending": total_pending,
                "total_owed": outstanding,
                "orders": orders,
                "order_count": len(orders)
            })

    return result

@api_router.get("/admin/defaulters")
async def get_defaulters(request: Request, search: Optional[str] = None):
    """Get monthly defaulters (admin only)."""
    await get_admin_user(request)

    sql = "SELECT * FROM users WHERE credit_balance < %s"
    params = [MONTHLY_CREDIT_LIMIT]
    if search:
        sql += " AND (name LIKE %s OR email LIKE %s OR phone LIKE %s)"
        like = f"%{search}%"
        params += [like, like, like]

    users = await db_fetchall(sql, params)

    result = []
    for user in users:
        outstanding = MONTHLY_CREDIT_LIMIT - float(user.get("credit_balance", MONTHLY_CREDIT_LIMIT))
        if outstanding > 0:
            orders = await db_fetchall(
                "SELECT * FROM orders WHERE user_id=%s AND payment_method='credit' AND status != 'cancelled' ORDER BY created_at DESC",
                (user["user_id"],)
            )
            result.append({
                "user": user,
                "outstanding_balance": outstanding,
                "total_due": outstanding,
                "orders": orders
            })

    return result

@api_router.get("/admin/users")
async def get_all_users(request: Request):
    """Get all users (admin only)."""
    await get_admin_user(request)
    return await db_fetchall("SELECT * FROM users ORDER BY created_at DESC")

@api_router.get("/admin/domains")
async def get_approved_domains(request: Request):
    """Get approved sign-in domains (super admin only)."""
    await get_super_admin_user(request)
    return await db_fetchall(
        "SELECT domain, is_active, added_by, disabled_by, created_at, updated_at, disabled_at FROM approved_domains ORDER BY domain ASC"
    )

@api_router.post("/admin/domains")
async def upsert_approved_domain(domain_data: ApprovedDomainCreate, request: Request):
    """Add or reactivate an approved sign-in domain (super admin only)."""
    admin = await get_super_admin_user(request)
    domain = _normalize_domain(domain_data.domain)
    if not domain or '.' not in domain:
        raise HTTPException(status_code=400, detail="Valid domain required")

    now = _now()
    actor = admin.get("name") or admin.get("email") or "super_admin"
    existing = await db_fetchone("SELECT * FROM approved_domains WHERE domain=%s", (domain,))

    if existing:
        await db_execute(
            """UPDATE approved_domains
               SET is_active=1, added_by=%s, disabled_by=NULL, disabled_at=NULL, updated_at=%s
               WHERE domain=%s""",
            (actor, now, domain)
        )
        action = "domain_reactivated" if not existing.get("is_active") else "domain_updated"
    else:
        await db_execute(
            """INSERT INTO approved_domains
               (domain, is_active, added_by, created_at, updated_at)
               VALUES (%s,1,%s,%s,%s)""",
            (domain, actor, now, now)
        )
        action = "domain_added"

    await create_admin_audit_log(
        admin,
        action,
        "approved_domain",
        domain,
        {"domain": domain, "active": True}
    )
    return await db_fetchone(
        "SELECT domain, is_active, added_by, disabled_by, created_at, updated_at, disabled_at FROM approved_domains WHERE domain=%s",
        (domain,)
    )

@api_router.delete("/admin/domains/{domain}")
async def disable_approved_domain(domain: str, request: Request):
    """Disable an approved sign-in domain (super admin only)."""
    admin = await get_super_admin_user(request)
    normalized_domain = _normalize_domain(domain)
    existing = await db_fetchone("SELECT * FROM approved_domains WHERE domain=%s", (normalized_domain,))
    if not existing:
        raise HTTPException(status_code=404, detail="Domain not found")

    if existing.get("is_active"):
        active_count = await db_count("SELECT COUNT(*) FROM approved_domains WHERE is_active=1")
        if active_count <= 1:
            raise HTTPException(status_code=400, detail="At least one approved domain must remain active")

    now = _now()
    actor = admin.get("name") or admin.get("email") or "super_admin"
    await db_execute(
        """UPDATE approved_domains
           SET is_active=0, disabled_by=%s, disabled_at=%s, updated_at=%s
           WHERE domain=%s""",
        (actor, now, now, normalized_domain)
    )
    await create_admin_audit_log(
        admin,
        "domain_disabled",
        "approved_domain",
        normalized_domain,
        {"domain": normalized_domain, "active": False}
    )
    return {"message": f"Domain {normalized_domain} disabled"}

@api_router.put("/admin/users/{user_id}/role")
async def update_user_role(user_id: str, role_update: UserRoleUpdate, request: Request):
    """Promote or demote a user role (super admin only)."""
    admin = await get_super_admin_user(request)
    new_role = (role_update.role or '').strip().lower()
    if new_role not in ROLE_ORDER:
        raise HTTPException(status_code=400, detail="Invalid role")
    if admin["user_id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    target_user = await db_fetchone("SELECT * FROM users WHERE user_id=%s", (user_id,))
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    previous_role = target_user.get("role", "user")
    if previous_role == new_role:
        return target_user

    if previous_role == "super_admin" and new_role != "super_admin":
        super_admin_count = await db_count("SELECT COUNT(*) FROM users WHERE role='super_admin'")
        if super_admin_count <= 1:
            raise HTTPException(status_code=400, detail="At least one super admin must remain assigned")

    now = _now()
    await db_execute(
        "UPDATE users SET role=%s, active_role=%s, updated_at=%s WHERE user_id=%s",
        (new_role, new_role, now, user_id)
    )
    await db_execute(
        "UPDATE user_sessions SET impersonated_role=NULL WHERE user_id=%s",
        (user_id,)
    )
    await create_admin_audit_log(
        admin,
        "user_role_updated",
        "user",
        user_id,
        {
            "email": target_user.get("email"),
            "previous_role": previous_role,
            "new_role": new_role,
        }
    )
    return await db_fetchone("SELECT * FROM users WHERE user_id=%s", (user_id,))

@api_router.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, request: Request):
    """Delete a user (admin only)."""
    admin = await get_admin_user(request)

    if admin["user_id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    user = await db_fetchone("SELECT * FROM users WHERE user_id=%s", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get("role") in ("admin", "super_admin"):
        raise HTTPException(status_code=400, detail="Cannot delete elevated users")

    await db_execute("DELETE FROM user_sessions WHERE user_id=%s", (user_id,))
    await db_execute("DELETE FROM orders WHERE user_id=%s", (user_id,))
    await db_execute("DELETE FROM notifications WHERE user_id=%s", (user_id,))
    await db_execute("DELETE FROM credit_invoices WHERE user_id=%s", (user_id,))
    await db_execute("DELETE FROM users WHERE user_id=%s", (user_id,))

    return {"message": f"User {user.get('name')} deleted successfully"}

@api_router.get("/admin/users/{user_id}/reconciliation-report")
async def get_user_reconciliation_report(user_id: str, request: Request, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Get detailed reconciliation report for a specific user (admin only)."""
    await get_admin_user(request)

    user = await db_fetchone("SELECT * FROM users WHERE user_id=%s", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sql = "SELECT * FROM orders WHERE user_id=%s AND payment_method='credit' AND status != 'cancelled'"
    params = [user_id]
    if start_date:
        sql += " AND created_at>=%s"
        params.append(start_date)
    if end_date:
        sql += " AND created_at<=%s"
        params.append(end_date + "T23:59:59")
    sql += " ORDER BY created_at DESC"

    orders = await db_fetchall(sql, params)

    order_breakdown = []
    total_amount = 0
    for order in orders:
        for item in order.get("items", []):
            cost = item.get("quantity", 0) * item.get("price", UNIT_PRICE)
            order_breakdown.append({
                "order_id": order.get("order_id"),
                "timestamp": order.get("created_at"),
                "flavor": item.get("product_name", "").replace("Happy Hour Jaba - ", ""),
                "quantity": item.get("quantity", 0),
                "unit_price": item.get("price", UNIT_PRICE),
                "cost": cost,
                "status": order.get("status")
            })
            total_amount += cost

    return {
        "user": user,
        "period": {"start": start_date or "All time", "end": end_date or "Present"},
        "order_breakdown": order_breakdown,
        "total_amount": total_amount,
        "outstanding_balance": MONTHLY_CREDIT_LIMIT - float(user.get("credit_balance", MONTHLY_CREDIT_LIMIT)),
        "generated_at": _now().isoformat()
    }

@api_router.post("/admin/users/{user_id}/send-reconciliation")
async def send_reconciliation_report(user_id: str, request: Request):
    """Send reconciliation report notification to user (admin only)."""
    admin = await get_admin_user(request)

    body = await request.json()
    start_date = body.get("start_date")
    end_date = body.get("end_date")

    user = await db_fetchone("SELECT * FROM users WHERE user_id=%s", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    outstanding = MONTHLY_CREDIT_LIMIT - float(user.get("credit_balance", MONTHLY_CREDIT_LIMIT))
    period_text = f"{start_date} to {end_date}" if start_date and end_date else "current period"
    now = _now()

    await db_execute(
        """INSERT INTO notifications
           (notification_id, user_id, title, message, notification_type, `read`, created_at, metadata)
           VALUES (%s,%s,%s,%s,'invoice',0,%s,%s)""",
        (
            f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
            user_id,
            "Reconciliation Report",
            f"Your credit reconciliation report for {period_text} has been shared. Outstanding balance: KES {outstanding:,}. Please clear your balance before the new cycle begins.",
            now,
            _serialize({"start_date": start_date, "end_date": end_date, "outstanding": outstanding})
        )
    )

    if user.get("email"):
        await send_email(
            user["email"],
            "Reconciliation Report - HH Jaba",
            f"""
            <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
                <div style="background:#22c55e;padding:20px;text-align:center;">
                    <h1 style="color:#000;margin:0;">HH Jaba</h1>
                </div>
                <div style="padding:20px;background:#f9f9f9;">
                    <h2 style="color:#333;">Reconciliation Report</h2>
                    <p>Hi {user.get('name', 'Customer')},</p>
                    <p>Your credit reconciliation report for <strong>{period_text}</strong> has been generated.</p>
                    <div style="background:#fff;padding:15px;border:2px solid #000;margin:20px 0;">
                        <p style="margin:0;font-size:14px;">Outstanding Balance:</p>
                        <p style="margin:5px 0 0 0;font-size:24px;font-weight:bold;color:#dc2626;">KES {outstanding:,}</p>
                    </div>
                    <p><strong>Important:</strong> Please clear your balance before the new cycle begins (No Carry-Forward policy).</p>
                    <p style="margin-top:20px;">Payment Details:</p>
                    <p><strong>Airtel Money:</strong> 0733878020</p>
                </div>
                <div style="padding:10px;text-align:center;color:#666;font-size:12px;">
                    <p>Happy Hour Jaba - 5DM Africa, Nairobi</p>
                    <p>contact@myhappyhour.co.ke</p>
                </div>
            </div>
            """
        )

    return {"message": f"Reconciliation report sent to {user.get('name')}"}


# ===== MANUAL INVOICE ROUTES =====

@api_router.post("/admin/manual-invoice")
async def create_manual_invoice(invoice: ManualInvoiceCreate, request: Request):
    """Create a manual invoice (admin only)."""
    await get_admin_user(request)

    invoice_id = f"INV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"
    now = _now()

    await db_execute(
        """INSERT INTO manual_invoices
           (invoice_id, user_id, customer_name, amount, description, payment_method, mpesa_code, product_name, quantity, status, created_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending',%s)""",
        (invoice_id, invoice.user_id, invoice.customer_name, invoice.amount,
         invoice.description, invoice.payment_method, invoice.mpesa_code,
         invoice.product_name, invoice.quantity, now)
    )

    return await db_fetchone("SELECT * FROM manual_invoices WHERE invoice_id=%s", (invoice_id,))

@api_router.get("/admin/manual-invoices")
async def get_manual_invoices(request: Request):
    """Get all manual invoices (admin only)."""
    await get_admin_user(request)
    return await db_fetchall("SELECT * FROM manual_invoices ORDER BY created_at DESC")

@api_router.post("/admin/manual-invoices/{invoice_id}/verify")
async def verify_manual_invoice(invoice_id: str, request: Request):
    """Verify a manual invoice (admin only)."""
    await get_admin_user(request)

    rows = await db_execute(
        "UPDATE manual_invoices SET status='verified' WHERE invoice_id=%s", (invoice_id,)
    )
    if rows == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"message": "Invoice verified"}

@api_router.post("/admin/manual-invoices/{invoice_id}/reject")
async def reject_manual_invoice(invoice_id: str, request: Request):
    """Reject a manual invoice (admin only)."""
    await get_admin_user(request)

    rows = await db_execute(
        "UPDATE manual_invoices SET status='rejected' WHERE invoice_id=%s", (invoice_id,)
    )
    if rows == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"message": "Invoice rejected"}


# ===== CREDIT INVOICE ROUTES =====

@api_router.post("/admin/credit-invoices")
async def create_credit_invoice(invoice_data: CreditInvoiceCreate, request: Request):
    """Create a credit purchase invoice (admin only)."""
    admin = await get_admin_user(request)

    user = await db_fetchone("SELECT * FROM users WHERE user_id=%s", (invoice_data.user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    date_str = datetime.now(timezone.utc).strftime('%Y%m%d')
    invoice_id = f"HHJ-INV-{date_str}-{uuid.uuid4().hex[:5].upper()}"

    is_cash = invoice_data.payment_type == "cash"
    default_item_status = "paid" if is_cash else "unpaid"

    processed_items = []
    subtotal = 0.0
    for item in invoice_data.line_items:
        line_total = item.quantity * item.unit_price
        processed_items.append({
            "flavor": item.flavor,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "line_total": line_total,
            "status": default_item_status if is_cash else item.status
        })
        subtotal += line_total

    now = _now()
    await db_execute(
        """INSERT INTO credit_invoices
           (invoice_id, user_id, customer_name, customer_email, customer_phone,
            billing_period_start, billing_period_end, line_items, subtotal, total_amount,
            status, payment_type, notes, created_at, created_by,
            company_email, payment_method, payment_number)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            invoice_id, invoice_data.user_id,
            user.get("name", ""), user.get("email", ""), user.get("phone", ""),
            invoice_data.billing_period_start, invoice_data.billing_period_end,
            _serialize(processed_items), subtotal, subtotal,
            "paid" if is_cash else "unpaid", invoice_data.payment_type,
            invoice_data.notes, now,
            admin.get("name", admin.get("email", "Admin")),
            "contact@myhappyhour.co.ke", "Airtel Money", "0733878020"
        )
    )

    created_invoice = await db_fetchone("SELECT * FROM credit_invoices WHERE invoice_id=%s", (invoice_id,))

    await db_execute(
        """INSERT INTO notifications
           (notification_id, user_id, title, message, notification_type, `read`, created_at, metadata)
           VALUES (%s,%s,%s,%s,'invoice',0,%s,%s)""",
        (
            f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
            invoice_data.user_id,
            "Invoice Ready",
            f"Invoice {invoice_id} has been issued for {_format_email_currency(subtotal)}.",
            now,
            _serialize({"invoice_id": invoice_id, "total_amount": subtotal, "status": created_invoice.get("status", "unpaid")})
        )
    )

    email_sent = bool(await send_credit_invoice_email(created_invoice))
    created_invoice["email_sent"] = email_sent
    return created_invoice

@api_router.get("/admin/credit-invoices")
async def get_credit_invoices(request: Request, user_id: Optional[str] = None):
    """Get all credit invoices (admin only)."""
    await get_admin_user(request)

    if user_id:
        return await db_fetchall(
            "SELECT * FROM credit_invoices WHERE user_id=%s ORDER BY created_at DESC", (user_id,)
        )
    return await db_fetchall("SELECT * FROM credit_invoices ORDER BY created_at DESC")

@api_router.get("/admin/credit-invoices/{invoice_id}")
async def get_credit_invoice(invoice_id: str, request: Request):
    """Get a specific credit invoice (admin only)."""
    await get_admin_user(request)

    invoice = await db_fetchone("SELECT * FROM credit_invoices WHERE invoice_id=%s", (invoice_id,))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@api_router.post("/admin/credit-invoices/{invoice_id}/send-email")
async def send_credit_invoice_email_admin(invoice_id: str, request: Request):
    """Send or resend a credit invoice email (admin only)."""
    await get_admin_user(request)

    invoice = await db_fetchone("SELECT * FROM credit_invoices WHERE invoice_id=%s", (invoice_id,))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    email_response = await send_credit_invoice_email(invoice, subject_prefix="Invoice Resent")
    if not email_response:
        raise HTTPException(status_code=502, detail="Failed to send invoice email")

    return {
        "message": f"Invoice sent to {invoice.get('customer_email')}",
        "invoice_id": invoice_id,
        "recipient": invoice.get("customer_email")
    }

@api_router.put("/admin/credit-invoices/{invoice_id}/status")
async def update_credit_invoice_status(invoice_id: str, request: Request):
    """Update credit invoice status (admin only)."""
    await get_admin_user(request)

    invoice = await db_fetchone("SELECT * FROM credit_invoices WHERE invoice_id=%s", (invoice_id,))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    body = await request.json()
    new_status = body.get("status", "unpaid")

    if new_status not in ["paid", "partial", "unpaid"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    prev_status = invoice.get("status")

    rows = await db_execute(
        "UPDATE credit_invoices SET status=%s WHERE invoice_id=%s", (new_status, invoice_id)
    )
    if rows == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if prev_status != new_status:
        await db_execute(
            "INSERT INTO notifications (notification_id, user_id, title, message, notification_type, `read`, created_at) VALUES (%s,%s,%s,%s,'invoice',0,%s)",
            (
                f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
                invoice.get("user_id"),
                "Invoice Status Updated",
                f"Invoice {invoice_id} status changed from {prev_status.upper()} to {new_status.upper()}.",
                _now()
            )
        )

    return {"message": f"Invoice status updated to {new_status}"}

@api_router.put("/admin/credit-invoices/{invoice_id}/line-item/{item_index}/status")
async def update_line_item_status(invoice_id: str, item_index: int, request: Request):
    """Update individual line item status (admin only)."""
    await get_admin_user(request)

    body = await request.json()
    new_status = body.get("status", "unpaid")

    if new_status not in ["paid", "unpaid"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    invoice = await db_fetchone("SELECT * FROM credit_invoices WHERE invoice_id=%s", (invoice_id,))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    line_items = invoice.get("line_items", [])
    if item_index < 0 or item_index >= len(line_items):
        raise HTTPException(status_code=400, detail="Invalid line item index")

    line_items[item_index]["status"] = new_status

    all_paid = all(item.get("status") == "paid" for item in line_items)
    any_paid = any(item.get("status") == "paid" for item in line_items)
    overall_status = "paid" if all_paid else ("partial" if any_paid else "unpaid")

    await db_execute(
        "UPDATE credit_invoices SET line_items=%s, status=%s WHERE invoice_id=%s",
        (_serialize(line_items), overall_status, invoice_id)
    )

    return await db_fetchone("SELECT * FROM credit_invoices WHERE invoice_id=%s", (invoice_id,))

@api_router.delete("/admin/credit-invoices/{invoice_id}")
async def delete_credit_invoice(invoice_id: str, request: Request):
    """Delete a credit invoice (admin only)."""
    await get_admin_user(request)

    rows = await db_execute("DELETE FROM credit_invoices WHERE invoice_id=%s", (invoice_id,))
    if rows == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"message": "Invoice deleted"}

@api_router.get("/admin/user-credit-history/{user_id}")
async def get_user_credit_history(user_id: str, request: Request, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Get user's credit purchase history (admin only)."""
    await get_admin_user(request)

    sql = "SELECT * FROM orders WHERE user_id=%s AND payment_method='credit'"
    params = [user_id]
    if start_date:
        sql += " AND created_at>=%s"
        params.append(start_date)
    if end_date:
        sql += " AND created_at<=%s"
        params.append(end_date)
    sql += " ORDER BY created_at DESC"

    orders = await db_fetchall(sql, params)

    flavor_totals = {}
    for order in orders:
        for item in order.get("items", []):
            flavor = item.get("product_name", "").replace("Happy Hour Jaba - ", "")
            qty = item.get("quantity", 0)
            flavor_totals[flavor] = flavor_totals.get(flavor, 0) + qty

    return {
        "orders": orders,
        "flavor_summary": flavor_totals,
        "total_orders": len(orders),
        "total_amount": sum(float(o.get("total_amount", 0)) for o in orders)
    }


# ===== AUTO INVOICE GENERATION =====

@api_router.post("/admin/auto-generate-invoice/{user_id}")
async def auto_generate_invoice(user_id: str, request: Request):
    """Automatically generate credit invoice from order history (admin only)."""
    admin = await get_admin_user(request)

    body = await request.json()
    start_date = body.get("start_date")
    end_date = body.get("end_date")

    if not start_date or not end_date:
        raise HTTPException(status_code=400, detail="Start and end dates are required")

    user = await db_fetchone("SELECT * FROM users WHERE user_id=%s", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    orders = await db_fetchall(
        """SELECT * FROM orders WHERE user_id=%s AND payment_method='credit'
           AND status != 'cancelled' AND created_at>=%s AND created_at<=%s
           ORDER BY created_at ASC""",
        (user_id, start_date, end_date)
    )

    if not orders:
        raise HTTPException(status_code=404, detail="No credit orders found in the specified date range")

    line_items = []
    for order in orders:
        for item in order.get("items", []):
            flavor = item.get("product_name", "").replace("Happy Hour Jaba - ", "")
            qty = item.get("quantity", 0)
            price = item.get("price", UNIT_PRICE)
            line_items.append({
                "flavor": flavor,
                "quantity": qty,
                "unit_price": price,
                "line_total": qty * price,
                "status": "unpaid",
                "order_id": order.get("order_id"),
                "order_date": order.get("created_at")
            })

    date_str = datetime.now(timezone.utc).strftime('%Y%m%d')
    invoice_id = f"HHJ-INV-{date_str}-{uuid.uuid4().hex[:5].upper()}"
    total_amount = sum(item["line_total"] for item in line_items)
    now = _now()

    await db_execute(
        """INSERT INTO credit_invoices
           (invoice_id, user_id, customer_name, customer_email, customer_phone,
            billing_period_start, billing_period_end, line_items, subtotal, total_amount,
            status, notes, created_at, created_by, company_email, company_location,
            payment_method, payment_number, auto_generated)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'unpaid',%s,%s,%s,%s,%s,%s,%s,1)""",
        (
            invoice_id, user_id,
            user.get("name", ""), user.get("email", ""), user.get("phone", ""),
            start_date, end_date,
            _serialize(line_items), total_amount, total_amount,
            f"Auto-generated from {len(orders)} orders",
            now, admin.get("name", admin.get("email", "Admin")),
            "contact@myhappyhour.co.ke", "Nairobi",
            "Airtel Money", "0733878020"
        )
    )

    await db_execute(
        """INSERT INTO notifications
           (notification_id, user_id, title, message, notification_type, `read`, created_at, metadata)
           VALUES (%s,%s,%s,%s,'invoice',0,%s,%s)""",
        (
            f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
            user_id,
            "Invoice Ready",
            f"Invoice {invoice_id} has been auto-generated for {_format_email_currency(total_amount)}.",
            now,
            _serialize({"invoice_id": invoice_id, "total_amount": total_amount, "auto_generated": True})
        )
    )

    created_invoice = await db_fetchone("SELECT * FROM credit_invoices WHERE invoice_id=%s", (invoice_id,))
    created_invoice["email_sent"] = bool(await send_credit_invoice_email(created_invoice, subject_prefix="Invoice Ready"))
    return created_invoice


# ===== FEEDBACK & NOTIFICATIONS =====

@api_router.post("/feedback")
async def submit_feedback(feedback: FeedbackCreate, request: Request):
    """Submit feedback to admin."""
    user = await get_current_user(request)

    feedback_id = f"FB-{uuid.uuid4().hex[:8].upper()}"
    await db_execute(
        """INSERT INTO feedback
           (feedback_id, user_id, user_name, user_email, subject, message, status, created_at)
           VALUES (%s,%s,%s,%s,%s,%s,'new',%s)""",
        (feedback_id, user["user_id"], user.get("name", ""), user.get("email", ""),
         feedback.subject or "General Feedback", feedback.message, _now())
    )

    return {"message": "Feedback submitted successfully", "feedback_id": feedback_id}

@api_router.get("/admin/feedback")
async def get_all_feedback(request: Request):
    """Get all feedback (admin only)."""
    await get_admin_user(request)
    return await db_fetchall("SELECT * FROM feedback ORDER BY created_at DESC")

@api_router.post("/admin/notifications")
async def create_notification(notification: NotificationCreate, request: Request):
    """Create notification/push offer (admin only)."""
    admin = await get_admin_user(request)

    notification_id = f"NOTIF-{uuid.uuid4().hex[:8].upper()}"
    now = _now()

    recipients = []

    if notification.target_users:
        for uid in notification.target_users:
            recipient = await db_fetchone("SELECT user_id, email, name FROM users WHERE user_id=%s", (uid,))
            if recipient:
                recipients.append(recipient)
            await db_execute(
                """INSERT INTO notifications
                   (notification_id, user_id, title, message, notification_type, `read`, created_at, created_by)
                   VALUES (%s,%s,%s,%s,%s,0,%s,%s)""",
                (notification_id, uid, notification.title, notification.message,
                 notification.notification_type, now, admin.get("name", admin.get("email")))
            )
    else:
        recipients = await db_fetchall("SELECT user_id, email, name FROM users WHERE role='user'")
        for u in recipients:
            await db_execute(
                """INSERT INTO notifications
                   (notification_id, user_id, title, message, notification_type, `read`, created_at, created_by)
                   VALUES (%s,%s,%s,%s,%s,0,%s,%s)""",
                (notification_id, u["user_id"], notification.title, notification.message,
                 notification.notification_type, now, admin.get("name", admin.get("email")))
            )

    for recipient in recipients:
        if recipient.get("email"):
            await send_email(
                recipient["email"],
                f"{notification.title} - HH Jaba",
                get_transactional_update_html(
                    recipient.get("name", "Customer"),
                    notification.title,
                    f"<p>{html.escape(notification.message)}</p>",
                    [("Notification Type", html.escape(notification.notification_type.upper()))],
                    "<p>You can also view this update inside your HH Jaba account.</p>"
                )
            )

    return {"message": "Notification created", "notification_id": notification_id}

@api_router.get("/notifications")
async def get_user_notifications(request: Request):
    """Get user's notifications."""
    user = await get_current_user(request)
    return await db_fetchall(
        "SELECT * FROM notifications WHERE user_id=%s ORDER BY created_at DESC LIMIT 100",
        (user["user_id"],)
    )

@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, request: Request):
    """Mark notification as read."""
    user = await get_current_user(request)
    await db_execute(
        "UPDATE notifications SET `read`=1 WHERE notification_id=%s AND user_id=%s",
        (notification_id, user["user_id"])
    )
    return {"message": "Notification marked as read"}

@api_router.get("/notifications/unread-count")
async def get_unread_count(request: Request):
    """Get count of unread notifications."""
    user = await get_current_user(request)
    count = await db_count(
        "SELECT COUNT(*) FROM notifications WHERE user_id=%s AND `read`=0",
        (user["user_id"],)
    )
    return {"unread_count": count}


# ===== USER DASHBOARD STATS =====

@api_router.get("/users/dashboard-stats")
async def get_user_dashboard_stats(request: Request):
    """Get user dashboard statistics."""
    user = await get_current_user(request)
    uid = user["user_id"]

    all_orders = await db_fetchall(
        "SELECT * FROM orders WHERE user_id=%s AND status != 'cancelled'", (uid,)
    )
    invoices = await db_fetchall(
        "SELECT * FROM credit_invoices WHERE user_id=%s ORDER BY created_at DESC LIMIT 100", (uid,)
    )
    payments = await db_fetchall(
        "SELECT * FROM payment_submissions WHERE user_id=%s ORDER BY submitted_at DESC LIMIT 100", (uid,)
    )

    total_pending = sum(float(o.get("total_amount", 0)) for o in all_orders if o.get("status") == "pending")
    total_owed = MONTHLY_CREDIT_LIMIT - float(user.get("credit_balance", MONTHLY_CREDIT_LIMIT))
    total_approved_payments = sum(float(p.get("verified_amount", 0) or 0) for p in payments if p.get("status") == "approved")
    pending_pop_count = sum(1 for p in payments if p.get("status") == "pending")
    paid_invoices = [inv for inv in invoices if inv.get("status") == "paid"]
    unpaid_invoices = [inv for inv in invoices if inv.get("status") != "paid"]

    return {
        "credit_balance": user.get("credit_balance", MONTHLY_CREDIT_LIMIT),
        "monthly_limit": MONTHLY_CREDIT_LIMIT,
        "total_pending": total_pending,
        "total_owed": total_owed if total_owed > 0 else 0,
        "total_orders": len(all_orders),
        "total_approved_payments": total_approved_payments,
        "pending_pop_count": pending_pop_count,
        "paid_invoices_count": len(paid_invoices),
        "unpaid_invoices_count": len(unpaid_invoices),
        "invoices": invoices[:5],
        "recent_payments": payments[:5]
    }

@api_router.get("/users/invoices")
async def get_user_invoices(request: Request):
    """Get invoices for current user."""
    user = await get_current_user(request)
    return await db_fetchall(
        "SELECT * FROM credit_invoices WHERE user_id=%s ORDER BY created_at DESC LIMIT 100",
        (user["user_id"],)
    )


@api_router.post("/users/invoices/{invoice_id}/send-email")
async def resend_user_invoice_email(invoice_id: str, request: Request):
    """Send or resend the current user's invoice email."""
    user = await get_current_user(request)

    invoice = await db_fetchone(
        "SELECT * FROM credit_invoices WHERE invoice_id=%s AND user_id=%s",
        (invoice_id, user["user_id"])
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    recipient_email = invoice.get("customer_email") or user.get("email")
    email_response = await send_credit_invoice_email(invoice, recipient_email=recipient_email, subject_prefix="Invoice Copy")
    if not email_response:
        raise HTTPException(status_code=502, detail="Failed to send invoice email")

    return {
        "message": f"Invoice sent to {recipient_email}",
        "invoice_id": invoice_id,
        "recipient": recipient_email
    }


# ===== POP (PROOF OF PAYMENT) ROUTES =====

@api_router.post("/payments/submit-pop")
async def submit_pop(pop_data: POPSubmission, request: Request):
    """Customer submits proof of payment against an invoice."""
    user = await get_current_user(request)

    invoice = await db_fetchone(
        "SELECT * FROM credit_invoices WHERE invoice_id=%s AND user_id=%s",
        (pop_data.invoice_id, user["user_id"])
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found or does not belong to you")

    pop_id = f"POP-{uuid.uuid4().hex[:8].upper()}"
    now = _now()

    await db_execute(
        """INSERT INTO payment_submissions
           (pop_id, invoice_id, user_id, user_name, user_email, transaction_code,
            amount_paid, payment_method, payment_type, notes, status, submitted_at, audit_trail)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending',%s,%s)""",
        (
            pop_id, pop_data.invoice_id, user["user_id"],
            user.get("name", ""), user.get("email", ""),
            pop_data.transaction_code, pop_data.amount_paid,
            pop_data.payment_method, pop_data.payment_type,
            pop_data.notes, now, _serialize([])
        )
    )

    admins = await get_privileged_users()
    for admin in admins:
        await db_execute(
            """INSERT INTO notifications
               (notification_id, user_id, title, message, notification_type, `read`, created_at)
               VALUES (%s,%s,%s,%s,'payment',0,%s)""",
            (
                f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
                admin["user_id"],
                "Payment Proof Submitted",
                f"{user.get('name')} submitted POP for Invoice {pop_data.invoice_id}: KES {pop_data.amount_paid:,.0f} ({pop_data.payment_type})",
                now
            )
        )

    if user.get("email"):
        await send_email(
            user["email"],
            f"Payment Proof Received - HH Jaba {pop_data.invoice_id}",
            get_transactional_update_html(
                user.get("name", "Customer"),
                "Payment Proof Received",
                f"""
                <p>We have received your proof of payment for invoice <strong>{html.escape(pop_data.invoice_id)}</strong>.</p>
                <p>The HH Jaba team will verify the transaction and notify you once the review is complete.</p>
                """,
                [
                    ("Invoice ID", html.escape(pop_data.invoice_id)),
                    ("Transaction Code", html.escape(pop_data.transaction_code.upper())),
                    ("Amount Submitted", _format_email_currency(pop_data.amount_paid)),
                    ("Payment Type", html.escape(pop_data.payment_type.replace("_", " ").title())),
                ],
                "<p>Please keep the original transaction confirmation until verification is complete.</p>"
            )
        )

    return {"pop_id": pop_id, "message": "Payment proof submitted for verification"}

@api_router.get("/payments/my-submissions")
async def get_my_pop_submissions(request: Request):
    """Get current user's POP submissions."""
    user = await get_current_user(request)
    return await db_fetchall(
        "SELECT * FROM payment_submissions WHERE user_id=%s ORDER BY submitted_at DESC LIMIT 100",
        (user["user_id"],)
    )

@api_router.get("/admin/payments/pending")
async def get_pending_payments(request: Request):
    """Get all pending/failed payment submissions (admin only)."""
    await get_admin_user(request)
    return await db_fetchall(
        "SELECT * FROM payment_submissions WHERE status IN ('pending','verification_failed') ORDER BY submitted_at DESC"
    )

@api_router.get("/admin/payments/all")
async def get_all_payments(request: Request):
    """Get all payment submissions (admin only)."""
    await get_admin_user(request)
    return await db_fetchall("SELECT * FROM payment_submissions ORDER BY submitted_at DESC")

@api_router.post("/admin/payments/{pop_id}/match")
async def match_transaction(pop_id: str, match_data: TransactionMatch, request: Request):
    """Admin enters their transaction code/amount to match against customer's POP."""
    admin = await get_admin_user(request)

    pop = await db_fetchone("SELECT * FROM payment_submissions WHERE pop_id=%s", (pop_id,))
    if not pop:
        raise HTTPException(status_code=404, detail="Payment submission not found")

    if pop["status"] not in ["pending", "verification_failed"]:
        raise HTTPException(status_code=400, detail="Payment already processed")

    code_match = pop["transaction_code"].strip().upper() == match_data.admin_transaction_code.strip().upper()
    amount_match = abs(float(pop["amount_paid"]) - match_data.admin_amount) < 1

    now = _now()
    admin_name = admin.get("name", admin.get("email"))

    audit_entry = {
        "action": "transaction_match",
        "admin": admin_name,
        "timestamp": now.isoformat(),
        "admin_code": match_data.admin_transaction_code.upper(),
        "admin_amount": match_data.admin_amount,
        "customer_code": pop["transaction_code"],
        "customer_amount": float(pop["amount_paid"]),
        "code_match": code_match,
        "amount_match": amount_match
    }

    if code_match and amount_match:
        verified_amount = match_data.admin_amount
        await db_execute(
            """UPDATE payment_submissions SET
               status='approved', verified_amount=%s, verified_at=%s, verified_by=%s,
               admin_transaction_code=%s, admin_amount=%s, match_method='auto',
               audit_trail=JSON_ARRAY_APPEND(COALESCE(audit_trail, JSON_ARRAY()), '$', CAST(%s AS JSON))
               WHERE pop_id=%s""",
            (verified_amount, now, admin_name,
             match_data.admin_transaction_code.upper(), match_data.admin_amount,
             _serialize(audit_entry), pop_id)
        )
        await _apply_approved_payment(pop, verified_amount)
        return {"status": "approved", "message": "Transaction codes and amounts match. Payment approved."}
    else:
        reasons = []
        if not code_match:
            reasons.append(f"Code mismatch: Customer '{pop['transaction_code']}' vs Admin '{match_data.admin_transaction_code.upper()}'")
        if not amount_match:
            reasons.append(f"Amount mismatch: Customer KES {float(pop['amount_paid']):,.0f} vs Admin KES {match_data.admin_amount:,.0f}")
        decline_reason = "; ".join(reasons)

        await db_execute(
            """UPDATE payment_submissions SET
               status='verification_failed', admin_transaction_code=%s, admin_amount=%s,
               decline_reason=%s, declined_at=%s, declined_by=%s,
               audit_trail=JSON_ARRAY_APPEND(COALESCE(audit_trail, JSON_ARRAY()), '$', CAST(%s AS JSON))
               WHERE pop_id=%s""",
            (match_data.admin_transaction_code.upper(), match_data.admin_amount,
             decline_reason, now, admin_name, _serialize(audit_entry), pop_id)
        )

        await db_execute(
            """INSERT INTO notifications
               (notification_id, user_id, title, message, notification_type, pop_id, `read`, created_at)
               VALUES (%s,%s,%s,%s,'payment_declined',%s,0,%s)""",
            (
                f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
                pop["user_id"],
                "Payment Declined",
                f"Payment for Invoice {pop['invoice_id']} verification failed. Reason: {decline_reason}. You can raise a dispute to resolve this.",
                pop_id, now
            )
        )

        if pop.get("user_email"):
            await send_email(
                pop["user_email"],
                f"Payment Verification Failed - HH Jaba {pop['invoice_id']}",
                get_transactional_update_html(
                    pop.get("user_name", "Customer"),
                    "Payment Verification Failed",
                    f"""
                    <p>Your payment submission for invoice <strong>{html.escape(pop['invoice_id'])}</strong> could not be verified automatically.</p>
                    <p>Please review the mismatch details below and raise a dispute in the portal if needed.</p>
                    """,
                    [
                        ("Invoice ID", html.escape(pop["invoice_id"])),
                        ("POP ID", html.escape(pop_id)),
                        ("Submitted Amount", _format_email_currency(pop.get("amount_paid", 0))),
                        ("Verification Reason", html.escape(decline_reason)),
                    ],
                    "<p>You can submit additional evidence through the dispute chat linked to this payment proof.</p>"
                )
            )
        return {"status": "verification_failed", "message": decline_reason}

@api_router.post("/admin/payments/{pop_id}/force-approve")
async def force_approve_payment(pop_id: str, approval: ForceApproval, request: Request):
    """Admin force-approves a failed transaction after chat resolution."""
    admin = await get_admin_user(request)

    pop = await db_fetchone("SELECT * FROM payment_submissions WHERE pop_id=%s", (pop_id,))
    if not pop:
        raise HTTPException(status_code=404, detail="Payment submission not found")

    if pop["status"] == "approved":
        raise HTTPException(status_code=400, detail="Payment already approved")

    if not approval.reason or len(approval.reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="A detailed reason is required for manual override")

    now = _now()
    admin_name = admin.get("name", admin.get("email"))
    verified_amount = float(pop.get("admin_amount") or pop["amount_paid"])

    audit_entry = {
        "action": "force_approve",
        "admin": admin_name,
        "timestamp": now.isoformat(),
        "reason": approval.reason,
        "amount": verified_amount
    }

    await db_execute(
        """UPDATE payment_submissions SET
           status='approved', verified_amount=%s, verified_at=%s, verified_by=%s,
           match_method='force_approved', force_approve_reason=%s,
           audit_trail=JSON_ARRAY_APPEND(COALESCE(audit_trail, JSON_ARRAY()), '$', CAST(%s AS JSON))
           WHERE pop_id=%s""",
        (verified_amount, now, admin_name, approval.reason, _serialize(audit_entry), pop_id)
    )

    await _apply_approved_payment(pop, verified_amount, approval.reason)
    return {"message": f"Payment force-approved by {admin_name}. Reason: {approval.reason}", "pop_id": pop_id}

@api_router.post("/admin/payments/{pop_id}/reject")
async def reject_payment_direct(pop_id: str, verification: PaymentVerification, request: Request):
    """Admin rejects a payment submission."""
    admin = await get_admin_user(request)

    pop = await db_fetchone("SELECT * FROM payment_submissions WHERE pop_id=%s", (pop_id,))
    if not pop:
        raise HTTPException(status_code=404, detail="Payment submission not found")

    now = _now()
    admin_name = admin.get("name", admin.get("email"))

    audit_entry = {
        "action": "rejected",
        "admin": admin_name,
        "timestamp": now.isoformat(),
        "reason": verification.reason
    }

    await db_execute(
        """UPDATE payment_submissions SET
           status='rejected', verified_at=%s, verified_by=%s, rejection_reason=%s,
           audit_trail=JSON_ARRAY_APPEND(COALESCE(audit_trail, JSON_ARRAY()), '$', CAST(%s AS JSON))
           WHERE pop_id=%s""",
        (now, admin_name, verification.reason, _serialize(audit_entry), pop_id)
    )

    await db_execute(
        """INSERT INTO notifications
           (notification_id, user_id, title, message, notification_type, `read`, created_at)
           VALUES (%s,%s,%s,%s,'payment',0,%s)""",
        (
            f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
            pop["user_id"],
            "Payment Rejected",
            f"Payment for Invoice {pop['invoice_id']} was rejected. Reason: {verification.reason or 'Not specified'}. Please resubmit.",
            now
        )
    )

    if pop.get("user_email"):
        rejection_reason = verification.reason or "Not specified"
        await send_email(
            pop["user_email"],
            f"Payment Rejected - HH Jaba {pop['invoice_id']}",
            get_transactional_update_html(
                pop.get("user_name", "Customer"),
                "Payment Rejected",
                f"""
                <p>Your payment submission for invoice <strong>{html.escape(pop['invoice_id'])}</strong> has been rejected.</p>
                <p>Please review the rejection reason below and submit a new proof of payment.</p>
                """,
                [
                    ("Invoice ID", html.escape(pop["invoice_id"])),
                    ("POP ID", html.escape(pop_id)),
                    ("Rejected Amount", _format_email_currency(pop.get("amount_paid", 0))),
                    ("Reason", html.escape(rejection_reason)),
                ]
            )
        )

    return {"message": "Payment rejected", "pop_id": pop_id}

async def _apply_approved_payment(pop: dict, verified_amount: float, approval_note: Optional[str] = None):
    """Helper: Update invoice status and restore credit after payment approval."""
    invoice = await db_fetchone(
        "SELECT * FROM credit_invoices WHERE invoice_id=%s", (pop["invoice_id"],)
    )
    invoice_already_paid_by_admin = False
    if invoice:
        # If the invoice was marked paid manually by admin/super_admin, do NOT adjust credit balance here.
        if invoice.get("status") == "paid":
            invoice_already_paid_by_admin = True

        approved_sum = await db_fetchone(
            "SELECT COALESCE(SUM(verified_amount),0) as total FROM payment_submissions WHERE invoice_id=%s AND status='approved'",
            (pop["invoice_id"],)
        )
        total_paid = float(approved_sum.get("total", 0) or 0)
        new_status = "paid" if total_paid >= float(invoice.get("total_amount", 0)) else "partial"
        await db_execute(
            "UPDATE credit_invoices SET status=%s, total_paid=%s WHERE invoice_id=%s",
            (new_status, total_paid, pop["invoice_id"])
        )

    if not invoice_already_paid_by_admin:
        await db_execute(
            "UPDATE users SET credit_balance=credit_balance+%s WHERE user_id=%s",
            (verified_amount, pop["user_id"])
        )


    user = await db_fetchone("SELECT credit_balance FROM users WHERE user_id=%s", (pop["user_id"],))
    remaining = MONTHLY_CREDIT_LIMIT - float(user.get("credit_balance", 0)) if user else 0

    await db_execute(
        """INSERT INTO notifications
           (notification_id, user_id, title, message, notification_type, `read`, created_at)
           VALUES (%s,%s,%s,%s,'payment',0,%s)""",
        (
            f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
            pop["user_id"],
            "Payment Approved",
            f"Payment of KES {verified_amount:,.0f} for Invoice {pop['invoice_id']} approved. Balance owed: KES {max(0, remaining):,.0f}",
            _now()
        )
    )

    if pop.get("user_email"):
        detail_rows = [
            ("Invoice ID", html.escape(pop["invoice_id"])),
            ("POP ID", html.escape(pop["pop_id"])),
            ("Approved Amount", _format_email_currency(verified_amount)),
            ("Balance Owed", _format_email_currency(max(0, remaining))),
        ]
        if approval_note:
            detail_rows.append(("Approval Note", html.escape(approval_note)))

        await send_email(
            pop["user_email"],
            f"Payment Approved - HH Jaba {pop['invoice_id']}",
            get_transactional_update_html(
                pop.get("user_name", "Customer"),
                "Payment Approved",
                f"""
                <p>Your payment for invoice <strong>{html.escape(pop['invoice_id'])}</strong> has been approved.</p>
                <p>Your available credit has been updated accordingly.</p>
                """,
                detail_rows,
                "<p>If you still have an outstanding balance, please clear it before the next billing cycle.</p>"
            )
        )


# ===== DISPUTE CHAT ROUTES =====

@api_router.post("/disputes/message")
async def send_dispute_message(msg: DisputeMessage, request: Request):
    """Customer or admin sends a message linked to a POP transaction."""
    user = await get_current_user(request)

    pop = await db_fetchone("SELECT * FROM payment_submissions WHERE pop_id=%s", (msg.pop_id,))
    if not pop:
        raise HTTPException(status_code=404, detail="Transaction not found")

    is_admin = has_effective_role(user, "admin", "super_admin")
    if not is_admin and pop["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    message_id = f"MSG-{uuid.uuid4().hex[:8].upper()}"
    now = _now()

    await db_execute(
        """INSERT INTO dispute_messages
           (message_id, pop_id, invoice_id, sender_id, sender_name, sender_role, message, created_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (message_id, msg.pop_id, pop.get("invoice_id"),
            user["user_id"], user.get("name", ""), get_effective_role(user),
         msg.message, now)
    )

    if is_admin:
        await db_execute(
            """INSERT INTO notifications
               (notification_id, user_id, title, message, notification_type, pop_id, `read`, created_at)
               VALUES (%s,%s,%s,%s,'dispute',%s,0,%s)""",
            (
                f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
                pop["user_id"],
                "Admin Reply on Dispute",
                f"Admin replied to your dispute for {msg.pop_id}: \"{msg.message[:80]}{'...' if len(msg.message) > 80 else ''}\"",
                msg.pop_id, now
            )
        )
    else:
        admins = await get_privileged_users()
        for a in admins:
            await db_execute(
                """INSERT INTO notifications
                   (notification_id, user_id, title, message, notification_type, pop_id, `read`, created_at)
                   VALUES (%s,%s,%s,%s,'dispute',%s,0,%s)""",
                (
                    f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
                    a["user_id"],
                    f"Dispute Message from {user.get('name')}",
                    f"Re: {msg.pop_id} — \"{msg.message[:80]}\"",
                    msg.pop_id, now
                )
            )

    return {"message_id": message_id}

@api_router.get("/disputes/{pop_id}/messages")
async def get_dispute_messages(pop_id: str, request: Request):
    """Get all chat messages for a specific POP transaction."""
    user = await get_current_user(request)

    pop = await db_fetchone("SELECT * FROM payment_submissions WHERE pop_id=%s", (pop_id,))
    if not pop:
        raise HTTPException(status_code=404, detail="Transaction not found")

    is_admin = has_effective_role(user, "admin", "super_admin")
    if not is_admin and pop["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    messages = await db_fetchall(
        "SELECT * FROM dispute_messages WHERE pop_id=%s ORDER BY created_at ASC LIMIT 500",
        (pop_id,)
    )

    return {"pop_id": pop_id, "invoice_id": pop.get("invoice_id"), "messages": messages}

@api_router.get("/admin/disputes")
async def get_all_disputes(request: Request):
    """Get all POP transactions that have dispute messages (admin only)."""
    await get_admin_user(request)

    rows = await db_fetchall(
        """SELECT pop_id,
                  COUNT(*) as message_count,
                  MAX(created_at) as last_time,
                  SUBSTRING_INDEX(GROUP_CONCAT(message ORDER BY created_at DESC SEPARATOR '|||'), '|||', 1) as last_message,
                  SUBSTRING_INDEX(GROUP_CONCAT(sender_name ORDER BY created_at DESC SEPARATOR '|||'), '|||', 1) as last_sender
           FROM dispute_messages
           GROUP BY pop_id
           ORDER BY last_time DESC
           LIMIT 500"""
    )

    result = []
    for d in rows:
        pop = await db_fetchone("SELECT * FROM payment_submissions WHERE pop_id=%s", (d["pop_id"],))
        if pop:
            result.append({
                "pop_id": d["pop_id"],
                "invoice_id": pop.get("invoice_id"),
                "user_name": pop.get("user_name"),
                "user_id": pop.get("user_id"),
                "pop_status": pop.get("status"),
                "amount_paid": pop.get("amount_paid"),
                "transaction_code": pop.get("transaction_code"),
                "message_count": d["message_count"],
                "last_message": d["last_message"],
                "last_sender": d["last_sender"],
                "last_time": d["last_time"]
            })

    return result


# ===== STARTING CREDIT IMPORT =====

async def _create_starting_credit_entry(entry: StartingCreditEntry, request: Request):
    admin = await get_admin_user(request)

    if entry.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")

    user = await db_fetchone("SELECT * FROM users WHERE user_id=%s", (entry.user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db_execute(
        "UPDATE users SET credit_balance=credit_balance-%s WHERE user_id=%s",
        (entry.amount, entry.user_id)
    )

    date_str = datetime.now(timezone.utc).strftime('%Y%m%d')
    invoice_id = f"HHJ-INV-{date_str}-{uuid.uuid4().hex[:5].upper()}"
    now = _now()
    line_items = [{
        "flavor": "Starting Credit",
        "quantity": 1,
        "unit_price": entry.amount,
        "line_total": entry.amount,
        "status": "unpaid"
    }]

    await db_execute(
        """INSERT INTO credit_invoices
           (invoice_id, user_id, customer_name, customer_email, customer_phone,
            billing_period_start, billing_period_end, line_items, subtotal, total_amount,
            status, payment_type, notes, created_at, created_by,
            company_email, payment_method, payment_number, is_backlog)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'unpaid','credit',%s,%s,%s,%s,%s,%s,1)""",
        (
            invoice_id, entry.user_id,
            user.get("name", ""), user.get("email", ""), user.get("phone", ""),
            entry.billing_period_start or datetime.now(timezone.utc).replace(day=1).strftime('%Y-%m-%d'),
            entry.billing_period_end or datetime.now(timezone.utc).strftime('%Y-%m-%d'),
            _serialize(line_items), entry.amount, entry.amount,
            f"Starting credit import: {entry.description}",
            now, admin.get("name", admin.get("email", "Admin")),
            "contact@myhappyhour.co.ke", "Airtel Money", "0733878020"
        )
    )

    await create_admin_audit_log(
        admin,
        action="add_starting_credit",
        target_type="user",
        target_id=entry.user_id,
        details={
            "invoice_id": invoice_id,
            "amount": entry.amount,
            "description": entry.description,
            "billing_period_start": entry.billing_period_start,
            "billing_period_end": entry.billing_period_end,
        },
    )

    return {
        "invoice_id": invoice_id,
        "message": f"Starting credit of KES {entry.amount:,.0f} added for {user.get('name')}"
    }


@api_router.post("/admin/starting-credit")
async def create_starting_credit(entry: StartingCreditEntry, request: Request):
    """Admin or super admin imports a user's legacy starting credit usage."""
    return await _create_starting_credit_entry(entry, request)


@api_router.post("/admin/backlog-credit")
async def create_backlog_credit(entry: BacklogCreditEntry, request: Request):
    """Backward-compatible route for historical clients; maps to starting credit import."""
    return await _create_starting_credit_entry(entry, request)


# ===== DEFAULTER WARNING TEMPLATES =====

@api_router.post("/admin/defaulter-warning/{user_id}")
async def send_defaulter_warning(user_id: str, request: Request, template: str = "overdue"):
    """Send a defaulter warning notification to a user."""
    await get_admin_user(request)

    user = await db_fetchone("SELECT * FROM users WHERE user_id=%s", (user_id,))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    outstanding = MONTHLY_CREDIT_LIMIT - float(user.get("credit_balance", MONTHLY_CREDIT_LIMIT))

    templates = {
        "limit_reached": {
            "title": "Credit Limit Reached (KES 30,000)",
            "message": f"Hi {user.get('name')}, your credit limit of KES 30,000 has been reached. Outstanding balance: KES {outstanding:,.0f}. Please settle your balance to continue ordering. Pay to Airtel Money 0733878020."
        },
        "overdue": {
            "title": "Overdue Payment Notice",
            "message": f"Hi {user.get('name')}, you have an overdue balance of KES {outstanding:,.0f}. Per our No Carry-Forward policy, this must be cleared before the next billing cycle. Pay to Airtel Money 0733878020."
        },
        "suspended": {
            "title": "Account Suspended",
            "message": f"Hi {user.get('name')}, your account has been suspended due to unpaid balance of KES {outstanding:,.0f}. Please clear your balance immediately to restore ordering privileges. Pay to Airtel Money 0733878020."
        }
    }

    tmpl = templates.get(template, templates["overdue"])

    await db_execute(
        """INSERT INTO notifications
           (notification_id, user_id, title, message, notification_type, `read`, created_at)
           VALUES (%s,%s,%s,%s,'warning',0,%s)""",
        (f"NOTIF-{uuid.uuid4().hex[:8].upper()}", user_id, tmpl["title"], tmpl["message"], _now())
    )

    wa_message = tmpl["message"].replace(" ", "%20")
    wa_link = f"https://wa.me/{user.get('phone', '').replace('+', '').replace(' ', '')}?text={wa_message}"

    return {"message": f"Warning sent to {user.get('name')}", "whatsapp_link": wa_link}


# ===== SUPER ADMIN ROUTES =====

@api_router.post("/admin/switch-role")
async def switch_role(request: Request, target_role: str = "super_admin"):
    """Super Admin switches their viewing role for testing."""
    user = await get_super_admin_user(request)

    if target_role not in ("super_admin", "admin", "user"):
        raise HTTPException(status_code=400, detail="Invalid role")

    session_token = await get_session_token(request)
    await db_execute(
        "UPDATE user_sessions SET impersonated_role=%s WHERE token_prefix=LEFT(%s,191)",
        (target_role, session_token)
    )
    await db_execute(
        "UPDATE users SET active_role=%s WHERE user_id=%s",
        (target_role, user["user_id"])
    )
    await create_admin_audit_log(
        user,
        "active_role_switched",
        "user",
        user["user_id"],
        {"target_role": target_role}
    )

    return {"message": f"Switched to {target_role} view", "active_role": target_role}

@api_router.get("/admin/current-role")
async def get_current_role(request: Request):
    """Get current active role for Super Admin."""
    user = await get_current_user(request)
    active_role = get_effective_role(user)
    is_super_admin = is_actual_super_admin(user)
    return {
        "actual_role": user.get("role"),
        "active_role": active_role,
        "is_super_admin": is_super_admin
    }

@api_router.post("/admin/maintenance/reset-test-data")
async def reset_test_data(request: Request):
    """Super Admin resets all test orders and invoices."""
    user = await get_super_admin_user(request)

    orders_count = await db_count("SELECT COUNT(*) FROM orders")
    invoices_count = await db_count("SELECT COUNT(*) FROM credit_invoices")
    payments_count = await db_count("SELECT COUNT(*) FROM payment_submissions")
    disputes_count = await db_count("SELECT COUNT(*) FROM dispute_messages")
    notifs_count = await db_count("SELECT COUNT(*) FROM notifications")

    await db_execute("DELETE FROM orders")
    await db_execute("DELETE FROM credit_invoices")
    await db_execute("DELETE FROM payment_submissions")
    await db_execute("DELETE FROM dispute_messages")
    await db_execute("DELETE FROM notifications")
    await db_execute("UPDATE users SET credit_balance=%s", (float(MONTHLY_CREDIT_LIMIT),))

    return {
        "message": "All test data cleared",
        "deleted": {
            "orders": orders_count,
            "invoices": invoices_count,
            "payments": payments_count,
            "disputes": disputes_count,
            "notifications": notifs_count
        }
    }

@api_router.post("/admin/maintenance/reset-counters")
async def reset_counters(request: Request):
    """Super Admin resets daily order counters."""
    user = await get_super_admin_user(request)

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
    count = await db_count(
        "SELECT COUNT(*) FROM orders WHERE created_at>=%s AND status IN ('pending','fulfilled')",
        (today_start,)
    )
    await db_execute(
        "DELETE FROM orders WHERE created_at>=%s AND status IN ('pending','fulfilled')",
        (today_start,)
    )

    return {"message": f"Reset {count} orders from today"}


# ===== ROOT ROUTE =====

@api_router.get("/")
async def root():
    return {"message": "HH Jaba Staff Portal API"}


# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    global pool
    pool = await aiomysql.create_pool(
        host=os.environ.get('MYSQL_HOST', 'localhost'),
        port=int(os.environ.get('MYSQL_PORT', 3306)),
        user=os.environ.get('MYSQL_USER', 'root'),
        password=os.environ.get('MYSQL_PASSWORD', ''),
        db=os.environ.get('MYSQL_DB', 'hhjaba'),
        autocommit=False,
        charset='utf8mb4',
        cursorclass=aiomysql.DictCursor,
        minsize=2,
        maxsize=10
    )
    await ensure_management_tables()
    await seed_approved_domains()
    await initialize_products()
    logger.info("HH Jaba Staff Portal API started (MySQL)")

@app.on_event("shutdown")
async def shutdown_db_client():
    pool.close()
    await pool.wait_closed()


# Serve React frontend static files
_frontend_build = ROOT_DIR.parent / "frontend" / "build"
if _frontend_build.exists():
    app.mount("/static", StaticFiles(directory=str(_frontend_build / "static")), name="static")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Serve actual files if they exist (favicon, manifest, etc.)
        file_path = _frontend_build / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        # Fallback to index.html for React Router
        return FileResponse(str(_frontend_build / "index.html"))
