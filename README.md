# 🚀 Trading Intelligence Platform

A **production-ready, multi-market Trading Intelligence System** designed to help traders identify high-probability setups for **intraday and swing trading**.

> ⚡ This is NOT a trading platform (no buy/sell).
> It is a **decision engine** that scans markets and shows the best opportunities.

---

# 🧠 What This Platform Does

* Scans **India 🇮🇳, USA 🇺🇸, Crypto 🪙, Commodities 🛢**
* Detects trading setups automatically
* Shows **Top Opportunities (not cluttered data)**
* Explains **WHY a stock is selected**
* Supports **intraday + swing trading**
* Uses **pattern detection (VCP, Rocket Base, Breakouts, etc.)**

---

# 🔥 Key Features

## 📊 Smart Dashboard

* Market status (Open / Closed)
* India & US time display
* Top 5 opportunities per market
* Sector strength overview

---

## 🌍 Multi-Market Support

* 🇮🇳 India (NSE stocks like RELIANCE.NS)
* 🇺🇸 USA (AAPL, TSLA, etc.)
* 🪙 Crypto (BTC-USD, ETH-USD)
* 🛢 Commodities (Gold, Silver)

---

## 📈 Strategy-Based Analysis (Not Indicators)

* Trend Continuation
* Pullback Setups
* Breakout Scanner
* Reversal Detection
* High Confluence (Best setups only)

---

## 🧠 Pattern Detection (Advanced)

* VCP (Volatility Contraction Pattern)
* Rocket Base Pattern
* Breakout structures
* Volume + consolidation logic

---

## 🔍 Stock Detail Page

When you click a stock:

* TradingView chart
* Entry / Stop Loss / Target
* Risk-Reward
* Pattern explanation
* Probability insight

---

## ⚡ Near Real-Time Updates

* Backend updates every **1–5 minutes**
* Auto-refresh frontend
* Optimized for trading (not HFT)

---

## 🔔 Alerts (Extendable)

* Breakout alerts
* Pullback alerts
* Trend alerts

---

## ⭐ Watchlist

* Family watchlist
* Track selected stocks
* Focused signals

---

# 🏗 Tech Stack

### Frontend

* Next.js (TypeScript)
* Tailwind CSS + ShadCN UI

### Backend

* FastAPI (Python)
* Pandas, NumPy
* Technical Analysis (TA)
* APScheduler

### Database

* MongoDB (Atlas)

---

# 📁 Project Structure

```id="proj-struct"
tradingplatform/
 ├── backend/
 │    ├── main.py
 │    ├── database.py
 │    ├── services/
 │    ├── requirements.txt
 │    └── venv/
 │
 ├── frontend/
 │    ├── app/
 │    ├── components/
 │    ├── package.json
 │    └── next.config.js
```

---

# 🚀 How to Run Locally (Step-by-Step)

Follow carefully 👇

---

## 🟢 1️⃣ Setup Backend

### Step 1: Go to backend

```bash id="b1"
cd tradingplatform/backend
```

---

### Step 2: Create virtual environment

```bash id="b2"
python -m venv venv
```

---

### Step 3: Activate venv

#### Windows (Git Bash):

```bash id="b3"
source venv/Scripts/activate
```

#### Windows (CMD):

```bash id="b4"
venv\Scripts\activate
```

---

### Step 4: Install dependencies

```bash id="b5"
pip install -r requirements.txt
```

---

### Step 5: Run backend server

```bash id="b6"
uvicorn main:app --reload
```

---

### Step 6: Verify backend

Open:

👉 http://localhost:8000/docs

If you see API docs → ✅ Backend is working

---

## 🟡 2️⃣ Setup Frontend

Open a new terminal:

```bash id="f1"
cd tradingplatform/frontend
```

---

### Install dependencies

```bash id="f2"
npm install
```

---

### Run frontend

```bash id="f3"
npm run dev
```

---

### Open app

👉 http://localhost:3000

---

## 🔵 3️⃣ Setup MongoDB

### Option A (Recommended)

Use MongoDB Atlas:

1. Create free cluster
2. Get connection string
3. Add to `.env` file

Example:

```env id="env1"
MONGO_URI=your_mongodb_connection_string
```

---

### Option B (Local MongoDB)

Run:

```bash id="m1"
mongod
```

---

# 🔗 How System Works

```id="flow"
Frontend (Next.js)
        ↓
Backend (FastAPI)
        ↓
MongoDB (Database)
        ↓
Market APIs (yfinance)
```

---

# ⚠️ Important Notes

* This app is for **analysis only**
* Always verify signals before trading
* Market data may have slight delay
* Not suitable for high-frequency trading

---

# 🧠 Philosophy

> “Don’t look at 100 charts…
> Let the system tell you the best 5.”

---

# 🔮 Future Scope

* Options (F&O) integration
* OI & IV analysis
* AI trade explanations
* Telegram / WhatsApp alerts

---

# 👨‍💻 Author

Built for personal & family trading system.

Follow for more:

👉 https://instagram.com/neelsheth2007

---

# ⭐ Final Thought

> Traders look at charts.
> Builders create systems that scan charts.

---
