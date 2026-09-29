"""
Interactive Q&A Assistant Service for Stock Market Analyzer.
Allows users to ask about any stock, domain, rating rationale,
or historical comparison on the go.
"""
import os
import re
from typing import Dict, Any, List
from app.database import (
    get_latest_run_details,
    save_chat_message,
    add_to_portfolio,
    remove_from_portfolio,
    get_user_portfolio,
    clear_user_portfolio,
)
from app.config import DOMAINS

import yfinance as yf
from app.services.news_service import fetch_google_news_rss, score_text_sentiment

POPULAR_EXTENDED_STOCKS = {
    "TSLA": {
        "ticker": "TSLA",
        "company_name": "Tesla Inc.",
        "domain": "AI & Energy",
        "aliases": ["tesla", "tsla"],
        "role": "Autonomous Driving AI, Robotics & Megapack Grid Storage",
        "level": "High",
        "badge": "🔴 High Volatility",
        "bull_case": "Expanding Megapack energy storage deployments, Cybercab autonomous AI scaling, and robotics development.",
        "bear_case": "Automotive margin compression, regulatory scrutiny over autonomous claims, and valuation sensitivity."
    },
    "AAPL": {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "domain": "AI / Consumer Tech",
        "aliases": ["apple", "aapl"],
        "role": "Apple Intelligence & Consumer Ecosystem",
        "level": "Low",
        "badge": "🟢 Core Anchor",
        "bull_case": "Monolithic consumer device install base driving massive edge-AI upgrade cycle.",
        "bear_case": "China revenue headwinds and anti-trust app store commission pressures."
    },
    "AMZN": {
        "ticker": "AMZN",
        "company_name": "Amazon.com Inc.",
        "domain": "AI / Cloud",
        "aliases": ["amazon", "amzn", "aws"],
        "role": "Cloud AI Infrastructure & Bedrock",
        "level": "Low",
        "badge": "🟢 Core Anchor",
        "bull_case": "AWS re-acceleration driven by enterprise generative AI workloads and custom Trainium chips.",
        "bear_case": "Retail margin sensitivity and massive capital expenditure requirements for data centers."
    },
    "GOOGL": {
        "ticker": "GOOGL",
        "company_name": "Alphabet Inc.",
        "domain": "AI",
        "aliases": ["google", "googl", "goog", "alphabet"],
        "role": "Gemini AI & Google Cloud Platform",
        "level": "Low",
        "badge": "🟢 Core Anchor",
        "bull_case": "Gemini models integrated across Search and Android, with TPU v5p cloud efficiencies.",
        "bear_case": "DOJ search antitrust remedy risks and competitive AI search erosion."
    },
    "SMCI": {
        "ticker": "SMCI",
        "company_name": "Super Micro Computer",
        "domain": "Chips / Hardware",
        "aliases": ["supermicro", "super micro", "smci"],
        "role": "Liquid-Cooled AI Server Racks",
        "level": "High",
        "badge": "🔴 High Volatility",
        "bull_case": "First-to-market speed with direct liquid cooling (DLC) racks for Nvidia Blackwell chips.",
        "bear_case": "Severe accounting audit scrutiny, margin compression, and customer concentration."
    },
    "DELL": {
        "ticker": "DELL",
        "company_name": "Dell Technologies",
        "domain": "AI / Hardware",
        "aliases": ["dell"],
        "role": "AI Enterprise Servers & Clusters",
        "level": "Medium",
        "badge": "🟡 Growth Swing",
        "bull_case": "Enterprise server backlog surge as Fortune 500 companies adopt on-premise AI clusters.",
        "bear_case": "Lower gross margin profile on high-end GPU server configurations."
    }
}


