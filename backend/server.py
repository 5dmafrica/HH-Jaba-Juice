from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import httpx
import resend

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Resend setup
resend.api_key = os.environ.get('RESEND_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')

# Admin emails
ADMIN_EMAILS = ['mavin@5dm.africa', 'yongo@5dm.africa']

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

# Order Cancellation Model
class OrderCancellation(BaseModel):
    reason: str

# Feedback Model
class FeedbackCreate(BaseModel):
    message: str
    subject: Optional[str] = None

# Notification Model
class NotificationCreate(BaseModel):
    title: str
    message: str
    notification_type: str = "general"  # 'offer', 'invoice', 'general'
    target_users: Optional[List[str]] = None  # None means all users

# Credit Purchase Invoice Models
class CreditInvoiceLineItem(BaseModel):
    flavor: str  # Tamarind, Watermelon, Beetroot, Pineapple, Hibiscus, Mixed Fruit
    quantity: int
    unit_price: float = 500.0
    status: str = "unpaid"  # 'paid' or 'unpaid'
    order_id: Optional[str] = None
    order_date: Optional[str] = None

class CreditInvoiceCreate(BaseModel):
    user_id: str
    billing_period_start: str  # ISO date string
    billing_period_end: str    # ISO date string
    line_items: List[CreditInvoiceLineItem]
    notes: Optional[str] = None

class CreditInvoice(BaseModel):
    invoice_id: str  # HHJ-INV-[Date]-[ID]
    user_id: str
    customer_name: str
    customer_email: str
    customer_phone: Optional[str] = None
    billing_period_start: str
    billing_period_end: str
    line_items: List[dict]
    subtotal: float
    total_amount: float
    status: str = "unpaid"  # 'paid', 'partial', 'unpaid'
    notes: Optional[str] = None
    created_at: str
    created_by: str  # Admin who created it

# ===== AUTH HELPERS =====

async def get_session_token(request: Request) -> Optional[str]:
    """Extract session token from cookie or Authorization header"""
    # Check cookie first
    session_token = request.cookies.get("session_token")
    if session_token:
        return session_token
    # Fallback to Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    return None

async def get_current_user(request: Request) -> dict:
    """Get current authenticated user"""
    session_token = await get_session_token(request)
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Find session
    session_doc = await db.user_sessions.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Check expiry
    expires_at = session_doc.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    
    # Get user
    user_doc = await db.users.find_one(
        {"user_id": session_doc["user_id"]},
        {"_id": 0}
    )
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user_doc

async def get_admin_user(request: Request) -> dict:
    """Get current user and verify admin role"""
    user = await get_current_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# ===== EMAIL SERVICE =====

async def send_email(recipient_email: str, subject: str, html_content: str):
    """Send email using Resend API"""
    if not resend.api_key:
        logger.warning("Resend API key not configured, skipping email")
        return None
    
    params = {
        "from": SENDER_EMAIL,
        "to": [recipient_email],
        "subject": subject,
        "html": html_content
    }
    
    try:
        email = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Email sent to {recipient_email}")
        return email
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return None

