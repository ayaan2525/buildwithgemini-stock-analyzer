"""
Analysis and ranking engine for Stock Market Analyzer.
Processes news, evaluates sentiment, correlates price momentum,
and produces 5 BUY and 5 CAUTIOUS stocks for AI, Chips, and Energy.
"""
from typing import Dict, Any, List, Tuple
from app.config import DOMAINS, POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS
from app.services.news_service import fetch_domain_news
from app.services.market_service import get_quotes_batch
from app.database import save_run

def extract_catalysts_and_risks(articles: List[Dict[str, Any]], ticker: str) -> Tuple[List[str], List[str]]:
    """Extract concrete catalysts and risks from relevant news headlines and snippets."""
    catalysts = []
    risks = []

    for art in articles:
        text = f"{art['title']}. {art['snippet']}"
        text_lower = text.lower()

        # If article mentions this ticker or general sector momentum
        has_pos = any(kw in text_lower for kw in POSITIVE_KEYWORDS)
        has_neg = any(kw in text_lower for kw in NEGATIVE_KEYWORDS)

        # Title is concise and represents the catalyst/risk well
        title = art['title']
        source = art.get('source', '')
        citation = f"{title} ({source})" if source else title

        if has_pos and not has_neg:
            if citation not in catalysts and len(catalysts) < 3:
                catalysts.append(citation)
        elif has_neg:
            if citation not in risks and len(risks) < 3:
                risks.append(citation)
        elif has_pos and citation not in catalysts and len(catalysts) < 3:
            catalysts.append(citation)

    return catalysts, risks

def calculate_stock_score(news_sentiment: float, news_count: int, weekly_change: float) -> float:
    """
    Synthesize an overall score between -100 and +100 based on:
    - News sentiment (-1.0 to +1.0)
    - News buzz/volume multiplier
    - 1-week price change percentage
    """
    # Weightings: 60% sentiment/news, 40% 1-week price performance
    # Bound weekly change to [-25%, +25%] for scoring scaling
    clamped_change = max(min(weekly_change, 25.0), -25.0)
    price_score = clamped_change * 2.0  # -50 to +50

    buzz_factor = min(1.0 + (news_count * 0.1), 2.0)
    sentiment_comp = news_sentiment * 50.0 * buzz_factor  # -100 to +100 scaled
    sentiment_comp = max(min(sentiment_comp, 50.0), -50.0)

    total_score = round(sentiment_comp + price_score, 2)
    return total_score

def classify_beginner_risk(ticker: str, weekly_change: float, sentiment_score: float, domain: str) -> Dict[str, str]:
    """Classify volatility and beginner friendliness into easy-to-understand tags."""
    abs_change = abs(weekly_change)
    # Mega-cap established leaders
    core_anchors = {"NVDA", "MSFT", "GOOGL", "AAPL", "AMZN", "TSM", "ASML", "XOM", "CVX", "NEE"}

    if ticker in core_anchors and abs_change < 6.0:
        return {
            "level": "Low",
            "tag": "Core Anchor",
            "color": "emerald",
            "badge": "🟢 Core Anchor",
            "desc": "Industry leader with lower drawdown risk for new stock users."
        }
    elif abs_change > 7.5 or abs(sentiment_score) > 35.0:
        return {
            "level": "High",
            "tag": "Volatile Rollercoaster",
            "color": "rose",
            "badge": "🔴 High Volatility",
            "desc": "High swing momentum; wide price swings, best for experienced traders."
        }
    else:
        return {
            "level": "Moderate",
            "tag": "Growth Swing",
            "color": "amber",
            "badge": "🟡 Growth Swing",
            "desc": "Solid growth trajectory with moderate weekly fluctuations."
        }

