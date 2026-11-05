#!/usr/bin/env python3
"""
VCP MONTHLY SCREENER v2 - live scan + custom-range backtest

Usage:
  python vcp_monthly_screener_v2.py live
  python vcp_monthly_screener_v2.py backtest --start 2025-01-01 --end 2026-09-30

Only COMPLETED months are evaluated (the in-progress month is always dropped).

For every stock and every completed month, with prev3 = the 3 months before it:
  STRICT  : range > sum(prev3 ranges)          AND volume >= 2.0 x avg(prev3 volumes)
            (your original rule)
  RELAXED : range > avg(prev3 ranges)          AND volume >= 1.5 x avg(prev3 volumes)
  RANK    : filler only. If a month has fewer than MIN_PICKS_PER_MONTH STRICT/RELAXED
            names, the highest-scoring remaining names are shown and tagged RANK.
            RANK rows are NOT breakout signals.

Score = (range / sum(prev3 ranges)) * (volume / avg(prev3 volumes))
"""

import argparse
import io
import os
import smtplib
import sys
import time
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import numpy as np
import pandas as pd
import requests
import yfinance as yf

# ----------------------------- CONFIG -----------------------------
LOOKBACK = 3                  # months in the comparison window
STRICT_VOL_MULT = 2.0         # strict: volume >= 2.0 x avg(prev3)
RELAXED_RANGE_FRAC = 1 / 3    # relaxed: range > (1/3) x sum(prev3) = avg(prev3)
RELAXED_VOL_MULT = 2.0        # relaxed: volume >= 2.0 x avg(prev3)  (+ breakout required)
RELAXED_LOOSE_VOL_MULT = 1.5  # comparison column only ('loose'), never used for picks
MIN_PICKS_PER_MONTH = 3       # guarantee at least this many rows per month (RANK fills the gap)
REQUEST_PAUSE_SEC = 0.1       # be gentle with Yahoo

NSE_INDEX_LISTS = {
    'Nifty 50': 'https://archives.nseindia.com/content/indices/ind_nifty50list.csv',
    'Nifty Next 50': 'https://archives.nseindia.com/content/indices/ind_niftynext50list.csv',
    'Nifty Midcap 150': 'https://archives.nseindia.com/content/indices/ind_niftymidcap150list.csv',
    'Nifty Smallcap 250': 'https://archives.nseindia.com/content/indices/ind_niftysmallcap250list.csv',
}
NSE_HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 'Accept': 'text/csv,*/*'}

# Used ONLY if the NSE index files cannot be downloaded.
FALLBACK_UNIVERSE = [
    'ADANIENT', 'ADANIPORTS', 'APOLLOHOSP', 'ASIANPAINT', 'AXISBANK', 'BAJAJ-AUTO', 'BAJFINANCE',
    'BAJAJFINSV', 'BEL', 'BHARTIARTL', 'BPCL', 'BRITANNIA', 'CIPLA', 'COALINDIA', 'DRREDDY',
    'EICHERMOT', 'ETERNAL', 'GRASIM', 'HCLTECH', 'HDFCBANK', 'HDFCLIFE', 'HEROMOTOCO', 'HINDALCO',
    'HINDUNILVR', 'ICICIBANK', 'INDUSINDBK', 'INFY', 'ITC', 'JIOFIN', 'JSWSTEEL', 'KOTAKBANK', 'LT',
    'M&M', 'MARUTI', 'NESTLEIND', 'NTPC', 'ONGC', 'POWERGRID', 'RELIANCE', 'SBILIFE', 'SBIN',
    'SHRIRAMFIN', 'SUNPHARMA', 'TATACONSUM', 'TATAMOTORS', 'TATASTEEL', 'TCS', 'TECHM', 'TITAN',
    'TRENT', 'ULTRACEMCO', 'WIPRO', 'POLYCAB', 'PAGEIND', 'BERGEPAINT', 'DIVISLAB', 'LUPIN',
    'BOSCHLTD', 'AMBUJACEM', 'SHREECEM', 'ALKEM', 'AUROPHARM', 'NATIONALUM', 'JINDALSTEL', 'SAIL',
    'VEDL', 'THERMAX', 'IRFC', 'IDFCFIRSTB', 'NAUKRI', 'PAYTM', 'NYKAA', 'HAVELLS', 'SIEMENS', 'ABB',
    'CROMPTON', 'CUMMINSIND', 'MUTHOOTFIN', 'KPITTECH', 'KALYANKJIL', 'IPCALAB', 'ASTRAL',
    'BLUESTARCO', 'CGPOWER', 'CONCOR', 'CEATLTD', 'COFORGE', 'DEEPAKNTR', 'DMART', 'MEESHO',
    'PERSISTENT', 'PIDILITIND', 'HAL', 'BHEL', 'IRCTC', 'TATAPOWER', 'ADANIGREEN', 'ADANIPOWER',
    'GODREJCP', 'MARICO', 'DABUR', 'COLPAL', 'HDFCAMC', 'MAXHEALTH', 'LTIM', 'PRESTIGE',
    'OBEROIRLTY', 'GODREJPROP', 'SUZLON', 'RVNL', 'IREDA', 'ZYDUSLIFE', 'TORNTPHARM',
]