def get_order_confirmation_html(order: dict, user: dict) -> str:
    """Generate order confirmation email HTML"""
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
    """Initialize default products if none exist"""
    count = await db.products.count_documents({})
    if count == 0:
        products = [
            {
                "product_id": f"prod_{uuid.uuid4().hex[:12]}",
                "name": "Happy Hour Jaba - Tamarind",
                "description": "Refreshing tamarind flavored beer",
                "price": 500.0,
                "stock": 100,
                "active": True,
                "color": "#8B4513",
                "image_url": "https://images.unsplash.com/photo-1763178947953-ae2fdb2410f7?auto=format&fit=crop&w=600&q=80",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "product_id": f"prod_{uuid.uuid4().hex[:12]}",
                "name": "Happy Hour Jaba - Watermelon",
                "description": "Sweet watermelon flavored beer",
                "price": 500.0,
                "stock": 100,
                "active": True,
                "color": "#FF1493",
                "image_url": "https://images.unsplash.com/photo-1769777134533-41f68b35df0e?auto=format&fit=crop&w=600&q=80",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "product_id": f"prod_{uuid.uuid4().hex[:12]}",
                "name": "Happy Hour Jaba - Beetroot",
                "description": "Earthy beetroot flavored beer",
                "price": 500.0,
                "stock": 100,
                "active": True,
                "color": "#8B0000",
                "image_url": "https://images.pexels.com/photos/5668199/pexels-photo-5668199.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "product_id": f"prod_{uuid.uuid4().hex[:12]}",
                "name": "Happy Hour Jaba - Pineapple",
                "description": "Tropical pineapple flavored beer",
                "price": 500.0,
                "stock": 100,
                "active": True,
                "color": "#FFD700",
                "image_url": "https://images.pexels.com/photos/21576286/pexels-photo-21576286.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "product_id": f"prod_{uuid.uuid4().hex[:12]}",
                "name": "Happy Hour Jaba - Hibiscus",
                "description": "Floral hibiscus flavored beer",
                "price": 500.0,
                "stock": 100,
                "active": True,
                "color": "#DC143C",
                "image_url": "https://images.unsplash.com/photo-1763178947953-ae2fdb2410f7?auto=format&fit=crop&w=600&q=80",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        ]
        await db.products.insert_many(products)
        logger.info("Initialized 5 default products")

# ===== AUTH ROUTES =====

@api_router.post("/auth/session")
async def exchange_session(request: Request, response: Response):
    """Exchange session_id for session_token via Emergent Auth"""
    body = await request.json()
    session_id = body.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    # Call Emergent Auth API
    async with httpx.AsyncClient() as client:
        try:
            auth_response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": session_id}
            )
            if auth_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid session_id")
            
            auth_data = auth_response.json()
        except httpx.RequestError as e:
            logger.error(f"Auth API error: {e}")
            raise HTTPException(status_code=500, detail="Authentication service error")
    
    email = auth_data.get("email", "")
    name = auth_data.get("name", "")
    picture = auth_data.get("picture", "")
    session_token = auth_data.get("session_token", "")
    
    # Validate email domain
    if not email.endswith("@5dm.africa"):
        raise HTTPException(
            status_code=403, 
            detail="Only @5dm.africa email addresses are allowed"
        )
    
    # Check if user exists
    existing_user = await db.users.find_one({"email": email}, {"_id": 0})
    
    if existing_user:
        # Update existing user
        await db.users.update_one(
            {"email": email},
            {"$set": {
                "name": name,
                "picture": picture,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        user_id = existing_user["user_id"]
    else:
        # Create new user
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        role = "admin" if email in ADMIN_EMAILS else "user"
        
        new_user = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "phone": None,
            "credit_balance": 10000.0,
            "role": role,
            "accepted_terms": False,
            "accepted_terms_at": None,
            "picture": picture,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(new_user)
    
    # Store session
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.delete_many({"user_id": user_id})  # Remove old sessions
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60  # 7 days
    )
    
    # Get updated user
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    
    return {"user": user, "session_token": session_token}

@api_router.get("/auth/me")
async def get_me(request: Request):
    """Get current authenticated user"""
    user = await get_current_user(request)
    return user

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user and clear session"""
    session_token = await get_session_token(request)
    if session_token:
        await db.user_sessions.delete_many({"session_token": session_token})
    
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out successfully"}

# ===== USER ROUTES =====

@api_router.post("/users/profile-setup")
async def setup_profile(profile: ProfileSetup, request: Request):
    """Complete user profile setup with phone and T&C acceptance"""
    user = await get_current_user(request)
    
    if not profile.accept_terms:
        raise HTTPException(status_code=400, detail="You must accept the terms and conditions")
    
    # Validate Kenyan phone number
    phone = profile.phone.strip()
    if phone.startswith("+254"):
        phone = "0" + phone[4:]
    elif phone.startswith("254"):
        phone = "0" + phone[3:]
    
    if not (phone.startswith("07") or phone.startswith("01")) or len(phone) != 10:
        raise HTTPException(status_code=400, detail="Invalid Kenyan phone number format")
    
    # Check if phone already exists for another user
    existing = await db.users.find_one(
        {"phone": phone, "user_id": {"$ne": user["user_id"]}},
        {"_id": 0}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    
    # Update user
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {
            "phone": phone,
            "accepted_terms": True,
            "accepted_terms_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    updated_user = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return updated_user

@api_router.get("/users/credit-balance")
async def get_credit_balance(request: Request):
    """Get user's current credit balance"""
    user = await get_current_user(request)
    return {"credit_balance": user.get("credit_balance", 0)}

# ===== PRODUCT ROUTES =====

@api_router.get("/products")
async def get_products():
    """Get all active products"""
    products = await db.products.find({"active": True}, {"_id": 0}).to_list(100)
    return products

@api_router.get("/products/all")
async def get_all_products(request: Request):
    """Get all products (admin only)"""
    await get_admin_user(request)
    products = await db.products.find({}, {"_id": 0}).to_list(100)
    return products

@api_router.put("/products/{product_id}/stock")
async def update_stock(product_id: str, stock_update: StockUpdate, request: Request):
    """Update product stock (admin only) - increments by default"""
    await get_admin_user(request)
    
    product = await db.products.find_one({"product_id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Build update document
    update_doc = {
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Add production info if provided
    if stock_update.manufacturing_date:
        update_doc["last_manufacturing_date"] = stock_update.manufacturing_date
    if stock_update.batch_id:
        update_doc["last_batch_id"] = stock_update.batch_id
    
    # Increment or set stock based on flag
    if stock_update.increment:
        # Add to existing stock
        result = await db.products.update_one(
            {"product_id": product_id},
            {
                "$inc": {"stock": stock_update.stock},
                "$set": update_doc
            }
        )
        
        # Log stock entry
        await db.stock_entries.insert_one({
            "entry_id": f"STK-{uuid.uuid4().hex[:8].upper()}",
            "product_id": product_id,
            "product_name": product.get("name"),
            "quantity_added": stock_update.stock,
            "manufacturing_date": stock_update.manufacturing_date,
            "batch_id": stock_update.batch_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    else:
        # Set absolute value
        update_doc["stock"] = stock_update.stock
        result = await db.products.update_one(
            {"product_id": product_id},
            {"$set": update_doc}
        )
    
    updated_product = await db.products.find_one({"product_id": product_id}, {"_id": 0})
    return updated_product

@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, request: Request):
    """Deactivate a product (admin only)"""
    await get_admin_user(request)
    
    result = await db.products.update_one(
        {"product_id": product_id},
        {"$set": {
            "active": False,
            "stock": 0,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"message": "Product deactivated"}

# ===== ORDER ROUTES =====

@api_router.post("/orders")
async def create_order(order_data: OrderCreate, request: Request):
    """Create a new order"""
    user = await get_current_user(request)
    
    # Check if profile is complete
    if not user.get("accepted_terms") or not user.get("phone"):
        raise HTTPException(status_code=400, detail="Please complete your profile setup first")
    
    # Calculate total
    total_quantity = sum(item.quantity for item in order_data.items)
    total_amount = sum(item.quantity * item.price for item in order_data.items)
    
    if total_quantity == 0:
        raise HTTPException(status_code=400, detail="Order must have at least one item")
    
    if total_quantity > DAILY_ORDER_LIMIT:
        raise HTTPException(status_code=400, detail=f"Maximum {DAILY_ORDER_LIMIT} bottles per order")
    
    # Check daily limit (10 bottles any payment method)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_orders = await db.orders.find({
        "user_id": user["user_id"],
        "created_at": {"$gte": today_start.isoformat()},
        "status": {"$ne": "cancelled"}
    }, {"_id": 0}).to_list(100)
    
    today_bottles = sum(
        sum(item.get("quantity", 0) for item in order.get("items", []))
        for order in today_orders
    )
    
    if today_bottles + total_quantity > DAILY_ORDER_LIMIT:
        raise HTTPException(
            status_code=400, 
            detail=f"Daily limit of {DAILY_ORDER_LIMIT} bottles reached. You've ordered {today_bottles} today."
        )
    
    # For credit payments, check additional limits
    if order_data.payment_method == "credit":
        # Check credit balance
        if user.get("credit_balance", 0) < total_amount:
            raise HTTPException(
                status_code=400, 
                detail="Insufficient credit balance"
            )
        
        # Check monthly credit limit (30,000 KES)
        month_start = today_start.replace(day=1)
        month_credit_orders = await db.orders.find({
            "user_id": user["user_id"],
            "payment_method": "credit",
            "created_at": {"$gte": month_start.isoformat()},
            "status": {"$ne": "cancelled"}
        }, {"_id": 0}).to_list(1000)
        
        month_credit_used = sum(order.get("total_amount", 0) for order in month_credit_orders)
        
        if month_credit_used + total_amount > MONTHLY_CREDIT_LIMIT:
            raise HTTPException(
                status_code=400, 
                detail=f"Monthly credit limit of KES {MONTHLY_CREDIT_LIMIT:,} reached. You've used KES {month_credit_used:,} this month."
            )
        
        # Check weekly credit limit (10 bottles per week)
        week_start = today_start - timedelta(days=today_start.weekday())
        week_orders = await db.orders.find({
            "user_id": user["user_id"],
            "payment_method": "credit",
            "created_at": {"$gte": week_start.isoformat()},
            "status": {"$ne": "cancelled"}
        }, {"_id": 0}).to_list(100)
        
        week_bottles = sum(
            sum(item.get("quantity", 0) for item in order.get("items", []))
            for order in week_orders
        )
        
        if week_bottles + total_quantity > WEEKLY_CREDIT_LIMIT:
            raise HTTPException(
                status_code=400, 
                detail=f"Weekly credit limit of {WEEKLY_CREDIT_LIMIT} bottles reached. You've used {week_bottles} on credit this week."
            )
        
        # Deduct credit
        await db.users.update_one(
            {"user_id": user["user_id"]},
            {"$inc": {"credit_balance": -total_amount}}
        )
    
    # Validate M-Pesa code
    if order_data.payment_method == "mpesa":
        if not order_data.mpesa_code or len(order_data.mpesa_code) < 5:
            raise HTTPException(status_code=400, detail="Valid M-Pesa transaction code required")
    
    # Create order
    order_id = f"ORD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"
    
    order = {
        "order_id": order_id,
        "user_id": user["user_id"],
        "user_name": user.get("name", ""),
        "user_email": user.get("email", ""),
        "user_phone": user.get("phone", ""),
        "items": [item.model_dump() for item in order_data.items],
        "total_amount": total_amount,
        "payment_method": order_data.payment_method,
        "mpesa_code": order_data.mpesa_code if order_data.payment_method == "mpesa" else None,
        "status": "fulfilled" if order_data.payment_method == "credit" else "pending",
        "verification_status": "verified" if order_data.payment_method == "credit" else "pending",
        "receipt_url": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.orders.insert_one(order)
    
    # Update stock
    for item in order_data.items:
        await db.products.update_one(
            {"name": item.product_name},
            {"$inc": {"stock": -item.quantity}}
        )
    
    # Send confirmation email
    order_doc = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    await send_email(
        user.get("email", ""),
        f"Order Confirmed - HH Jaba #{order_id}",
        get_order_confirmation_html(order_doc, user)
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
    """Get user's order history with filters"""
    user = await get_current_user(request)
    
    query = {"user_id": user["user_id"]}
    
    if payment_method and payment_method != "all":
        query["payment_method"] = payment_method
    
    if status and status != "all":
        query["status"] = status
    
    if from_date:
        query["created_at"] = {"$gte": from_date}
    
    if to_date:
        if "created_at" in query:
            query["created_at"]["$lte"] = to_date
        else:
            query["created_at"] = {"$lte": to_date}
    
    orders = await db.orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return orders

@api_router.get("/orders/{order_id}")
async def get_order(order_id: str, request: Request):
    """Get specific order details"""
    user = await get_current_user(request)
    
    order = await db.orders.find_one(
        {"order_id": order_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return order

# ===== ADMIN ROUTES =====

@api_router.get("/admin/pending-orders")
async def get_pending_orders(request: Request, payment_method: Optional[str] = None):
    """Get all pending orders (admin only)"""
    await get_admin_user(request)
    
    query = {"status": "pending"}
    if payment_method and payment_method != "all":
        query["payment_method"] = payment_method
    
    orders = await db.orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return orders

@api_router.post("/admin/orders/{order_id}/fulfill")
async def fulfill_order(order_id: str, request: Request):
    """Mark order as fulfilled (admin only)"""
    await get_admin_user(request)
    
    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    await db.orders.update_one(
        {"order_id": order_id},
        {"$set": {
            "status": "fulfilled",
            "verification_status": "verified",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Send fulfillment email
    user = await db.users.find_one({"user_id": order["user_id"]}, {"_id": 0})
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
                    <p>Your order #{order_id} has been fulfilled.</p>
                    <p>Thank you for your order!</p>
                </div>
            </div>
            """
        )
    
    updated_order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    return updated_order

@api_router.post("/admin/orders/{order_id}/cancel")
async def cancel_order(order_id: str, cancellation: OrderCancellation, request: Request):
    """Cancel an order with mandatory reason (admin only)"""
    admin = await get_admin_user(request)
    
    if not cancellation.reason or len(cancellation.reason.strip()) < 5:
        raise HTTPException(status_code=400, detail="Cancellation reason is required (minimum 5 characters)")
    
    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Refund credit if credit payment
    if order.get("payment_method") == "credit":
        await db.users.update_one(
            {"user_id": order["user_id"]},
            {"$inc": {"credit_balance": order["total_amount"]}}
        )
    
    # Restore stock
    for item in order.get("items", []):
        await db.products.update_one(
            {"name": item["product_name"]},
            {"$inc": {"stock": item["quantity"]}}
        )
    
    await db.orders.update_one(
        {"order_id": order_id},
        {"$set": {
            "status": "cancelled",
            "verification_status": "rejected",
            "cancellation_reason": cancellation.reason,
            "cancelled_by": admin.get("name", admin.get("email")),
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify customer
    user = await db.users.find_one({"user_id": order["user_id"]}, {"_id": 0})
    if user:
        # Create notification
        await db.notifications.insert_one({
            "notification_id": f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
            "user_id": order["user_id"],
            "title": "Order Cancelled",
            "message": f"Your order #{order_id} has been cancelled. Reason: {cancellation.reason}",
            "notification_type": "order",
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    return {"message": "Order cancelled", "reason": cancellation.reason}

@api_router.post("/admin/orders/{order_id}/reject")
async def reject_order(order_id: str, request: Request):
    """Reject an order (admin only) - deprecated, use cancel instead"""
    await get_admin_user(request)
    
    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Refund credit if credit payment
    if order.get("payment_method") == "credit":
        await db.users.update_one(
            {"user_id": order["user_id"]},
            {"$inc": {"credit_balance": order["total_amount"]}}
        )
    
    # Restore stock
    for item in order.get("items", []):
        await db.products.update_one(
            {"name": item["product_name"]},
            {"$inc": {"stock": item["quantity"]}}
        )
    
    await db.orders.update_one(
        {"order_id": order_id},
        {"$set": {
            "status": "cancelled",
            "verification_status": "rejected",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Order rejected and refunded"}

@api_router.get("/admin/reconciliation")
async def get_reconciliation(request: Request, search: Optional[str] = None):
    """Get users with outstanding credit balances (admin only)"""
    await get_admin_user(request)
    
    # Get all users with credit balance used (less than monthly limit)
    query = {"credit_balance": {"$lt": MONTHLY_CREDIT_LIMIT}}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}}
        ]
    
    users = await db.users.find(query, {"_id": 0}).to_list(1000)
    
    result = []
    for user in users:
        outstanding = MONTHLY_CREDIT_LIMIT - user.get("credit_balance", MONTHLY_CREDIT_LIMIT)
        if outstanding > 0:
            # Get detailed order history
            orders = await db.orders.find(
                {"user_id": user["user_id"], "payment_method": "credit", "status": {"$ne": "cancelled"}},
                {"_id": 0}
            ).sort("created_at", -1).to_list(100)
            
            # Calculate totals
            total_pending = sum(o.get("total_amount", 0) for o in orders if o.get("status") == "pending")
            total_fulfilled = sum(o.get("total_amount", 0) for o in orders if o.get("status") == "fulfilled")
            
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
    """Get monthly defaulters (admin only) - No VAT penalty"""
    await get_admin_user(request)
    
    # Get users with outstanding balance
    query = {"credit_balance": {"$lt": MONTHLY_CREDIT_LIMIT}}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}}
        ]
    
    users = await db.users.find(query, {"_id": 0}).to_list(1000)
    
    result = []
    for user in users:
        outstanding = MONTHLY_CREDIT_LIMIT - user.get("credit_balance", MONTHLY_CREDIT_LIMIT)
        if outstanding > 0:
            orders = await db.orders.find(
                {"user_id": user["user_id"], "payment_method": "credit", "status": {"$ne": "cancelled"}},
                {"_id": 0}
            ).sort("created_at", -1).to_list(100)
            
            result.append({
                "user": user,
                "outstanding_balance": outstanding,
                "total_due": outstanding,  # No VAT penalty - matches invoice format
                "orders": orders
            })
    
    return result

@api_router.get("/admin/users")
async def get_all_users(request: Request):
    """Get all users (admin only)"""
    await get_admin_user(request)
    users = await db.users.find({}, {"_id": 0}).to_list(1000)
    return users

@api_router.post("/admin/manual-invoice")
async def create_manual_invoice(invoice: ManualInvoiceCreate, request: Request):
    """Create a manual invoice (admin only)"""
    await get_admin_user(request)
    
    invoice_id = f"INV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"
    
    invoice_doc = {
        "invoice_id": invoice_id,
        "user_id": invoice.user_id,
        "customer_name": invoice.customer_name,
        "amount": invoice.amount,
        "description": invoice.description,
        "payment_method": invoice.payment_method,
        "mpesa_code": invoice.mpesa_code,
        "product_name": invoice.product_name,
        "quantity": invoice.quantity,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.manual_invoices.insert_one(invoice_doc)
    
    return await db.manual_invoices.find_one({"invoice_id": invoice_id}, {"_id": 0})

@api_router.get("/admin/manual-invoices")
async def get_manual_invoices(request: Request):
    """Get all manual invoices (admin only)"""
    await get_admin_user(request)
    invoices = await db.manual_invoices.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return invoices

@api_router.post("/admin/manual-invoices/{invoice_id}/verify")
async def verify_manual_invoice(invoice_id: str, request: Request):
    """Verify a manual invoice (admin only)"""
    await get_admin_user(request)
    
    result = await db.manual_invoices.update_one(
        {"invoice_id": invoice_id},
        {"$set": {"status": "verified"}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return {"message": "Invoice verified"}

@api_router.post("/admin/manual-invoices/{invoice_id}/reject")
async def reject_manual_invoice(invoice_id: str, request: Request):
    """Reject a manual invoice (admin only)"""
    await get_admin_user(request)
    
    result = await db.manual_invoices.update_one(
        {"invoice_id": invoice_id},
        {"$set": {"status": "rejected"}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return {"message": "Invoice rejected"}

# ===== CREDIT PURCHASE INVOICE ROUTES =====

@api_router.post("/admin/credit-invoices")
async def create_credit_invoice(invoice_data: CreditInvoiceCreate, request: Request):
    """Create a credit purchase invoice (admin only)"""
    admin = await get_admin_user(request)
    
    # Get user details
    user = await db.users.find_one({"user_id": invoice_data.user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate invoice ID: HHJ-INV-[Date]-[ID]
    date_str = datetime.now(timezone.utc).strftime('%Y%m%d')
    # Get count of invoices today for sequential numbering
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = await db.credit_invoices.count_documents({
        "created_at": {"$gte": today_start.isoformat()}
    })
    invoice_id = f"HHJ-INV-{date_str}-{str(today_count + 1).zfill(3)}"
    
    # Process line items and calculate totals
    processed_items = []
    subtotal = 0
    
    for item in invoice_data.line_items:
        line_total = item.quantity * item.unit_price
        processed_items.append({
            "flavor": item.flavor,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "line_total": line_total,
            "status": item.status
        })
        subtotal += line_total
    
    # Create invoice document
    invoice_doc = {
        "invoice_id": invoice_id,
        "user_id": invoice_data.user_id,
        "customer_name": user.get("name", ""),
        "customer_email": user.get("email", ""),
        "customer_phone": user.get("phone", ""),
        "billing_period_start": invoice_data.billing_period_start,
        "billing_period_end": invoice_data.billing_period_end,
        "line_items": processed_items,
        "subtotal": subtotal,
        "total_amount": subtotal,
        "status": "unpaid",
        "notes": invoice_data.notes,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": admin.get("name", admin.get("email", "Admin")),
        # Company details for invoice
        "company_email": "contact@myhappyhour.co.ke",
        "payment_method": "Airtel Money",
        "payment_number": "0733878020"
    }
    
    await db.credit_invoices.insert_one(invoice_doc)
    
    return await db.credit_invoices.find_one({"invoice_id": invoice_id}, {"_id": 0})

@api_router.get("/admin/credit-invoices")
async def get_credit_invoices(request: Request, user_id: Optional[str] = None):
    """Get all credit invoices (admin only)"""
    await get_admin_user(request)
    
    query = {}
    if user_id:
        query["user_id"] = user_id
    
    invoices = await db.credit_invoices.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return invoices

@api_router.get("/admin/credit-invoices/{invoice_id}")
async def get_credit_invoice(invoice_id: str, request: Request):
    """Get a specific credit invoice (admin only)"""
    await get_admin_user(request)
    
    invoice = await db.credit_invoices.find_one({"invoice_id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return invoice

@api_router.put("/admin/credit-invoices/{invoice_id}/status")
async def update_credit_invoice_status(invoice_id: str, request: Request):
    """Update credit invoice status (admin only)"""
    await get_admin_user(request)
    
    body = await request.json()
    new_status = body.get("status", "unpaid")
    
    if new_status not in ["paid", "partial", "unpaid"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    result = await db.credit_invoices.update_one(
        {"invoice_id": invoice_id},
        {"$set": {"status": new_status}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return {"message": f"Invoice status updated to {new_status}"}

@api_router.put("/admin/credit-invoices/{invoice_id}/line-item/{item_index}/status")
async def update_line_item_status(invoice_id: str, item_index: int, request: Request):
    """Update individual line item status (admin only)"""
    await get_admin_user(request)
    
    body = await request.json()
    new_status = body.get("status", "unpaid")
    
    if new_status not in ["paid", "unpaid"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    invoice = await db.credit_invoices.find_one({"invoice_id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    line_items = invoice.get("line_items", [])
    if item_index < 0 or item_index >= len(line_items):
        raise HTTPException(status_code=400, detail="Invalid line item index")
    
    line_items[item_index]["status"] = new_status
    
    # Recalculate overall status
    all_paid = all(item.get("status") == "paid" for item in line_items)
    any_paid = any(item.get("status") == "paid" for item in line_items)
    
    if all_paid:
        overall_status = "paid"
    elif any_paid:
        overall_status = "partial"
    else:
        overall_status = "unpaid"
    
    await db.credit_invoices.update_one(
        {"invoice_id": invoice_id},
        {"$set": {"line_items": line_items, "status": overall_status}}
    )
    
    return await db.credit_invoices.find_one({"invoice_id": invoice_id}, {"_id": 0})

@api_router.delete("/admin/credit-invoices/{invoice_id}")
async def delete_credit_invoice(invoice_id: str, request: Request):
    """Delete a credit invoice (admin only)"""
    await get_admin_user(request)
    
    result = await db.credit_invoices.delete_one({"invoice_id": invoice_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return {"message": "Invoice deleted"}

@api_router.get("/admin/user-credit-history/{user_id}")
async def get_user_credit_history(user_id: str, request: Request, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Get user's credit purchase history for invoice generation (admin only)"""
    await get_admin_user(request)
    
    query = {
        "user_id": user_id,
        "payment_method": "credit"
    }
    
    if start_date or end_date:
        query["created_at"] = {}
        if start_date:
            query["created_at"]["$gte"] = start_date
        if end_date:
            query["created_at"]["$lte"] = end_date
    
    orders = await db.orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    # Aggregate by flavor
    flavor_totals = {}
    for order in orders:
        for item in order.get("items", []):
            flavor = item.get("product_name", "").replace("Happy Hour Jaba - ", "")
            qty = item.get("quantity", 0)
            if flavor in flavor_totals:
                flavor_totals[flavor] += qty
            else:
                flavor_totals[flavor] = qty
    
    return {
        "orders": orders,
        "flavor_summary": flavor_totals,
        "total_orders": len(orders),
        "total_amount": sum(o.get("total_amount", 0) for o in orders)
    }

# ===== AUTO INVOICE GENERATION =====

@api_router.post("/admin/auto-generate-invoice/{user_id}")
async def auto_generate_invoice(user_id: str, request: Request):
    """Automatically generate credit invoice from order history (admin only)"""
    admin = await get_admin_user(request)
    
    body = await request.json()
    start_date = body.get("start_date")
    end_date = body.get("end_date")
    
    if not start_date or not end_date:
        raise HTTPException(status_code=400, detail="Start and end dates are required")
    
    # Get user
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get credit orders in date range
    orders = await db.orders.find({
        "user_id": user_id,
        "payment_method": "credit",
        "status": {"$ne": "cancelled"},
        "created_at": {"$gte": start_date, "$lte": end_date}
    }, {"_id": 0}).sort("created_at", 1).to_list(1000)
    
    if not orders:
        raise HTTPException(status_code=404, detail="No credit orders found in the specified date range")
    
    # Build line items from orders
    line_items = []
    for order in orders:
        for item in order.get("items", []):
            flavor = item.get("product_name", "").replace("Happy Hour Jaba - ", "")
            line_items.append({
                "flavor": flavor,
                "quantity": item.get("quantity", 0),
                "unit_price": item.get("price", UNIT_PRICE),
                "line_total": item.get("quantity", 0) * item.get("price", UNIT_PRICE),
                "status": "unpaid",
                "order_id": order.get("order_id"),
                "order_date": order.get("created_at")
            })
    
    # Generate invoice ID
    date_str = datetime.now(timezone.utc).strftime('%Y%m%d')
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = await db.credit_invoices.count_documents({
        "created_at": {"$gte": today_start.isoformat()}
    })
    invoice_id = f"HHJ-INV-{date_str}-{str(today_count + 1).zfill(3)}"
    
    # Calculate total
    total_amount = sum(item["line_total"] for item in line_items)
    
    # Create invoice
    invoice_doc = {
        "invoice_id": invoice_id,
        "user_id": user_id,
        "customer_name": user.get("name", ""),
        "customer_email": user.get("email", ""),
        "customer_phone": user.get("phone", ""),
        "billing_period_start": start_date,
        "billing_period_end": end_date,
        "line_items": line_items,
        "subtotal": total_amount,
        "total_amount": total_amount,
        "status": "unpaid",
        "notes": f"Auto-generated from {len(orders)} orders",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": admin.get("name", admin.get("email", "Admin")),
        "company_email": "contact@myhappyhour.co.ke",
        "company_location": "Nairobi",
        "payment_method": "Airtel Money",
        "payment_number": "0733878020",
        "auto_generated": True
    }
    
    await db.credit_invoices.insert_one(invoice_doc)
    
    return await db.credit_invoices.find_one({"invoice_id": invoice_id}, {"_id": 0})

# ===== FEEDBACK & NOTIFICATIONS =====

@api_router.post("/feedback")
async def submit_feedback(feedback: FeedbackCreate, request: Request):
    """Submit feedback to admin"""
    user = await get_current_user(request)
    
    feedback_doc = {
        "feedback_id": f"FB-{uuid.uuid4().hex[:8].upper()}",
        "user_id": user["user_id"],
        "user_name": user.get("name", ""),
        "user_email": user.get("email", ""),
        "subject": feedback.subject or "General Feedback",
        "message": feedback.message,
        "status": "new",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.feedback.insert_one(feedback_doc)
    
    return {"message": "Feedback submitted successfully", "feedback_id": feedback_doc["feedback_id"]}

@api_router.get("/admin/feedback")
async def get_all_feedback(request: Request):
    """Get all feedback (admin only)"""
    await get_admin_user(request)
    feedback = await db.feedback.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return feedback

@api_router.post("/admin/notifications")
async def create_notification(notification: NotificationCreate, request: Request):
    """Create notification/push offer (admin only)"""
    admin = await get_admin_user(request)
    
    notification_id = f"NOTIF-{uuid.uuid4().hex[:8].upper()}"
    
    if notification.target_users:
        # Send to specific users
        for user_id in notification.target_users:
            await db.notifications.insert_one({
                "notification_id": notification_id,
                "user_id": user_id,
                "title": notification.title,
                "message": notification.message,
                "notification_type": notification.notification_type,
                "read": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": admin.get("name", admin.get("email"))
            })
    else:
        # Broadcast to all users
        users = await db.users.find({"role": "user"}, {"user_id": 1, "_id": 0}).to_list(10000)
        for user in users:
            await db.notifications.insert_one({
                "notification_id": notification_id,
                "user_id": user["user_id"],
                "title": notification.title,
                "message": notification.message,
                "notification_type": notification.notification_type,
                "read": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": admin.get("name", admin.get("email"))
            })
    
    return {"message": "Notification created", "notification_id": notification_id}

@api_router.get("/notifications")
async def get_user_notifications(request: Request):
    """Get user's notifications"""
    user = await get_current_user(request)
    notifications = await db.notifications.find(
        {"user_id": user["user_id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return notifications

@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, request: Request):
    """Mark notification as read"""
    user = await get_current_user(request)
    await db.notifications.update_many(
        {"notification_id": notification_id, "user_id": user["user_id"]},
        {"$set": {"read": True}}
    )
    return {"message": "Notification marked as read"}

@api_router.get("/notifications/unread-count")
async def get_unread_count(request: Request):
    """Get count of unread notifications"""
    user = await get_current_user(request)
    count = await db.notifications.count_documents({
        "user_id": user["user_id"],
        "read": False
    })
    return {"unread_count": count}

# ===== USER DASHBOARD STATS =====

@api_router.get("/users/dashboard-stats")
async def get_user_dashboard_stats(request: Request):
    """Get user dashboard statistics"""
    user = await get_current_user(request)
    
    # Get credit orders
    credit_orders = await db.orders.find({
        "user_id": user["user_id"],
        "payment_method": "credit",
        "status": {"$ne": "cancelled"}
    }, {"_id": 0}).to_list(1000)
    
    # Get invoices for this user
    invoices = await db.credit_invoices.find({
        "user_id": user["user_id"]
    }, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    # Calculate stats
    total_pending = sum(o.get("total_amount", 0) for o in credit_orders if o.get("status") == "pending")
    total_owed = MONTHLY_CREDIT_LIMIT - user.get("credit_balance", MONTHLY_CREDIT_LIMIT)
    paid_invoices = [inv for inv in invoices if inv.get("status") == "paid"]
    unpaid_invoices = [inv for inv in invoices if inv.get("status") != "paid"]
    
    return {
        "credit_balance": user.get("credit_balance", MONTHLY_CREDIT_LIMIT),
        "monthly_limit": MONTHLY_CREDIT_LIMIT,
        "total_pending": total_pending,
        "total_owed": total_owed if total_owed > 0 else 0,
        "total_orders": len(credit_orders),
        "paid_invoices_count": len(paid_invoices),
        "unpaid_invoices_count": len(unpaid_invoices),
        "invoices": invoices[:5]  # Last 5 invoices
    }

@api_router.get("/users/invoices")
async def get_user_invoices(request: Request):
    """Get invoices for current user"""
    user = await get_current_user(request)
    invoices = await db.credit_invoices.find(
        {"user_id": user["user_id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return invoices

# ===== ROOT ROUTE =====

@api_router.get("/")
async def root():
    return {"message": "HH Jaba Staff Portal API"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await initialize_products()
    logger.info("HH Jaba Staff Portal API started")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
