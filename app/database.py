"""
SQLite database persistence for Stock Market Analyzer.
Stores historical runs, rankings (Buy / Cautious), news articles, and chat history.
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Runs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            summary TEXT,
            total_stocks INTEGER DEFAULT 0
        )
    """)

    # Rankings table: 5 positive (BUY) and 5 negative (CAUTIOUS) per domain
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rankings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            domain TEXT NOT NULL,
            ticker TEXT NOT NULL,
            company_name TEXT NOT NULL,
            rating TEXT NOT NULL,           -- 'BUY' or 'CAUTIOUS'
            rank INTEGER NOT NULL,             -- 1 to 5
            sentiment_score REAL NOT NULL,
            current_price REAL,
            weekly_change_pct REAL,
            catalysts_json TEXT,            -- list of strings
            risks_json TEXT,                -- list of strings
            summary TEXT,
            FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE
        )
    """)

    # News articles table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            domain TEXT NOT NULL,
            ticker TEXT,
            title TEXT NOT NULL,
            source TEXT,
            url TEXT,
            published_at TEXT,
            snippet TEXT,
            sentiment TEXT,
            FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE
        )
    """)

    # Chat history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL
        )
    """)

    # User Portfolio & Long-term Memory table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_portfolio (
            ticker TEXT PRIMARY KEY,
            company_name TEXT NOT NULL,
            domain TEXT NOT NULL,
            shares REAL DEFAULT 1.0,
            added_at TEXT NOT NULL,
            notes TEXT
        )
    """)

    conn.commit()
    conn.close()

