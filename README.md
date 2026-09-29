# 📊 Silicon Pulse — Autonomous AI Market Copilot

> **Track 3 Hackathon Project**: Real-time cross-sector stock intelligence, multi-agent courtroom deliberations, and persistent portfolio diversification memory.

<div align="center">

![Silicon Pulse Demo](demo.gif)

*Watch the 30-second live demonstration above, or download [`stock_analyzer_demo.webm`](stock_analyzer_demo.webm).*

</div>

---

## 🌟 Overview

**Silicon Pulse** is an agentic financial intelligence copilot built to cut through market noise across three hyper-growth, interdependent tech sectors: **AI**, **Semiconductor Chips**, and **Clean Energy**. 

Rather than giving flat predictions, the system employs a **multi-agent deliberation engine** grounded in real-time market data, technical volatility scoring, live financial news, and persistent portfolio memory to protect investors from sector over-concentration.

---

## 🚀 Key Features

### 1. 🤖 Multi-Agent Bull vs. Bear Courtroom
Whenever a user asks about a specific stock (e.g. *"Should I buy Tesla?"*), the system triggers an autonomous debate:
* **🐂 The Bull Agent**: Presents technical momentum, growth catalysts, and upside fundamentals.
* **🐻 The Bear Agent**: Counters with valuation multiples, supply-chain risks, and headwind news citations.
* **⚖️ Chief Risk Officer**: Synthesizes the debate into an impartial, risk-adjusted verdict with clear stop-loss and entry strategies.

### 2. 🧠 Persistent Portfolio Memory & Cross-Sector Diversification
* Remembers user holdings across sessions (e.g., *"I bought Apple"*).
* Detects sector over-concentration across the **AI ➔ Chips ➔ Energy** supply chain.
* Proactively advises users to diversify into unhedged sectors before adding more exposure.

### 3. 🔍 Multi-Domain 7-Day Market Scanner
* Continuously scans NASDAQ & NYSE tickers across AI, Chips, and Energy.
* Computes real-time volatility ratings (`Core Anchor`, `Moderate Risk`, `High Volatility`).
* Feeds live sentiment analysis into a clean, modern dark-mode dashboard.

---

## 🛠️ Tech Stack & Architecture

* **Backend**: FastAPI (Python 3.12+), SQLite for portfolio and news caching.
* **Intelligence Layer**: Gemini 2.5 Flash / Agent Platform, Google Search grounding & live financial RAG.
* **Frontend**: Responsive Tailwind CSS, Lucide icons, interactive Drawer UI.
* **Automated QA & Evaluation**: Multi-turn dialogue intent parser disambiguating portfolio declarations vs. advisory inquiries.

---

## ⚡ Quick Start

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/ayaan2525/buildwithgemini-stock-analyzer.git
cd buildwithgemini-stock-analyzer
pip install -r requirements.txt
```

### 2. Run the App
```bash
./run.sh
```
Or start via uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000` in your browser.

---

## 📹 Demo Video

The repository includes a recorded video demo:
* **Inline Demo**: See `demo.gif` above.
* **High Definition WebM**: [`stock_analyzer_demo.webm`](stock_analyzer_demo.webm)
