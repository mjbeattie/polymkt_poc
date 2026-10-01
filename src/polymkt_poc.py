#!/usr/bin/env python3
"""
polymkt_poc.py

Robust Polymarket proof-of-concept script:
- Uses POLY_BASE_URL env var to override API base URL
- Writes outputs to OUTPUT_DIR (default "output")
- Uses requests.Session with retries and backoff
- Handles empty API responses gracefully
- Saves results CSV and plots into OUTPUT_DIR
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional

import requests
from requests.adapters import HTTPAdapter, Retry
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# -------------------------
# Configuration (override via env)
# -------------------------

from dotenv import load_dotenv

# Load variables from .env into environment variables
load_dotenv()

# Read the variables
api_key = os.getenv("POLY_API_KEY")
BASE_URL = os.getenv("POLY_BASE_URL", "https://api.polymarket.com")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
MARKETS_ENDPOINT = "/markets"
FILLS_ENDPOINT = "/fills"
PAGE_SIZE = int(os.getenv("PAGE_SIZE", 100))
MAX_PAGES = int(os.getenv("MAX_PAGES", 5))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 15))
SLEEP_BETWEEN_MARKETS = float(os.getenv("SLEEP_BETWEEN_MARKETS", 0.1))

# Taxonomy and weights (adjust as needed)
TAXONOMY = [
    "predictive maintenance", "digital twin", "non-destructive testing", "NDT",
    "ultrasonic", "eddy current", "robotic inspection", "drone", "UAV",
    "additive manufacturing", "3d printing", "augmented reality", "AR",
    "remote diagnostics", "IoT sensor", "vibration sensor", "machine learning",
    "anomaly detection", "blockchain", "parts provenance"
]
KEYWORD_WEIGHTS = {k: 1.0 for k in TAXONOMY}
KEYWORD_WEIGHTS.update({
    "predictive maintenance": 2.0,
    "digital twin": 1.8,
    "NDT": 1.5,
    "robotic inspection": 1.5
})

# Ensure output directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "plots"), exist_ok=True)

# -------------------------
# Logging
# -------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("polymkt_poc")

# -------------------------
# HTTP session with retries
# -------------------------
def make_session(retries: int = 4, backoff_factor: float = 1.0) -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"])
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

session = make_session()

def safe_get(url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    try:
        resp = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        logger.warning("Request failed for %s params=%s : %s", url, params, e)
        return None
    except ValueError as e:
        logger.warning("Invalid JSON from %s : %s", url, e)
        return None

# -------------------------
# API helpers
# -------------------------
def get_markets(page: int = 1, page_size: int = PAGE_SIZE) -> List[Dict[str, Any]]:
    url = f"{BASE_URL}{MARKETS_ENDPOINT}"
    params = {"page": page, "per_page": page_size}
    data = safe_get(url, params=params)
    if data is None:
        return []
    if isinstance(data, dict):
        if "markets" in data and isinstance(data["markets"], list):
            return data["markets"]
        if "data" in data and isinstance(data["data"], list):
            return data["data"]
        if all(k in data for k in ("id", "title")):
            return [data]
        return []
    elif isinstance(data, list):
        return data
    else:
        return []

def get_fills_for_market(market_id: str, limit: int = 500) -> List[Dict[str, Any]]:
    url = f"{BASE_URL}{FILLS_ENDPOINT}"
    params = {"market_id": market_id, "limit": limit}
    data = safe_get(url, params=params)
    if data is None:
        return []
    if isinstance(data, dict) and "fills" in data and isinstance(data["fills"], list):
        return data["fills"]
    if isinstance(data, list):
        return data
    return []

def search_markets_by_taxonomy(markets: List[Dict[str, Any]], taxonomy: List[str]) -> List[Dict[str, Any]]:
    matches = []
    for m in markets:
        text = " ".join([
            str(m.get("title", "")),
            str(m.get("description", "")),
            " ".join(m.get("tags", []) if m.get("tags") else [])
        ]).lower()
        matched_keywords = [kw for kw in taxonomy if kw.lower() in text]
        if matched_keywords:
            m["_matched_keywords"] = matched_keywords
            matches.append(m)
    return matches

# -------------------------
# Metrics and scoring
# -------------------------
def compute_metrics_and_scores(markets: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for m in markets:
        market_id = m.get("id") or m.get("marketId") or m.get("slug") or None
        title = m.get("title", "")
        created_at = m.get("created_at") or m.get("createdAt") or None
        price = m.get("price") or m.get("last_price") or m.get("lastPrice") or None
        volume_24h = m.get("volume_24h") or m.get("volume") or m.get("volume24h") or 0
        tags = m.get("tags", [])
        matched = m.get("_matched_keywords", [])

        fills = []
        if market_id:
            fills = get_fills_for_market(market_id, limit=200)

        df_f = pd.DataFrame(fills)
        if not df_f.empty:
            # timestamp normalization
            if 'created_at' in df_f.columns:
                df_f['timestamp'] = pd.to_datetime(df_f['created_at'])
            elif 'createdAt' in df_f.columns:
                df_f['timestamp'] = pd.to_datetime(df_f['createdAt'])
            else:
                for c in df_f.columns:
                    if 'time' in c or 'date' in c:
                        try:
                            df_f['timestamp'] = pd.to_datetime(df_f[c])
                            break
                        except Exception:
                            continue
            if 'timestamp' in df_f.columns:
                df_f = df_f.sort_values('timestamp')
            # price column normalization
            price_col = None
            for c in ['price', 'price_usd', 'last_price', 'lastPrice']:
                if c in df_f.columns:
                    price_col = c
                    break
            if price_col:
                prices = df_f[price_col].astype(float)
            else:
                prices = pd.Series(dtype=float)
            price_change_24h = (prices.iloc[-1] - prices.iloc[0]) / prices.iloc[0] if len(prices) > 1 and prices.iloc[0] != 0 else 0.0
            volatility = prices.pct_change().std() if len(prices) > 1 else 0.0
            trade_count = len(df_f)
            avg_trade_size = df_f['size'].astype(float).mean() if 'size' in df_f.columns else np.nan
        else:
            price_change_24h = 0.0
            volatility = 0.0
            trade_count = 0
            avg_trade_size = np.nan

        relevance = sum(KEYWORD_WEIGHTS.get(k, 1.0) for k in matched) / max(len(KEYWORD_WEIGHTS), 1)
        adoption = float(price_change_24h) * np.log1p(float(volume_24h) if volume_24h else 0.0)
        text = " ".join([title, m.get("description", "")]).lower()
        disruption_indicators = ["fail", "unavailable", "disrupt", "disruption", "shortage", "ban", "regulation", "grounded"]
        disruption_flag = any(word in text for word in disruption_indicators)
        disruption_score = 1.0 if disruption_flag else 0.0
        confidence = float(np.tanh((trade_count / 10.0) + (np.log1p(volume_24h or 0) / 10.0)))
        composite = relevance * (adoption - disruption_score) * confidence

        rows.append({
            "market_id": market_id,
            "title": title,
            "matched_keywords": ", ".join(matched),
            "price": price,
            "volume_24h": volume_24h,
            "price_change_24h": price_change_24h,
            "volatility": volatility,
            "trade_count": trade_count,
            "avg_trade_size": avg_trade_size,
            "relevance": relevance,
            "adoption": adoption,
            "disruption_score": disruption_score,
            "confidence": confidence,
            "composite_score": composite,
            "created_at": created_at,
            "tags": ", ".join(tags) if tags else ""
        })

        time.sleep(SLEEP_BETWEEN_MARKETS)

    df = pd.DataFrame(rows)
    if "composite_score" not in df.columns:
        df["composite_score"] = pd.Series(dtype=float)
    if not df.empty:
        df = df.sort_values("composite_score", ascending=False)
    return df

# -------------------------
# Visualization helper
# -------------------------
def plot_market_price_series(market_id: str, title: str, save_path: Optional[str] = None):
    fills = get_fills_for_market(market_id, limit=500)
    df = pd.DataFrame(fills)
    if df.empty:
        logger.info("No fills for market %s", market_id)
        return
    if 'created_at' in df.columns:
        df['timestamp'] = pd.to_datetime(df['created_at'])
    elif 'createdAt' in df.columns:
        df['timestamp'] = pd.to_datetime(df['createdAt'])
    else:
        for c in df.columns:
            if 'time' in c or 'date' in c:
                try:
                    df['timestamp'] = pd.to_datetime(df[c])
                    break
                except Exception:
                    continue
    price_col = None
    for c in ['price', 'price_usd', 'last_price', 'lastPrice']:
        if c in df.columns:
            price_col = c
            break
    if price_col is None or 'timestamp' not in df.columns:
        logger.info("Insufficient data to plot market %s", market_id)
        return
    df = df.sort_values('timestamp')
    plt.figure(figsize=(10, 4))
    plt.plot(df['timestamp'], df[price_col].astype(float), marker='o', linestyle='-')
    plt.title(title)
    plt.xlabel("Time")
    plt.ylabel("Price")
    plt.grid(True)
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path)
        logger.info("Saved plot to %s", save_path)
    else:
        plt.show()
    plt.close()

# -------------------------
# Main flow
# -------------------------
def main():
    logger.info("Starting Polymarket POC (BASE_URL=%s OUTPUT_DIR=%s)", BASE_URL, OUTPUT_DIR)

    all_markets = []
    for page in range(1, MAX_PAGES + 1):
        logger.info("Fetching markets page %d", page)
        page_markets = get_markets(page=page)
        if not page_markets:
            logger.info("No markets returned for page %d; stopping fetch", page)
            break
        all_markets.extend(page_markets)
        time.sleep(0.2)

    logger.info("Fetched %d markets", len(all_markets))
    matched = search_markets_by_taxonomy(all_markets, TAXONOMY)
    logger.info("Found %d markets matching taxonomy", len(matched))

    df_scores = compute_metrics_and_scores(matched)
    if df_scores.empty:
        logger.info("No scored markets to show. Writing empty results file.")
        cols = ["market_id","title","matched_keywords","price","volume_24h","price_change_24h",
                "volatility","trade_count","avg_trade_size","relevance","adoption",
                "disruption_score","confidence","composite_score","created_at","tags"]
        pd.DataFrame(columns=cols).to_csv(os.path.join(OUTPUT_DIR, "results_empty.csv"), index=False)
        return

    out_csv = os.path.join(OUTPUT_DIR, "results_scored.csv")
    df_scores.to_csv(out_csv, index=False)
    logger.info("Wrote %s with %d rows", out_csv, len(df_scores))

    # Save top N plots
    top = df_scores.head(5)
    for idx, row in top.iterrows():
        safe_name = str(row['market_id']).replace("/", "_")
        plot_path = os.path.join(OUTPUT_DIR, "plots", f"top_{idx}_{safe_name}.png")
        plot_market_price_series(row['market_id'], row['title'], save_path=plot_path)

    logger.info("Done. Check the output directory: %s", OUTPUT_DIR)

if __name__ == "__main__":
    main()