# ----------------------------- UNIVERSE -----------------------------
def load_universe():
    """Pull current constituents of Nifty 50 / Next 50 / Midcap 150 / Smallcap 250 from NSE."""
    symbols = set()
    for name, url in NSE_INDEX_LISTS.items():
        try:
            resp = requests.get(url, headers=NSE_HEADERS, timeout=20)
            resp.raise_for_status()
            df = pd.read_csv(io.StringIO(resp.text))
            syms = df['Symbol'].dropna().astype(str).str.strip()
            symbols.update(f"{s}.NS" for s in syms)
            print(f"  {name:20s} {len(syms)} symbols")
        except Exception as exc:
            print(f"  {name:20s} download failed ({exc})")
    if not symbols:
        print("  NSE lists unavailable -> using built-in fallback universe")
        symbols = {f"{s}.NS" for s in FALLBACK_UNIVERSE}
    return sorted(symbols)


# ----------------------------- DATA -----------------------------
def fetch_monthly(symbol, fetch_start, fetch_end, cutoff):
    """Monthly OHLCV, keeping only months that fully closed on or before `cutoff`.
    Returns (df, reason). df is None when the stock could not be used."""
    try:
        raw = yf.Ticker(symbol).history(start=fetch_start, end=fetch_end,
                                        interval='1mo', auto_adjust=False)
    except Exception as exc:
        return None, f"exception: {exc}"
    if raw is None or raw.empty:
        return None, "empty response from Yahoo"

    df = raw[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
    idx = pd.DatetimeIndex(df.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    df.index = idx

    month_end = idx.to_period('M').end_time.normalize()
    closed = np.asarray(month_end <= cutoff)
    df = df[closed]
    if len(df) <= LOOKBACK:
        return None, f"only {len(df)} completed months"
    return df, ""


# ----------------------------- LOGIC -----------------------------
def evaluate(df, symbol, start, end):
    """One row per completed month in [start, end] that has LOOKBACK prior months."""
    rows = []
    rng = (df['High'] - df['Low']).to_numpy(dtype=float)
    highs = df['High'].to_numpy(dtype=float)
    vol = df['Volume'].to_numpy(dtype=float)
    close = df['Close'].to_numpy(dtype=float)
    months = df.index

    for i in range(LOOKBACK, len(df)):
        month = months[i]
        if month < start or month > end:
            continue

        cur_r, cur_v = rng[i], vol[i]
        sum_r = rng[i - LOOKBACK:i].sum()
        avg_v = vol[i - LOOKBACK:i].mean()
        if sum_r <= 0 or avg_v <= 0:
            continue

        c1 = cur_r > sum_r                          # range condition (your rule)
        c2 = cur_v >= STRICT_VOL_MULT * avg_v       # volume condition (your rule)
        prior_high = highs[i - LOOKBACK:i].max()
        breakout = close[i] > prior_high            # closed above resistance (prior 3 months' high)
        range_ok = cur_r > RELAXED_RANGE_FRAC * sum_r
        relaxed = range_ok and (cur_v >= RELAXED_VOL_MULT * avg_v) and breakout
        loose = range_ok and (cur_v >= RELAXED_LOOSE_VOL_MULT * avg_v)

        range_vs_sum = cur_r / sum_r
        vol_vs_avg = cur_v / avg_v
        rows.append({
            'month': month,
            'symbol': symbol,
            'close': round(close[i], 2),
            'prior3_high': round(prior_high, 2),
            'breakout': bool(breakout),
            'loose': bool(loose),
            'range': round(cur_r, 2),
            'sum_prev3_range': round(sum_r, 2),
            'range_vs_sum': round(range_vs_sum, 2),
            'volume': int(cur_v),
            'avg_prev3_volume': int(avg_v),
            'vol_vs_avg': round(vol_vs_avg, 2),
            'c1_range': c1,
            'c2_volume': c2,
            'strict': c1 and c2,
            'relaxed': relaxed,
            'score': round(range_vs_sum * vol_vs_avg, 3),
        })
    return rows


TIER_ORDER = {'STRICT': 0, 'RELAXED': 1, 'RANK': 2}


def pick_for_month(rows):
    """Strict and relaxed hits first; top-scoring filler (tagged RANK) if too few."""
    picks = []
    for r in rows:
        if r['strict']:
            picks.append({**r, 'tier': 'STRICT'})
        elif r['relaxed']:
            picks.append({**r, 'tier': 'RELAXED'})
    picks.sort(key=lambda r: (TIER_ORDER[r['tier']], -r['score']))

    if len(picks) < MIN_PICKS_PER_MONTH:
        taken = {p['symbol'] for p in picks}
        rest = sorted((r for r in rows if r['symbol'] not in taken), key=lambda r: -r['score'])
        for r in rest[:MIN_PICKS_PER_MONTH - len(picks)]:
            picks.append({**r, 'tier': 'RANK'})
    return picks


def run_scan(symbols, start, end):
    fetch_start = (start - pd.DateOffset(months=LOOKBACK + 1)).strftime('%Y-%m-%d')  # warm-up window
    fetch_end = (end + pd.Timedelta(days=1)).strftime('%Y-%m-%d')                    # yfinance end is exclusive
    cutoff = min(pd.Timestamp(date.today()), end)

    rows, failed, reasons = [], 0, []
    for n, sym in enumerate(symbols, 1):
        print(f"\r  [{n}/{len(symbols)}] {sym:18s}", end='', flush=True)
        df, reason = fetch_monthly(sym, fetch_start, fetch_end, cutoff)
        if df is None:
            failed += 1
            if len(reasons) < 5:
                reasons.append(f"{sym}: {reason}")
            continue
        rows += evaluate(df, sym.replace('.NS', ''), start, end)
        time.sleep(REQUEST_PAUSE_SEC)
    print(f"\n  Stocks with usable data: {len(symbols) - failed}/{len(symbols)}")
    if failed == len(symbols):
        print("  ALL fetches failed. First errors:")
        for r in reasons:
            print(f"    {r}")
        print("  -> Usually Yahoo blocking or rate-limiting, or no internet. Try again later, "
              "or run: pip install -U yfinance")
    return rows


def print_diagnostics(rows):
    n = len(rows)
    if n == 0:
        print("\nNo stock-months evaluated. Check internet access and the date range.")
        return
    c1 = sum(r['c1_range'] for r in rows)
    c2 = sum(r['c2_volume'] for r in rows)
    both = sum(r['strict'] for r in rows)
    rel = sum(r['relaxed'] for r in rows)
    print("\n" + "=" * 70)
    print("STRICTNESS DIAGNOSTICS (stock-months evaluated)")
    print("=" * 70)
    print(f"  Total stock-months          : {n}")
    print(f"  Range > sum(prev3)          : {c1:5d}  ({100*c1/n:.2f}%)")
    print(f"  Volume >= 2x avg(prev3)     : {c2:5d}  ({100*c2/n:.2f}%)")
    print(f"  STRICT (both, your rule)    : {both:5d}  ({100*both/n:.2f}%)")
    brk = sum(r['breakout'] for r in rows)
    loose = sum(r['loose'] for r in rows)
    print(f"  Close above prior-3 high    : {brk:5d}  ({100*brk/n:.2f}%)")
    print(f"  RELAXED (range>avg, vol>=2x, breakout): {rel:5d}  ({100*rel/n:.2f}%)")
    print(f"  Comparison only (range>avg, vol>=1.5x, no breakout): {loose:5d}  ({100*loose/n:.2f}%)")
    print("=" * 70)


def print_picks(month, picks):
    counts = {t: sum(p['tier'] == t for p in picks) for t in TIER_ORDER}
    print(f"\n{month:%Y-%m}  picks={len(picks)}  "
          f"(STRICT {counts['STRICT']}, RELAXED {counts['RELAXED']}, RANK {counts['RANK']})")
    for p in picks:
        print(f"   {p['symbol']:12s} {p['tier']:8s} close {p['close']:>10.2f}  "
              f"range/sum {p['range_vs_sum']:5.2f}x  vol/avg {p['vol_vs_avg']:5.2f}x  "
              f"score {p['score']:6.2f}")


def send_email(df, subject):
    sender = os.getenv('SENDER_EMAIL', '')
    password = os.getenv('SENDER_PASSWORD', '')
    recipient = os.getenv('RECIPIENT_EMAIL', sender)
    if not sender or not password:
        print("Email skipped (SENDER_EMAIL / SENDER_PASSWORD not set)")
        return
    msg = MIMEMultipart()
    msg['From'], msg['To'], msg['Subject'] = sender, recipient, subject
    msg.attach(MIMEText(df.to_html(index=False), 'html'))
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender, password)
        server.send_message(msg)
    print(f"Email sent to {recipient}")


# ----------------------------- MAIN -----------------------------
def main():
    ap = argparse.ArgumentParser(description='VCP monthly screener v2')
    ap.add_argument('mode', nargs='?', default='live', choices=['live', 'backtest'],
                    help='live (default): last completed month. backtest: needs --start and --end')
    ap.add_argument('--start', help='YYYY-MM-DD (backtest)')
    ap.add_argument('--end', help='YYYY-MM-DD (backtest)')
    args = ap.parse_args()

    today = pd.Timestamp(date.today())
    if args.mode == 'live':
        start = today.replace(day=1) - pd.DateOffset(months=1)   # last completed month
        end = today
    else:
        if not (args.start and args.end):
            sys.exit("backtest needs --start and --end (YYYY-MM-DD)")
        start, end = pd.Timestamp(args.start), pd.Timestamp(args.end)
        if start >= end:
            sys.exit("start must be before end")

    print("Loading universe:")
    symbols = load_universe()
    print(f"Universe size: {len(symbols)}")
    print(f"Evaluating completed months {start:%Y-%m} to {end:%Y-%m-%d}")

    rows = run_scan(symbols, start, end)
    print_diagnostics(rows)

    all_picks = []
    for month in sorted({r['month'] for r in rows}):
        month_rows = [r for r in rows if r['month'] == month]
        picks = pick_for_month(month_rows)
        print_picks(month, picks)
        all_picks += [{**p, 'month': f"{month:%Y-%m}"} for p in picks]

    if not all_picks:
        print("\nNo stock-months were evaluated, so there is nothing to pick from. "
              "See the fetch errors above.")
        return

    out = pd.DataFrame(all_picks)[['month', 'symbol', 'tier', 'close', 'prior3_high', 'breakout',
                                   'range', 'sum_prev3_range', 'range_vs_sum', 'volume',
                                   'avg_prev3_volume', 'vol_vs_avg', 'c1_range', 'c2_volume',
                                   'loose', 'score']]
    fname = f"vcp_v2_{args.mode}_{pd.Timestamp.now():%Y%m%d_%H%M}.csv"
    out.to_csv(fname, index=False)
    print(f"\nSaved: {os.path.abspath(fname)}")

    if args.mode == 'live':
        send_email(out, f"VCP monthly picks - {today:%Y-%m-%d}")


if __name__ == '__main__':
    main()
                           
