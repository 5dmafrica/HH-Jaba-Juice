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
    """Update product stock (admin only)"""
    await get_admin_user(request)
    
    result = await db.products.update_one(
        {"product_id": product_id},
        {"$set": {
            "stock": stock_update.stock,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product = await db.products.find_one({"product_id": product_id}, {"_id": 0})
    return product

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
    
    if total_quantity > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 bottles per order")
    
    # Check daily limit (5 bottles any payment method)
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
    
    if today_bottles + total_quantity > 5:
        raise HTTPException(
            status_code=400, 
            detail=f"Daily limit of 5 bottles reached. You've ordered {today_bottles} today."
        )
    
    # For credit payments, check additional limits
    if order_data.payment_method == "credit":
        # Check credit balance
        if user.get("credit_balance", 0) < total_amount:
            raise HTTPException(
                status_code=400, 
                detail="Insufficient credit balance"
            )
        
        # Check weekly credit limit (5 bottles per week)
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
        
        if week_bottles + total_quantity > 5:
            raise HTTPException(
                status_code=400, 
                detail=f"Weekly credit limit of 5 bottles reached. You've used {week_bottles} on credit this week."
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

@api_router.post("/admin/orders/{order_id}/reject")
async def reject_order(order_id: str, request: Request):
    """Reject an order (admin only)"""
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
async def get_reconciliation(request: Request):
    """Get users with outstanding credit balances (admin only)"""
    await get_admin_user(request)
    
    # Get all users with credit balance used (less than 10000)
    users = await db.users.find(
        {"credit_balance": {"$lt": 10000}},
        {"_id": 0}
    ).to_list(1000)
    
    result = []
    for user in users:
        outstanding = 10000 - user.get("credit_balance", 10000)
        if outstanding > 0:
            orders = await db.orders.find(
                {"user_id": user["user_id"], "payment_method": "credit"},
                {"_id": 0}
            ).sort("created_at", -1).to_list(100)
            
            result.append({
                "user": user,
                "outstanding_balance": outstanding,
                "orders": orders
            })
    
    return result

@api_router.get("/admin/defaulters")
async def get_defaulters(request: Request):
    """Get monthly defaulters with VAT penalties (admin only)"""
    await get_admin_user(request)
    
    # Get users with outstanding balance
    users = await db.users.find(
        {"credit_balance": {"$lt": 10000}},
        {"_id": 0}
    ).to_list(1000)
    
    result = []
    for user in users:
        outstanding = 10000 - user.get("credit_balance", 10000)
        if outstanding > 0:
            vat_penalty = outstanding * 0.16
            total_due = outstanding + vat_penalty
            
            orders = await db.orders.find(
                {"user_id": user["user_id"], "payment_method": "credit", "status": {"$ne": "cancelled"}},
                {"_id": 0}
            ).sort("created_at", -1).to_list(100)
            
            result.append({
                "user": user,
                "original_balance": outstanding,
                "vat_penalty": vat_penalty,
                "total_due": total_due,
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
