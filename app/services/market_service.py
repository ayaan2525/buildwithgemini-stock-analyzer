"""
Service to fetch live stock prices and 1-week percentage performance
using Yahoo Finance chart API.
"""
import urllib.request
import json
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def get_stock_quote(ticker: str) -> Dict[str, Any]:
    """
    Fetch current price and 7-day performance for a given ticker.
    """
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=7d"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    fallback_data = {
        "ticker": ticker,
        "current_price": None,
        "weekly_change_pct": 0.0,
        "sparkline": [],
        "currency": "USD",
        "day_high": None,
        "day_low": None
    }

    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        # print(f"Quote error for {ticker}: {e}")
        return fallback_data

    try:
        result = data.get("chart", {}).get("result", [])
        if not result:
            return fallback_data

        meta = result[0].get("meta", {})
        price = meta.get("regularMarketPrice")
        currency = meta.get("currency", "USD")
        day_high = meta.get("regularMarketDayHigh")
        day_low = meta.get("regularMarketDayLow")

        quote_ind = result[0].get("indicators", {}).get("quote", [{}])[0]
        closes = [round(c, 2) for c in quote_ind.get("close", []) if c is not None]

        if closes and price:
            start_price = closes[0]
            weekly_change = round(((price - start_price) / start_price) * 100, 2)
        elif len(closes) >= 2:
            start_price = closes[0]
            curr = closes[-1]
            weekly_change = round(((curr - start_price) / start_price) * 100, 2)
            price = curr
        else:
            weekly_change = 0.0

        return {
            "ticker": ticker,
            "current_price": round(price, 2) if price else None,
            "weekly_change_pct": weekly_change,
            "sparkline": closes,
            "currency": currency,
            "day_high": round(day_high, 2) if day_high else None,
            "day_low": round(day_low, 2) if day_low else None
        }
    except Exception as e:
        print(f"Error parsing quote for {ticker}: {e}")
        return fallback_data

def get_quotes_batch(tickers: List[str]) -> Dict[str, Dict[str, Any]]:
    """Fetch quotes concurrently for a list of tickers."""
    results = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_ticker = {executor.submit(get_stock_quote, t): t for t in tickers}
        for future in future_to_ticker:
            t = future_to_ticker[future]
            try:
                res = future.result()
                results[t] = res
            except Exception as e:
                print(f"Batch quote failed for {t}: {e}")
                results[t] = {"ticker": t, "current_price": None, "weekly_change_pct": 0.0, "sparkline": []}
    return results
