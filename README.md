# Trading Intelligence Platform

A production-ready AI-driven market scanning and trading setups platform built with FastAPI, MongoDB, Next.js, and Tailwind CSS.

## 🚀 Features
- **Smart Market Scanning**: Automated scanning of multiple tickers using advanced strategies (Trend Continuation, Pullback, Breakouts, Reversals, High Confluence).
- **Background Engine**: APScheduler periodically analyzes intraday data (every 5 mins) and swing data (daily).
- **Beginner-friendly Dashboard**: Clean, jargon-free UI with ShadCN built for quick decision making.
- **Stock Analysis View**: TradingView charts embedded with automated Trade Plan generation (Entry, Stop Loss, Target).
- **Family Watchlist**: Shared MongoDB-backed watchlist to track setups for monitored stocks.

---

## 🏗️ Prerequisites
- Python 3.10+
- Node.js 18+
- MongoDB Atlas cluster URL

---

## 🛠️ Step-by-Step Setup

### 1. Database Setup
1. Create a free cluster on [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
2. Get your connection string.
3. Replace `<username>` and `<password>` in `backend/.env`.

### 2. Backend Setup (FastAPI)
Open a terminal and navigate to the `backend` folder:
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

Start the backend server:
```bash
uvicorn main:app --reload --port 8000
```
*Note: The APScheduler will automatically start scanning markets in the background on startup.*

### 3. Frontend Setup (Next.js)
Open a new terminal and navigate to the `frontend` folder:
```bash
cd frontend
npm install
```

Start the frontend development server:
```bash
npm run dev
```

### 4. Open the Application
Navigate to [http://localhost:3000](http://localhost:3000) in your browser. All API requests point to `http://localhost:8000` by default.

---

## 📂 Architecture Overview
- **`backend/data_fetcher.py`**: Integration with `yfinance` to pull historical and real-time interval data.
- **`backend/indicators.py`**: Computes EMA, VWAP, RSI, ATR limits.
- **`backend/strategies.py`**: Defines exact logic for triggering stock setups based on structure.
- **`backend/signal_engine.py`**: Loops through provided symbols, analyzes using strategies, builds Risk-Reward variables, assigns Smart Score (1-10 level).
- **`frontend/src/store/useStore.ts`**: Zustand state handling timeframe toggling and real-time dashboard data caching.
- **`frontend/src/app`**: Next.js App router containing Pages and Dashboards.
