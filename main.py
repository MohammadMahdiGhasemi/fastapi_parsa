from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from bson import ObjectId
from pymongo import MongoClient
from passlib.context import CryptContext
from typing import List, Optional
import secrets
import datetime

# --- App Configuration ---
app = FastAPI()

# MongoDB connection information
MONGO_URI = ""
client = MongoClient(MONGO_URI)
db = client['']

# --- Templates ---
templates = Jinja2Templates(directory="templates")

# --- Password Hashing ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# --- Models ---
class User(BaseModel):
    id: Optional[str]
    username: str
    password: str

class CustomerRegistrationForm(BaseModel):
    name: str
    email: str
    phone: str

class Product(BaseModel):
    name: str
    brand: str
    price: int
    category: str
    size: str
    gender: str
    stock: int
    rating: Optional[int]
    notes: Optional[str]
    image_url: Optional[str]

# --- Routes ---
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(email: str = Form(...), phone: str = Form(...)):
    user = db.Customers.find_one({"email": email})
    if user and user["phone"] == phone:
        return RedirectResponse(url="/home", status_code=302)
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/home", response_class=HTMLResponse)
async def home(request: Request):
    products = list(db.Products.find())
    return templates.TemplateResponse("index.html", {"request": request, "products": products})

@app.get("/product/{product_id}", response_class=HTMLResponse)
async def product_detail(request: Request, product_id: str):
    product = db.Products.find_one({"_id": ObjectId(product_id)})
    return templates.TemplateResponse("product_detail.html", {"request": request, "product": product})

@app.post("/register")
async def register(form: CustomerRegistrationForm):
    existing_user = db.Customers.find_one({"email": form.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    customer = {
        "name": form.name,
        "email": form.email,
        "phone": form.phone,
        "registration_date": str(datetime.datetime.now())
    }
    db.Customers.insert_one(customer)
    return RedirectResponse(url="/login", status_code=302)

@app.post("/add_to_cart/{product_id}")
async def add_to_cart(product_id: str, quantity: int = Form(...)):
    product = db.Products.find_one({"_id": ObjectId(product_id)})
    if product:
        # Simulating a session cart
        return {"message": "Added to cart", "product_id": product_id, "quantity": quantity}
    raise HTTPException(status_code=404, detail="Product not found")

@app.get("/cart", response_class=HTMLResponse)
async def view_cart(request: Request):
    # Example implementation
    cart = []  # Fetch cart from session or database
    total_price = sum(item["price"] * item["quantity"] for item in cart)
    return templates.TemplateResponse("checkout.html", {"request": request, "cart_details": cart, "total_price": total_price})

@app.post("/checkout")
async def checkout():
    # Example implementation
    cart = []  # Fetch cart from session or database
    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty")

    order = {
        "customer_id": "example_customer_id",
        "products": cart,
        "total_price": sum(item["price"] * item["quantity"] for item in cart),
        "order_date": str(datetime.datetime.now()),
        "status": "pending"
    }
    db.Orders.insert_one(order)
    return {"message": "Order placed successfully"}


@app.get("/aggregations", response_class=HTMLResponse)
async def aggregations(request: Request):
    return templates.TemplateResponse("aggregations.html", {"request": request})
# --- Aggregations ---
@app.get("/aggregation/top_rated_products")
async def top_rated_products():
    pipeline = [
        {"$match": {"rating": {"$gte": 4}}},
        {"$sort": {"rating": -1}},
        {"$limit": 10}
    ]
    results = list(db.Products.aggregate(pipeline))
    return results

@app.get("/aggregation/low_stock_products")
async def low_stock_products():
    pipeline = [
        {"$match": {"stock": {"$lte": 5}}},
        {"$sort": {"stock": 1}}
    ]
    results = list(db.Products.aggregate(pipeline))
    return results

@app.get("/aggregation/category_sales")
async def category_sales():
    pipeline = [
        {"$group": {"_id": "$category", "total_sales": {"$sum": "$price"}}},
        {"$sort": {"total_sales": -1}}
    ]
    results = list(db.Products.aggregate(pipeline))
    return results

@app.get("/aggregation/popular_brands")
async def popular_brands():
    pipeline = [
        {"$group": {"_id": "$brand", "product_count": {"$sum": 1}}},
        {"$sort": {"product_count": -1}},
        {"$limit": 5}
    ]
    results = list(db.Products.aggregate(pipeline))
    return results

@app.get("/aggregation/daily_sales")
async def daily_sales():
    pipeline = [
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$order_date"}}, "total_sales": {"$sum": "$total_price"}}},
        {"$sort": {"_id": -1}}
    ]
    results = list(db.Orders.aggregate(pipeline))
    return results

@app.get("/aggregation/recent_orders")
async def recent_orders():
    pipeline = [
        {"$sort": {"order_date": -1}},
        {"$limit": 10}
    ]
    results = list(db.Orders.aggregate(pipeline))
    return results

@app.get("/aggregation/customer_order_count")
async def customer_order_count():
    pipeline = [
        {"$group": {"_id": "$customer_id", "order_count": {"$sum": 1}}},
        {"$sort": {"order_count": -1}},
        {"$limit": 10}
    ]
    results = list(db.Orders.aggregate(pipeline))
    return results

@app.get("/aggregation/top_spending_customers")
async def top_spending_customers():
    pipeline = [
        {"$group": {"_id": "$customer_id", "total_spent": {"$sum": "$total_price"}}},
        {"$sort": {"total_spent": -1}},
        {"$limit": 10}
    ]
    results = list(db.Orders.aggregate(pipeline))
    return results

@app.get("/aggregation/product_count_by_category")
async def product_count_by_category():
    pipeline = [
        {"$group": {"_id": "$category", "product_count": {"$sum": 1}}},
        {"$sort": {"product_count": -1}}
    ]
    results = list(db.Products.aggregate(pipeline))
    return results

@app.get("/aggregation/total_price_by_brand")
async def total_price_by_brand():
    pipeline = [
        {"$group": {"_id": "$brand", "total_price": {"$sum": "$price"}}},
        {"$sort": {"total_price": -1}}
    ]
    results = list(db.Products.aggregate(pipeline))
    return results

@app.get("/aggregation/average_price_by_category")
async def average_price_by_category():
    pipeline = [
        {"$group": {"_id": "$category", "average_price": {"$avg": "$price"}}},
        {"$sort": {"average_price": -1}}
    ]
    results = list(db.Products.aggregate(pipeline))
    return results

@app.get("/aggregation/order_count_by_customer")
async def order_count_by_customer():
    pipeline = [
        {"$group": {"_id": "$customer_id", "order_count": {"$sum": 1}}},
        {"$sort": {"order_count": -1}}
    ]
    results = list(db.Orders.aggregate(pipeline))
    return results

@app.get("/aggregation/daily_sales_total")
async def daily_sales_total():
    pipeline = [
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$order_date"}}, "total_sales": {"$sum": "$total_price"}}},
        {"$sort": {"_id": -1}}
    ]
    results = list(db.Orders.aggregate(pipeline))
    return results
   
