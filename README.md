# 🌍 Translation API with Tiered Subscriptions

A scalable translation API with **auto-user creation** and **Stripe-powered subscriptions**. Supports 200+ languages via LibreTranslate/NLLB.

## ✨ Features
- ✅ **No registration needed** (users auto-created on first request)
- ✅ **Tiered rate-limiting** (Free to Enterprise plans)
- ✅ **Stripe subscriptions** (one-click upgrades)
- ✅ **Real-time usage tracking** (`/user-status` endpoint)
- ✅ **Self-hostable** or deploy on Railway/Heroku

---

## 📊 Subscription Plans

| Plan         | Price (€/mo) | Character Limit | Key Features               |
|--------------|--------------|-----------------|----------------------------|
| **Free**     | €0           | 500,000         | Basic translations         |
| **Basic**    | €10          | 1,000,000       | Higher volume needs        |
| **Pro**      | €15          | 10,000,000      | For small businesses       |
| **Enterprise**| €25         | Unlimited       | Priority support           |

🔹 **All plans reset monthly**  
🔹 **Overages blocked** (upgrade required)

---

## 🚀 Quick Start

### 1. Get Started (No API Key Needed)
Just include a **unique `user_id`** in requests (e.g., email/UUID).  
Example: `"user_id": "alice@example.com"`

### 2. Translate Text
**Endpoint**: `POST /translate`  
**Request**:
```bash
curl -X POST "https://your-api.up.railway.app/translate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world",
    "target_lang": "es",
    "user_id": "alice@example.com"
  }'