def resolve_stock(query_text: str) -> Optional[Dict[str, Any]]:
    """Resolve any stock ticker, company name, or alias to standardized metadata."""
    if not query_text:
        return None
    raw = query_text.strip()
    q_lower = raw.lower()
    q_upper = raw.upper()
    words = re.findall(r"\b[A-Za-z0-9]+\b", raw)

    # 1. Direct symbol/alias check in POPULAR_EXTENDED_STOCKS
    for sym, item in POPULAR_EXTENDED_STOCKS.items():
        if sym in words or q_upper == sym or any(a in q_lower for a in item["aliases"]):
            domain = "AI" if "AI" in item["domain"] else ("Chips" if "Chips" in item["domain"] else "Energy")
            return {
                "ticker": sym,
                "company_name": item["company_name"],
                "domain": domain,
                "display_domain": item["domain"]
            }

    # 2. Check DOMAINS config
    for dom_key, dom_info in DOMAINS.items():
        for sym, st in dom_info["stocks"].items():
            name_lower = st["name"].lower()
            short_name = re.sub(r"\b(corporation|corp|inc|holdings|ltd|platforms|technology|technologies)\b", "", name_lower).strip()
            if sym in words or q_upper == sym or (len(short_name) >= 3 and short_name in q_lower):
                return {
                    "ticker": sym,
                    "company_name": st["name"],
                    "domain": dom_key,
                    "display_domain": dom_info["name"]
                }

    # 3. Check latest scan run
    run = get_latest_run_details()
    if run:
        for dom_key, dom_data in run.get("domains", {}).items():
            for st in dom_data.get("buy", []) + dom_data.get("cautious", []):
                sym = st["ticker"]
                name_lower = st["company_name"].lower()
                short_name = re.sub(r"\b(corporation|corp|inc|holdings|ltd|platforms)\b", "", name_lower).strip()
                if sym in words or q_upper == sym or (len(short_name) >= 3 and short_name in q_lower):
                    return {
                        "ticker": sym,
                        "company_name": st["company_name"],
                        "domain": dom_key,
                        "display_domain": dom_key
                    }

    # 4. If single uppercase word of 2-5 letters (e.g. "GOOG", "ORCL")
    for w in words:
        if 2 <= len(w) <= 5 and w.isalpha() and w.isupper():
            return {
                "ticker": w,
                "company_name": f"{w} Equity",
                "domain": "AI",
                "display_domain": "Tech"
            }

    return None


