import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import DOMAINS
from app.services.news_service import fetch_domain_news, match_stock_tickers, score_text_sentiment
from app.services.market_service import get_stock_quote, get_quotes_batch
from app.services.analyzer_service import analyze_domain, run_full_market_analysis
from app.database import init_db, get_latest_run_details, get_runs_list, get_connection
from app.services.qa_service import generate_answer

def run_all_tests():
    print("=== [TEST 1] Testing Database Initialization ===")
    init_db()
    conn = get_connection()
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    conn.close()
    assert "runs" in tables, "Table 'runs' missing"
    assert "rankings" in tables, "Table 'rankings' missing"
    assert "articles" in tables, "Table 'articles' missing"
    assert "chat_messages" in tables, "Table 'chat_messages' missing"
    print("Database tables successfully initialized.")

    print("\n=== [TEST 2] Testing News Service & Entity Matching ===")
    test_text = "Nvidia reports record earnings surge as AI chip demand accelerates"
    ai_stocks = DOMAINS["AI"]["stocks"]
    matched = match_stock_tickers(test_text, ai_stocks)
    assert "NVDA" in matched, f"Expected NVDA in matched, got {matched}"
    score = score_text_sentiment(test_text)
    assert score > 0.0, f"Expected positive sentiment score, got {score}"
    print(f"Ticker match and sentiment scored properly: Matched={matched}, Score={score}")

    print("\n=== [TEST 3] Testing Live Google News RSS Ingestion ===")
    ai_news = fetch_domain_news("AI")
    assert len(ai_news) > 0, "Failed to fetch any AI news articles"
    print(f"Successfully fetched {len(ai_news)} Google News articles for AI domain.")
    print(f"Sample Headline: '{ai_news[0]['title']}' (Source: {ai_news[0]['source']})")

    print("\n=== [TEST 4] Testing Market Quote Fetcher ===")
    quote = get_stock_quote("NVDA")
    assert quote["ticker"] == "NVDA"
    print(f"NVDA Quote: Price=${quote['current_price']}, 7d Change={quote['weekly_change_pct']}%")

    print("\n=== [TEST 5] Testing Domain Analysis & 5-Buy / 5-Cautious Ranking ===")
    analysis_res = analyze_domain("AI", ai_news)
    buy_picks = analysis_res["buy"]
    cautious_picks = analysis_res["cautious"]

    assert len(buy_picks) == 5, f"Expected 5 BUY picks, got {len(buy_picks)}"
    assert len(cautious_picks) == 5, f"Expected 5 CAUTIOUS picks, got {len(cautious_picks)}"

    print(f"Top 5 Buy in AI: {[p['ticker'] for p in buy_picks]}")
    print(f"Top 5 Cautious in AI: {[p['ticker'] for p in cautious_picks]}")

    print("\n=== [TEST 6] Testing Full Multi-Domain Run & Persistence ===")
    full_run = run_full_market_analysis()
    run_id = full_run["run_id"]
    assert run_id > 0, "Run ID was not returned"

    stored_run = get_latest_run_details()
    assert stored_run is not None, "Failed to retrieve stored run from SQLite"
    assert "AI" in stored_run["domains"], "AI domain missing in stored run"
    assert "Chips" in stored_run["domains"], "Chips domain missing in stored run"
    assert "Energy" in stored_run["domains"], "Energy domain missing in stored run"

    # Verify each domain has 5 buy and 5 cautious
    for dom in ["AI", "Chips", "Energy"]:
        d_data = stored_run["domains"][dom]
        assert len(d_data["buy"]) == 5, f"{dom} must have 5 buy ratings"
        assert len(d_data["cautious"]) == 5, f"{dom} must have 5 cautious ratings"

    print("Persistent multi-domain rankings verified in SQLite database.")

    print("\n=== [TEST 7] Testing Interactive Q&A Assistant ===")
    ans1 = generate_answer("Why is NVDA rated buy?")
    assert "NVDA" in ans1, "Expected NVDA details in answer"
    print("Q&A Specific Ticker Query: Passed.")

    ans2 = generate_answer("What are the top energy picks?")
    assert "Energy" in ans2 or "Top" in ans2, "Expected energy overview in answer"
    print("Q&A Sector Query: Passed.")

    print("\n All Automated Tests Passed Successfully!")

if __name__ == "__main__":
    run_all_tests()