def save_run(summary: str, domain_results: Dict[str, Dict[str, Any]], all_articles: List[Dict[str, Any]]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.utcnow().isoformat() + "Z"

    total_stocks = sum(len(res.get("buy", [])) + len(res.get("cautious", [])) for res in domain_results.values())

    cursor.execute(
        "INSERT INTO runs (timestamp, summary, total_stocks) VALUES (?, ?, ?)",
        (now_str, summary, total_stocks)
    )
    run_id = cursor.lastrowid

    # Insert rankings
    for domain, res in domain_results.items():
        # Top 5 Buy
        for rank_idx, item in enumerate(res.get("buy", []), start=1):
            cursor.execute("""
                INSERT INTO rankings (
                    run_id, domain, ticker, company_name, rating, rank,
                    sentiment_score, current_price, weekly_change_pct,
                    catalysts_json, risks_json, summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, domain, item["ticker"], item["company_name"], "BUY", rank_idx,
                item.get("sentiment_score", 0.0), item.get("current_price"), item.get("weekly_change_pct"),
                json.dumps(item.get("catalysts", [])), json.dumps(item.get("risks", [])), item.get("summary", "")
            ))

        # Top 5 Cautious
        for rank_idx, item in enumerate(res.get("cautious", []), start=1):
            cursor.execute("""
                INSERT INTO rankings (
                    run_id, domain, ticker, company_name, rating, rank,
                    sentiment_score, current_price, weekly_change_pct,
                    catalysts_json, risks_json, summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, domain, item["ticker"], item["company_name"], "CAUTIOUS", rank_idx,
                item.get("sentiment_score", 0.0), item.get("current_price"), item.get("weekly_change_pct"),
                json.dumps(item.get("catalysts", [])), json.dumps(item.get("risks", [])), item.get("summary", "")
            ))

    # Insert articles
    for art in all_articles:
        cursor.execute("""
            INSERT INTO articles (
                run_id, domain, ticker, title, source, url, published_at, snippet, sentiment
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, art.get("domain", ""), art.get("ticker", ""), art.get("title", ""),
            art.get("source", ""), art.get("url", ""), art.get("published_at", ""),
            art.get("snippet", ""), art.get("sentiment", "neutral")
        ))

    conn.commit()
    conn.close()
    return run_id

def get_runs_list(limit: int = 30) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, summary, total_stocks FROM runs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_run_details(run_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, timestamp, summary, total_stocks FROM runs WHERE id = ?", (run_id,))
    run_row = cursor.fetchone()
    if not run_row:
        conn.close()
        return None

    run_data = dict(run_row)

    # Get rankings
    cursor.execute("""
        SELECT domain, ticker, company_name, rating, rank, sentiment_score,
               current_price, weekly_change_pct, catalysts_json, risks_json, summary
        FROM rankings WHERE run_id = ? ORDER BY domain, rating, rank
    """, (run_id,))
    ranking_rows = cursor.fetchall()

    domains: Dict[str, Dict[str, Any]] = {}
    core_anchors = {"NVDA", "MSFT", "GOOGL", "AAPL", "AMZN", "TSM", "ASML", "XOM", "CVX", "NEE"}

    for r in ranking_rows:
        dom = r["domain"]
        if dom not in domains:
            domains[dom] = {"buy": [], "cautious": []}

        cats = json.loads(r["catalysts_json"] or "[]")
        risks = json.loads(r["risks_json"] or "[]")
        chg = r["weekly_change_pct"] if r["weekly_change_pct"] is not None else 0.0
        score = r["sentiment_score"] if r["sentiment_score"] is not None else 0.0
        ticker = r["ticker"]

        if ticker in core_anchors and abs(chg) < 6.0:
            risk_info = {
                "level": "Low",
                "tag": "Core Anchor",
                "color": "emerald",
                "badge": "🟢 Core Anchor",
                "desc": "Industry leader with lower drawdown risk for new stock users."
            }
        elif abs(chg) > 7.5 or abs(score) > 35.0:
            risk_info = {
                "level": "High",
                "tag": "Volatile Rollercoaster",
                "color": "rose",
                "badge": "🔴 High Volatility",
                "desc": "High swing momentum; wide price swings, best for experienced traders."
            }
        else:
            risk_info = {
                "level": "Moderate",
                "tag": "Growth Swing",
                "color": "amber",
                "badge": "🟡 Growth Swing",
                "desc": "Solid growth trajectory with moderate weekly fluctuations."
            }

        item = {
            "ticker": ticker,
            "company_name": r["company_name"],
            "rating": r["rating"],
            "rank": r["rank"],
            "sentiment_score": score,
            "current_price": r["current_price"],
            "weekly_change_pct": chg,
            "catalysts": cats,
            "risks": risks,
            "bull_case": cats[0] if cats else f"Momentum in {dom} ecosystem.",
            "bear_case": risks[0] if risks else f"Sector multiple risk in {dom}.",
            "beginner_risk": risk_info,
            "summary": r["summary"]
        }
        if r["rating"] == "BUY":
            domains[dom]["buy"].append(item)
        else:
            domains[dom]["cautious"].append(item)

    run_data["domains"] = domains

    # Attach Domino Chain
    ai_top = domains.get("AI", {}).get("buy", [{}])[0].get("ticker", "NVDA") if "AI" in domains and domains["AI"].get("buy") else "NVDA"
    chips_top = domains.get("Chips", {}).get("buy", [{}])[0].get("ticker", "TSM") if "Chips" in domains and domains["Chips"].get("buy") else "TSM"
    energy_top = domains.get("Energy", {}).get("buy", [{}])[0].get("ticker", "CEG") if "Energy" in domains and domains["Energy"].get("buy") else "CEG"

    run_data["domino_chain"] = {
        "title": "The AI-to-Megawatt Domino Chain",
        "steps": [
            {
                "domain": "AI Software & Models",
                "icon": "cpu",
                "lead": f"Hyperscale AI Deployment ({ai_top})",
                "description": "Tech giants commit tens of billions to train and run reasoning-capable frontier AI clusters."
            },
            {
                "domain": "Semiconductors & Hardware",
                "icon": "zap",
                "lead": f"Foundry & Silicon Bottleneck ({chips_top})",
                "description": "Accelerators require advanced packaging (CoWoS) and foundry wafer allocation running at near-100% capacity."
            },
            {
                "domain": "Energy & Power Grid",
                "icon": "battery-charging",
                "lead": f"Gigawatt Baseload Power Surge ({energy_top})",
                "description": "Data centers consume massive electricity, driving 20-year contracts for nuclear and independent power producers."
            }
        ],
        "takeaway": f"Ecosystem Ripple Effect: AI software scaling fuels semiconductor backlogs ({chips_top}), which in turn sparks historic 24/7 power agreements for energy titans ({energy_top})."
    }

    # Get articles
    cursor.execute("""
        SELECT domain, ticker, title, source, url, published_at, snippet, sentiment
        FROM articles WHERE run_id = ? ORDER BY id ASC
    """, (run_id,))
    article_rows = cursor.fetchall()
    run_data["articles"] = [dict(a) for a in article_rows]

    conn.close()
    return run_data

def get_latest_run_details() -> Optional[Dict[str, Any]]:
    runs = get_runs_list(1)
    if not runs:
        return None
    return get_run_details(runs[0]["id"])

def save_chat_message(role: str, content: str):
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.utcnow().isoformat() + "Z"
    cursor.execute("INSERT INTO chat_messages (timestamp, role, content) VALUES (?, ?, ?)", (now_str, role, content))
    conn.commit()
    conn.close()

def get_chat_history(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, role, content FROM chat_messages ORDER BY id ASC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def clear_chat_history():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_messages")
    conn.commit()
    conn.close()

# User Portfolio Memory Operations
def add_to_portfolio(ticker: str, company_name: str, domain: str, shares: float = 1.0, notes: str = "") -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.utcnow().isoformat() + "Z"
    ticker_clean = ticker.upper().strip()
    cursor.execute("""
        INSERT INTO user_portfolio (ticker, company_name, domain, shares, added_at, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(ticker) DO UPDATE SET
            company_name=excluded.company_name,
            domain=excluded.domain,
            shares=excluded.shares,
            added_at=excluded.added_at,
            notes=excluded.notes
    """, (ticker_clean, company_name, domain, shares, now_str, notes))
    conn.commit()
    conn.close()
    return {
        "ticker": ticker_clean,
        "company_name": company_name,
        "domain": domain,
        "shares": shares,
        "added_at": now_str,
        "notes": notes
    }

def remove_from_portfolio(ticker: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_portfolio WHERE ticker = ?", (ticker.upper().strip(),))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_user_portfolio() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ticker, company_name, domain, shares, added_at, notes FROM user_portfolio ORDER BY added_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def clear_user_portfolio():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_portfolio")
    conn.commit()
    conn.close()

# Auto-initialize DB on import
init_db()