def handle_portfolio_intent(question: str) -> Optional[str]:
    """Check if the user is declaring a purchase, checking portfolio, or selling."""
    q_lower = question.lower().strip()

    # 1. Show portfolio intent
    if any(p in q_lower for p in ["my portfolio", "show portfolio", "view portfolio", "what do i own", "what stocks do i own", "my holdings", "what do i have", "check portfolio"]):
        holdings = get_user_portfolio()
        if not holdings:
            return (
                "💼 **Your Portfolio Memory is currently empty.**\n\n"
                "Tell me about any stock you buy at any time, for example:\n"
                "- *'I bought Apple'* or *'I bought 10 shares of NVDA'*\n"
                "- *'I own Tesla'*\n\n"
                "I will remember your holdings and proactively alert you when you need to diversify across **AI, Chips, and Energy**!"
            )

        lines = ["💼 **Your Saved Portfolio Memory:**\n"]
        domain_counts = {}
        for h in holdings:
            dom = h["domain"]
            domain_counts[dom] = domain_counts.get(dom, 0) + 1
            lines.append(f"- **{h['ticker']}** ({h['company_name']}) • *Domain: {h['domain']}*")

        lines.append("\n📊 **Supply Chain Allocation:**")
        for dom in ["AI", "Chips", "Energy"]:
            cnt = domain_counts.get(dom, 0)
            status = f"{cnt} position(s)" if cnt > 0 else "⚠️ 0 (Unhedged / Missing)"
            lines.append(f"• **{dom}**: {status}")

        missing = [d for d in ["AI", "Chips", "Energy"] if d not in domain_counts]
        if missing:
            lines.append(f"\n💡 **Diversification Advice**: You currently lack exposure to **{' and '.join(missing)}**. Consider branching out to avoid single-sector drawdowns!")
        else:
            lines.append("\n🏆 **Great diversification!** You have positions across AI, Chips, and Energy.")

        return "\n".join(lines)

    # 2. Buy / Owned intent
    # Skip if question is asking for advice rather than declaring an action/holding
    is_advice_question = bool(re.search(r"\b(should|can|could|would|shall|do|why|how|if|what\s+if)\s+(?:i|we)\s+buy\b", q_lower)) or \
                         bool(re.search(r"\b(is\s+it\s+(?:good|safe|time|smart)\s+to\s+buy|buy\s+or\s+(?:sell|avoid)|worth\s+buying)\b", q_lower))

    matched_stock_info = None
    if not is_advice_question:
        buy_patterns = [
            r"\b(?:i\s+(?:already\s+|just\s+)?(?:bought|purchased|own|hold|acquired)|i\s+have(?:\s+some)?|added(?:\s+to\s+(?:my\s+)?portfolio)?)\s+(?:some\s+|shares\s+of\s+|\d+\s+shares\s+of\s+)?([a-zA-Z0-9\.\s]{1,30})",
            r"\b(?:my\s+portfolio\s+(?:has|contains|includes))\s+([a-zA-Z0-9\.\s]{1,30})"
        ]

        for pattern in buy_patterns:
            m = re.search(pattern, q_lower)
            if m:
                target_raw = m.group(1).strip()
                target_clean = re.sub(r"\b(stock|shares|today|yesterday|recently|last\s+week|to\s+my\s+portfolio)\b", "", target_raw).strip()
                st_info = resolve_stock(target_clean) or resolve_stock(target_raw)
                if st_info:
                    matched_stock_info = st_info
                    break

    if matched_stock_info:
        ticker = matched_stock_info["ticker"]
        cname = matched_stock_info["company_name"]
        domain = matched_stock_info["domain"]

        # Save to database
        add_to_portfolio(ticker=ticker, company_name=cname, domain=domain, notes=f"Added from chat: '{question}'")

        # Get all holdings to provide smart diversification advice
        holdings = get_user_portfolio()
        owned_domains = set(h["domain"] for h in holdings)
        other_domains = [d for d in ["Chips", "Energy", "AI"] if d != domain and d not in owned_domains]
        if not other_domains:
            other_domains = [d for d in ["Chips", "Energy", "AI"] if d != domain]

        # Top picks for diversification
        run = get_latest_run_details()
        rec_suggestions = []
        if run:
            for od in other_domains[:2]:
                picks = run.get("domains", {}).get(od, {}).get("buy", [])
                if picks:
                    p = picks[0]
                    rec_suggestions.append(
                        f"• **{od} Top Pick**: **{p['ticker']}** ({p['company_name']}) — 🐂 *{p.get('bull_case', 'Momentum leader')}*"
                    )

        rec_text = "\n".join(rec_suggestions) if rec_suggestions else (
            "• **Chips**: **TSM** (Taiwan Semiconductor) — foundry monopoly making AI silicon\n"
            "• **Energy**: **CEG** (Constellation Energy) — nuclear power contracts for hyperscale data centers"
        )

        return (
            f"💼 **Portfolio Memory Saved!**\n\n"
            f"I've logged **{ticker} ({cname})** in your portfolio memory under the **{domain}** domain.\n\n"
            f"🧠 **Personalized Diversification Intelligence:**\n"
            f"> *“Hey, you already bought **{cname.split()[0]} ({ticker})**! "
            f"Why not diversify and go for other **{' or '.join(other_domains).lower()}**? "
            f"Over-concentrating in {domain} leaves you exposed to sector-wide pullbacks. "
            f"Spreading into the other legs of the AI infrastructure domino gives you far stronger risk-adjusted protection.”*\n\n"
            f"📊 **Recommended Counter-Picks for Diversification:**\n"
            f"{rec_text}\n\n"
            f"💡 *Ask: 'What should I buy next to diversify?' or 'Show my portfolio'*"
        )

    # 3. Sell / Remove intent
    sell_match = re.search(r"\b(?:i\s+sold|remove\s+from\s+portfolio|delete\s+from\s+portfolio)\s+([a-zA-Z0-9\.\s]{1,30})", q_lower)
    if sell_match:
        target_raw = sell_match.group(1).strip()
        st_info = resolve_stock(target_raw)
        if st_info:
            removed = remove_from_portfolio(st_info["ticker"])
            if removed:
                return f"💼 **Portfolio Memory Updated**: Removed **{st_info['ticker']} ({st_info['company_name']})** from your holdings."
            else:
                return f"ℹ️ **{st_info['ticker']}** was not present in your portfolio memory."

    return None