def synthesize_domino_chain(domain_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Connect the dots between the 3 domains:
    AI (Demand Driver) -> Chips (Foundry Capacity) -> Energy (Megawatts & Grid)
    """
    ai_top = domain_results.get("AI", {}).get("buy", [{}])[0].get("ticker", "NVDA")
    chips_top = domain_results.get("Chips", {}).get("buy", [{}])[0].get("ticker", "TSM")
    energy_top = domain_results.get("Energy", {}).get("buy", [{}])[0].get("ticker", "CEG")

    return {
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

def analyze_domain(domain_key: str, domain_articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze all candidate stocks in a domain and return:
    - top 5 BUY
    - top 5 CAUTIOUS
    """
    domain_cfg = DOMAINS[domain_key]
    stocks_info = domain_cfg["stocks"]
    tickers = list(stocks_info.keys())

    # 1. Fetch live market quotes for all tickers in this domain
    quotes = get_quotes_batch(tickers)

    # 2. Group articles by ticker
    articles_by_ticker = {t: [] for t in tickers}
    general_domain_articles = []

    for art in domain_articles:
        matched = art.get("matched_tickers", [])
        if matched:
            for t in matched:
                if t in articles_by_ticker:
                    articles_by_ticker[t].append(art)
        else:
            general_domain_articles.append(art)

    # 3. Score every stock in the domain
    stock_evaluations = []

    for ticker, info in stocks_info.items():
        art_list = articles_by_ticker.get(ticker, [])
        # If stock has few specific articles, include general domain articles for context
        eval_articles = art_list if len(art_list) >= 2 else (art_list + general_domain_articles[:2])

        # Calculate average news sentiment
        if art_list:
            avg_sentiment = sum(a.get("sentiment_score", 0.0) for a in art_list) / len(art_list)
        else:
            # Baseline from sector general news
            avg_sentiment = sum(a.get("sentiment_score", 0.0) for a in general_domain_articles[:5]) / max(len(general_domain_articles[:5]), 1)

        quote = quotes.get(ticker, {})
        weekly_change = quote.get("weekly_change_pct") or 0.0
        current_price = quote.get("current_price")

        score = calculate_stock_score(avg_sentiment, len(art_list), weekly_change)
        catalysts, risks = extract_catalysts_and_risks(eval_articles, ticker)

        # Ensure we always provide meaningful context if news is sparse
        if not catalysts:
            catalysts.append(f"Strong sector tailwinds in {domain_cfg['name']} ({info['role']}).")
        if not risks:
            risks.append(f"Valuation multiple scrutiny & sector volatility in {domain_key}.")

        # Generate concise summary
        if score >= 0:
            summary = f"Bullish setup: Weekly return of {weekly_change:+.1f}% with positive {domain_key} news catalysts."
        else:
            summary = f"Cautious outlook: Weekly retreat of {weekly_change:+.1f}% or mixed sentiment headwinds."

        # Risk and Courtroom arguments
        risk_info = classify_beginner_risk(ticker, weekly_change, score, domain_key)
        bull_case = catalysts[0] if catalysts else f"High momentum in {info['role']}."
        bear_case = risks[0] if risks else f"Macro headwind and valuation risk in {domain_key}."

        stock_evaluations.append({
            "ticker": ticker,
            "company_name": info["name"],
            "role": info["role"],
            "sentiment_score": score,
            "current_price": current_price,
            "weekly_change_pct": weekly_change,
            "sparkline": quote.get("sparkline", []),
            "catalysts": catalysts,
            "risks": risks,
            "bull_case": bull_case,
            "bear_case": bear_case,
            "beginner_risk": risk_info,
            "summary": summary,
            "news_count": len(art_list)
        })

    # 4. Sort to pick Top 5 BUY and Top 5 CAUTIOUS
    # Sort descending by score
    sorted_stocks = sorted(stock_evaluations, key=lambda s: s["sentiment_score"], reverse=True)

    # Top 5 positive rated as BUY
    buy_picks = sorted_stocks[:5]
    for idx, p in enumerate(buy_picks, start=1):
        p["rating"] = "BUY"
        p["rank"] = idx

    # Bottom 5 rated as CAUTIOUS (reverse ordered so worst/highest risk is #1 Cautious)
    cautious_picks = sorted_stocks[-5:][::-1]
    for idx, p in enumerate(cautious_picks, start=1):
        p["rating"] = "CAUTIOUS"
        p["rank"] = idx

    return {
        "domain": domain_key,
        "name": domain_cfg["name"],
        "description": domain_cfg["description"],
        "buy": buy_picks,
        "cautious": cautious_picks
    }

def run_full_market_analysis() -> Dict[str, Any]:
    """
    Run complete analysis across AI, Chips, and Energy.
    Saves results to SQLite and returns the complete run payload.
    """
    domain_results = {}
    all_articles = []

    for domain_key in ["AI", "Chips", "Energy"]:
        domain_articles = fetch_domain_news(domain_key)
        all_articles.extend(domain_articles)
        domain_res = analyze_domain(domain_key, domain_articles)
        domain_results[domain_key] = domain_res

    # Synthesize Cross-Domain Domino Chain
    domino_chain = synthesize_domino_chain(domain_results)

    # Construct executive summary
    top_buy_tickers = [domain_results[d]["buy"][0]["ticker"] for d in ["AI", "Chips", "Energy"]]
    top_cautious_tickers = [domain_results[d]["cautious"][0]["ticker"] for d in ["AI", "Chips", "Energy"]]

    summary_text = (
        f"Weekly 7-Day Market Scan: Analyzed latest Google News & price action across AI, Chips, and Energy. "
        f"Top positive momentum leads: {', '.join(top_buy_tickers)}. "
        f"Top cautious alerts: {', '.join(top_cautious_tickers)}. "
        f"Total 30 domain leaders ranked (15 Buy / 15 Cautious). "
        f"{domino_chain['takeaway']}"
    )

    run_id = save_run(summary_text, domain_results, all_articles)

    return {
        "run_id": run_id,
        "summary": summary_text,
        "domino_chain": domino_chain,
        "domains": domain_results,
        "total_articles": len(all_articles)
    }

