import os
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import requests
import stripe
from sqlalchemy import create_engine, Column, String, Integer, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Initialize FastAPI
app = FastAPI(title="Translation API", 
             description="Auto-scaling translation service with Stripe subscriptions",
             version="1.0.0")

# CORS (Configure in production!)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Stripe Setup
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# PostgreSQL Database (Railway.app)
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True)
    email = Column(String, nullable=True)
    subscription_plan = Column(String, default="free")
    chars_used = Column(Integer, default=0)
    last_reset = Column(Date, default=datetime.utcnow().date())

Base.metadata.create_all(bind=engine)  # Creates tables

# Pricing Tiers (Euros)
PRICING = {
    "free": {"limit": 500000, "price": 0},
    "basic": {"limit": 1000000, "price": 10},
    "pro": {"limit": 10000000, "price": 15},
    "enterprise": {"limit": float("inf"), "price": 25}
}

# Dependency for DB sessions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Translation Engine (LibreTranslate)
LIBRETRANSLATE_URL = "https://libretranslate.com/translate"

# Helper Functions
def check_usage_limit(user_id: str, text: str, db: Session):
    user = db.query(User).filter(User.user_id == user_id).first()
    
    # Auto-create user if new
    if not user:
        user = User(user_id=user_id)
        db.add(user)
        db.commit()
    
    # Reset monthly usage if needed
    if datetime.utcnow().date() > user.last_reset + timedelta(days=30):
        user.chars_used = 0
        user.last_reset = datetime.utcnow().date()
        db.commit()
    
    chars_needed = len(text)
    if user.chars_used + chars_needed > PRICING[user.subscription_plan]["limit"]:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Limit exceeded",
                "upgrade_url": f"/create-checkout?user_id={user_id}",
                "chars_used": user.chars_used,
                "chars_limit": PRICING[user.subscription_plan]["limit"]
            }
        )
    return True

# API Models
class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "en"
    target_lang: str
    user_id: str

# API Endpoints
@app.post("/translate")
async def translate(
    request: TranslateRequest,
    db: Session = Depends(get_db)
):
    # Check usage
    check_usage_limit(request.user_id, request.text, db)
    
    # Call LibreTranslate
    try:
        payload = {
            "q": request.text,
            "source": request.source_lang,
            "target": request.target_lang
        }
        response = requests.post(LIBRETRANSLATE_URL, json=payload).json()
        translated_text = response["translatedText"]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "Translation failed", "message": str(e)}
        )
    
    # Update usage
    user = db.query(User).filter(User.user_id == request.user_id).first()
    user.chars_used += len(request.text)
    db.commit()
    
    return {"translation": translated_text}

@app.get("/user-status/{user_id}")
async def get_user_status(
    user_id: str,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail={"error": "User not found"}
        )
    
    return {
        "user_id": user.user_id,
        "plan": user.subscription_plan,
        "chars_used": user.chars_used,
        "chars_left": PRICING[user.subscription_plan]["limit"] - user.chars_used,
        "last_reset": user.last_reset
    }

# Stripe Integration
@app.post("/create-checkout")
async def create_checkout(
    user_id: str,
    plan: str,
    db: Session = Depends(get_db)
):
    if plan not in PRICING:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid plan", "valid_plans": list(PRICING.keys())}
        )
    
    # Ensure user exists
    if not db.query(User).filter(User.user_id == user_id).first():
        db.add(User(user_id=user_id))
        db.commit()
    
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price": os.getenv(f"STRIPE_{plan.upper()}_PRICE_ID"),
                "quantity": 1,
            }],
            mode="subscription",
            success_url=f"{os.getenv('YOUR_DOMAIN')}/success?user_id={user_id}",
            cancel_url=f"{os.getenv('YOUR_DOMAIN')}/cancel",
            metadata={"user_id": user_id}
        )
        return {"checkout_url": checkout_session.url}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "Stripe checkout failed", "message": str(e)}
        )

@app.post("/stripe-webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        return JSONResponse(
            {"error": "Invalid webhook signature", "message": str(e)},
            status_code=400
        )

    if event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        user_id = subscription["metadata"]["user_id"]
        plan = subscription["items"]["data"][0]["plan"]["nickname"].lower()
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if user:
            user.subscription_plan = plan
            db.commit()

    return JSONResponse({"status": "success"})

# Health Check
@app.get("/")
async def health_check():
    return {"status": "active", "message": "Translation API is running"}