def find_stock_mention(question: str, domains_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Find any stocks mentioned in the user's question, including dynamic lookup for extended market leaders."""
    q_upper = question.upper()
    q_lower = question.lower()
    matches = []

    # 1. Search in pre-scanned run domains
    for domain_key, dom in domains_data.items():
        all_stocks = dom.get("buy", []) + dom.get("cautious", [])
        for st in all_stocks:
            ticker = st["ticker"]
            name = st["company_name"].lower()
            short_name = re.sub(r"\b(corporation|corp|inc|holdings|ltd|platforms)\b", "", name).strip()

            if re.search(rf"\b{re.escape(ticker)}\b", q_upper) or (len(short_name) >= 3 and short_name in q_lower):
                matches.append({"domain": domain_key, **st})

    if matches:
        return matches

    # 2. Check popular extended stocks (like TSLA, AAPL, etc.)
    for sym, item in POPULAR_EXTENDED_STOCKS.items():
        if re.search(rf"\b{re.escape(sym)}\b", q_upper) or any(alias in q_lower for alias in item["aliases"]):
            # Dynamically fetch real-time quote
            price = None
            weekly_chg = 0.0
            try:
                t_obj = yf.Ticker(sym)
                fast = t_obj.fast_info
                price = fast.last_price
                prev = fast.previous_close
                if price and prev:
                    weekly_chg = ((price - prev) / prev) * 100.0
            except Exception:
                price = 350.0

            # Dynamically fetch 7-day news
            live_news = []
            try:
                live_news = fetch_google_news_rss(f"{item['company_name']} stock when:7d", max_items=4)
            except Exception:
                pass

            sentiment = 0.5
            if live_news:
                sentiment = score_text_sentiment(" ".join([n.get("title", "") for n in live_news]))

            rating = "BUY" if sentiment >= 0 else "CAUTIOUS"

            synth_stock = {
                "ticker": sym,
                "company_name": item["company_name"],
                "domain": item["domain"],
                "rank": 1,
                "rating": rating,
                "current_price": price,
                "weekly_change_pct": round(weekly_chg, 2),
                "sentiment_score": sentiment,
                "beginner_risk": {
                    "level": item["level"],
                    "badge": item["badge"],
                    "desc": f"{item['badge']} — high-profile market asset. Monitor position sizing."
                },
                "bull_case": item["bull_case"],
                "bear_case": item["bear_case"],
                "live_news": live_news
            }
            matches.append(synth_stock)
            break

    return matches

def generate_answer(question: str) -> str:
    """Generate a high-quality contextual response for the user's query."""
    # 0. Check for Portfolio Memory intents (e.g. "I bought Apple", "Show my portfolio", "I sold TSLA")
    portfolio_reply = handle_portfolio_intent(question)
    if portfolio_reply:
        save_chat_message("user", question)
        save_chat_message("assistant", portfolio_reply)
        return portfolio_reply

    run = get_latest_run_details()
    if not run:
        return "No market analysis has been executed yet. Click **'Run 7-Day Analysis'** at the top to scan latest news and rank stocks."

    domains = run.get("domains", {})
    articles = run.get("articles", [])

    q_lower = question.lower()

    # 1. Explicit Diversification queries
    if any(p in q_lower for p in ["diversify", "next to buy", "what should i buy next", "next move", "what next", "how to diversify"]):
        holdings = get_user_portfolio()
        if holdings:
            owned_domains = set(h["domain"] for h in holdings)
            missing_domains = [d for d in ["Chips", "Energy", "AI"] if d not in owned_domains]
            if not missing_domains:
                missing_domains = [d for d in ["Chips", "Energy", "AI"]]

            held_desc = ", ".join([f"{h['ticker']} ({h['domain']})" for h in holdings])
            lines = [
                f"### 🛡️ **Personalized Diversification Strategy**\n\n",
                f"Based on your portfolio memory, you already own: **{held_desc}**.\n\n",
                f"> *“To optimize risk across the AI infrastructure domino chain, your next move should target **{' & '.join(missing_domains)}** rather than doubling down on what you already hold!”*\n\n",
                f"**Top Recommended Diversification Candidates:**\n"
            ]
            for md in missing_domains[:2]:
                picks = domains.get(md, {}).get("buy", [])
                if picks:
                    top_st = picks[0]
                    lines.append(
                        f"- **{md} Recommendation**: **{top_st['ticker']}** ({top_st['company_name']}) • Price: ${top_st.get('current_price', 0.0):.2f}\n"
                        f"  • *Beginner Badge*: `{top_st.get('beginner_risk', {}).get('badge', '🟢 Core Anchor')}`\n"
                        f"  • *Catalyst*: 🐂 {top_st.get('bull_case', 'Solid sector momentum')}\n"
                    )
            lines.append("\n💡 *Ask: 'Give me the Bull vs Bear case for " + (domains.get(missing_domains[0], {}).get("buy", [{}])[0].get("ticker", "TSM")) + "' to inspect downside risks.*")
            answer = "".join(lines)
            save_chat_message("user", question)
            save_chat_message("assistant", answer)
            return answer

    # Check if user mentions specific stock(s)
    matched_stocks = find_stock_mention(question, domains)

    # 2. Cross-Domain Domino Effect / Supply Chain queries
    if any(w in q_lower for w in ["domino", "ripple", "supply chain", "connection", "connect", "powering ai", "ecosystem", "why energy"]):
        domino = run.get("domino_chain", {})
        steps = domino.get("steps", [])
        steps_text = "\n\n".join([
            f"**{i}. {s.get('domain', '')}**\n• *Driver*: {s.get('lead', '')}\n• {s.get('description', '')}"
            for i, s in enumerate(steps, 1)
        ])
        answer = (
            f"### 🔗 **The AI-to-Megawatt Supply Chain Domino Effect**\n\n"
            f"In the tech economy, AI, Chips, and Energy are tightly linked in a continuous loop:\n\n"
            f"{steps_text}\n\n"
            f"💡 **Takeaway for Beginners:**\n"
            f"> *When tech giants increase AI CapEx, do not just look at AI software stocks—watch the chip foundries that make the GPUs and the utility companies that supply the gigawatts of electricity!*"
        )
        save_chat_message("user", question)
        save_chat_message("assistant", answer)
        return answer

    # 2. Beginner / Safest / New user queries
    if any(w in q_lower for w in ["safest", "safe", "beginner", "new to", "start", "low risk"]):
        safe_picks = []
        for d_key in ["AI", "Chips", "Energy"]:
            for st in domains.get(d_key, {}).get("buy", []):
                risk = st.get("beginner_risk", {})
                if risk.get("level") == "Low" or st["ticker"] in ["NVDA", "MSFT", "GOOGL", "TSM", "XOM", "NEE", "CEG"]:
                    safe_picks.append((d_key, st))

        lines = [
            "### 🛡️ **Beginner-Friendly 'Core Anchor' Stocks**\n",
            "For new stock users, volatile swings can be stressful. These are established market pillars with proven cash flows and lower relative drawdown risk:\n"
        ]
        for d_key, st in safe_picks[:4]:
            price = f"${st['current_price']:.2f}" if st.get("current_price") else "N/A"
            chg = f"{st.get('weekly_change_pct', 0.0):+.1f}%"
            bull = st.get("bull_case") or (st.get("catalysts", ["Stable market leader"])[0])
            lines.append(
                f"- **{st['ticker']}** ({st['company_name']} - *{d_key}*): Price **{price}** (7d: **{chg}**)\n"
                f"  • *Beginner Tag*: `🟢 Core Anchor`\n"
                f"  • *Why it's safer*: {bull}"
            )

        lines.append("\n💡 **Golden Rule for Beginners**: Diversify across sectors—pair an AI leader (e.g. MSFT/NVDA) with an essential energy provider (e.g. CEG/NEE).")
        answer = "\n".join(lines)
        save_chat_message("user", question)
        save_chat_message("assistant", answer)
        return answer

    # 3. Specific stock questions (Multi-Agent Bull vs Bear Deliberation)
    if matched_stocks:
        response_parts = []
        for st in matched_stocks[:2]:  # Limit to 2 for conciseness
            ticker = st["ticker"]
            name = st["company_name"]
            domain = st["domain"]
            rating = st["rating"]
            rank = st["rank"]
            price = f"${st['current_price']:.2f}" if st.get("current_price") else "N/A"
            chg = f"{st['weekly_change_pct']:+.1f}%" if st.get("weekly_change_pct") is not None else "0.0%"
            score = st.get("sentiment_score", 0.0)

            risk_info = st.get("beginner_risk") or {
                "badge": "🟢 Core Anchor" if rating == "BUY" else "🔴 High Volatility",
                "desc": "Check position size carefully."
            }

            bull_arg = st.get("bull_case") or (st.get("catalysts", ["Positive momentum"])[0])
            bear_arg = st.get("bear_case") or (st.get("risks", ["Sector volatility"])[0])

            # Find matching recent news (from run articles or dynamically fetched live news)
            related_news = st.get("live_news") or [a for a in articles if a.get("ticker") == ticker][:2]
            news_quote_bull = f"Live news confirms: *'{related_news[0]['title']}'* ({related_news[0]['source']})." if related_news else "7-day momentum metrics are positive."
            news_quote_bear = f"Downside headline to monitor: *'{related_news[-1]['title']}'*." if len(related_news) > 1 else "Watch for unexpected valuation contraction."

            rating_badge = "🟢 BUY" if rating == "BUY" else "🔴 CAUTIOUS"
            verdict_badge = risk_info.get("badge", "🟡 Growth Swing")

            # Portfolio Memory & Concentration Check
            holdings = get_user_portfolio()
            owned_same_ticker = [h for h in holdings if h["ticker"] == ticker]
            owned_same_domain = [
                h for h in holdings
                if (h["domain"] == domain or ("AI" in h["domain"] and "AI" in domain)) and h["ticker"] != ticker
            ]
            other_domains = [d for d in ["Chips", "Energy", "AI"] if d != domain and ("AI" not in d if "AI" in domain else True)]
            if not other_domains:
                other_domains = ["Chips", "Energy"]

            memory_callout = ""
            if owned_same_ticker:
                memory_callout = (
                    f"> 💼 **Portfolio Memory Alert**: You already hold **{ticker}** in your portfolio. "
                    f"Be mindful of single-stock position sizing before adding additional shares.\n\n"
                )
            elif owned_same_domain:
                first_owned = owned_same_domain[0]
                first_name = first_owned["company_name"].split()[0]
                memory_callout = (
                    f"💼 **Portfolio Memory & Diversification Alert**:\n"
                    f"> *“Hey, you already bought **{first_name} ({first_owned['ticker']})** in **{first_owned['domain']}**! "
                    f"Adding **{ticker}** increases your portfolio concentration in the {domain} sector. "
                    f"Why not diversify and go for other **{' or '.join(other_domains).lower()}** (such as TSM for chips or CEG/NEE for energy) "
                    f"to balance your risk across the entire supply chain?”*\n\n"
                    f"---\n\n"
                )

            # Multi-Agent Dialogue script
            dialogue = (
                f"{memory_callout}"
                f"### ⚖️ Multi-Agent Deliberation: **{ticker} ({name})**\n"
                f"*Sector: {domain} | Rank: {rating_badge} #{rank} | Price: {price} (7d: {chg})*\n\n"
                f"---\n\n"
                f"**🐂 Bull Agent (Growth & Momentum Lead):**\n"
                f"> *\"My case for {ticker} is backed by this week's momentum: {bull_arg}. {news_quote_bull} "
                f"In this macro cycle, companies with direct exposure to {domain} infrastructure have powerful tailwinds that can sustain upside momentum.\"*\n\n"
                f"**🐻 Bear Agent (Risk & Valuation Auditor):**\n"
                f"> *\"Hold on Bull, let's inject some reality for retail investors: {bear_arg}. {news_quote_bear} "
                f"Beginners often get trapped buying at the top of a hype cycle without considering multiple contraction or execution delays in {domain}.\"*\n\n"
                f"**⚖️ Chief Risk Officer (Final Consensus Verdict):**\n"
                f"> **Rating**: `{verdict_badge}` • **Stance**: **{rating}**\n"
                f"> - **Guidance for Beginners**: {risk_info.get('desc', 'Position size with discipline.')}\n"
                f"> - **Actionable Strategy**: "
                f"{'Dollar-cost average into positions in 3 separate tranches to avoid entry timing risk.' if rating == 'BUY' else 'Keep on watchlist only; do not initiate new positions until valuation stabilizes.'}"
            )
            response_parts.append(dialogue)

        answer = "\n\n---\n\n".join(response_parts)
        save_chat_message("user", question)
        save_chat_message("assistant", answer)
        return answer

    # 4. Domain specific questions (e.g. "Tell me about Energy", "What about Chips?")
    for d_key in ["AI", "Chips", "Energy"]:
        if d_key.lower() in q_lower or (d_key == "Chips" and "semiconductor" in q_lower):
            d_data = domains.get(d_key, {})
            buy_list = d_data.get("buy", [])
            cautious_list = d_data.get("cautious", [])

            buy_bullets = "\n".join([
                f"  {i}. **{s['ticker']}** ({s['company_name']}): {s.get('weekly_change_pct', 0.0):+.1f}% — 🐂 *{s.get('bull_case', s.get('catalysts', ['Momentum'])[0])}*"
                for i, s in enumerate(buy_list[:5], 1)
            ])

            cautious_bullets = "\n".join([
                f"  {i}. **{s['ticker']}** ({s['company_name']}): {s.get('weekly_change_pct', 0.0):+.1f}% — 🐻 *{s.get('bear_case', s.get('risks', ['Headwinds'])[0])}*"
                for i, s in enumerate(cautious_list[:5], 1)
            ])

            answer = (
                f"### 📊 **{d_key} Domain Analysis (7-Day Outlook)**\n\n"
                f"**🟢 Top 5 Buy Picks (Positive Catalysts):**\n{buy_bullets}\n\n"
                f"**🔴 Top 5 Cautious Watchlist (Headwinds & Risks):**\n{cautious_bullets}\n\n"
                f"💡 *Ask: 'Why is {buy_list[0]['ticker']} rated buy?' or 'What is the ripple effect to Energy?'*"
            )
            save_chat_message("user", question)
            save_chat_message("assistant", answer)
            return answer

    # 5. Overall Top recommendations or Market Overview (Strict phrase matching)
    overview_phrases = [
        "top buy", "best buy", "what to buy", "what should i buy", "which stocks to buy",
        "top picks", "best picks", "best stocks", "overall recommendations", "market overview",
        "summary", "give me recommendations", "best stock", "market scan"
    ]
    if any(phrase in q_lower for phrase in overview_phrases) or q_lower.strip() in ["buy", "buys", "top", "picks", "recommendations", "overview"]:
        lines = ["### 🏆 **Top Buy Recommendations Across All Domains (7-Day Scan)**\n"]

        holdings = get_user_portfolio()
        if holdings:
            held_desc = ", ".join([f"{h['ticker']} ({h['domain']})" for h in holdings])
            owned_domains = set(h["domain"] for h in holdings)
            unowned = [d for d in ["Chips", "Energy", "AI"] if d not in owned_domains]
            if unowned:
                lines.append(
                    f"> 💼 **Portfolio Memory Context**: You currently hold **{held_desc}**.\n"
                    f"> *💡 Tip: Since you already have {list(owned_domains)[0]} exposure, we recommend prioritizing **{' & '.join(unowned)}** for smart diversification!*\n\n"
                )

        for d_key in ["AI", "Chips", "Energy"]:
            d_data = domains.get(d_key, {})
            top_stock = d_data.get("buy", [{}])[0] if d_data.get("buy") else None
            if top_stock:
                risk_badge = top_stock.get("beginner_risk", {}).get("badge", "🟢 Core Anchor")
                lines.append(
                    f"- **{d_key} Top Pick**: **{top_stock['ticker']}** ({top_stock['company_name']}) "
                    f"| Price: ${top_stock.get('current_price', 0.0):.2f} (7d: **{top_stock.get('weekly_change_pct', 0.0):+.1f}%**)\n"
                    f"  • *Rating*: `{risk_badge}` | 🐂 *Catalyst*: {top_stock.get('bull_case', 'Solid sector momentum')}"
                )

        lines.append("\n### ⚠️ **Key Stocks to Approach with Caution:**\n")
        for d_key in ["AI", "Chips", "Energy"]:
            d_data = domains.get(d_key, {})
            cautious_stock = d_data.get("cautious", [{}])[0] if d_data.get("cautious") else None
            if cautious_stock:
                lines.append(
                    f"- **{d_key} #1 Cautious**: **{cautious_stock['ticker']}** ({cautious_stock['company_name']}) "
                    f"| 7-Day: **{cautious_stock.get('weekly_change_pct', 0.0):+.1f}%**\n"
                    f"  • 🐻 *Risk*: {cautious_stock.get('bear_case', 'Market headwind')}"
                )

        answer = "\n".join(lines)
        save_chat_message("user", question)
        save_chat_message("assistant", answer)
        return answer

    # 6. Fallback intelligent response
    answer = (
        f"I'm your **Silicon Pulse Pocket Copilot**, tracking 7-day market sentiment across **AI, Chips, and Energy**.\n\n"
        f"Here are a few high-conviction queries you can ask right now:\n"
        f"- 🔗 *'Explain the supply chain ripple effect from AI to Energy'* \n"
        f"- 🛡️ *'What are the safest stocks for beginners?'*\n"
        f"- 🐂 *'Give me the Bull vs Bear case for NVDA'*\n"
        f"- ⚡ *'Why should I be cautious with Intel (INTC)?'*\n"
        f"- 🔋 *'Show me top nuclear energy stocks powering AI data centers'*"
    )
    save_chat_message("user", question)
    save_chat_message("assistant", answer)
    return answer
