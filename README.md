# 🌍 Translation API

**A scalable translation API with tiered subscriptions** Free, Basic, Pro, Enterprise

---

## ✨ Features
- **200+ languages** via LibreTranslate/NLLB
- **Rate-limiting** by character count (Free: 500K/mo)
- **Stripe subscriptions** for paid tiers
- **Self-hostable** or deploy on Railway/Heroku

---

## 🚀 Quick Start

### 1. Get Your API Key
Free tier requires no API key. Just send a `user_id` with requests.

### 2. Translate Text
**Endpoint**: `POST /translate`  
**Headers**: `Content-Type: application/json`  
**Body**:
```json
{
  "text": "Hello world",
  "target_lang": "es",
  "user_id": "your_unique_user_id"
}
