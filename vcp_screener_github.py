#!/usr/bin/env python3
"""
MINERVINI SEPA / VCP BREAKOUT SCREENER (NSE)
Rules taken from "Trade Like a Stock Market Wizard" (Mark Minervini).

A stock is a signal on day i only if ALL of these hold:

 1. TREND TEMPLATE (book, ch. 5 - all 8 must pass)
    - close > 150-day MA and > 200-day MA
    - 150-day MA > 200-day MA
    - 200-day MA rising for at least 1 month (22 sessions)
    - 50-day MA > 150-day MA and > 200-day MA
    - close > 50-day MA
    - close >= 30% above 52-week low
    - close within 25% of 52-week high
    - relative strength rank >= 70 (see NOTE on RS below)

 2. VCP - volatility contraction (book, ch. 10)
    - 2 to 4 successive pullbacks, each about half (here: <= 75%) of the previous one
    - first pullback of the run <= 35%, last pullback <= 10%
    - volume during the last contraction below its 50-day average (volume dry-up)
    - pivot = high of the last swing high (top of the last contraction)
    - pivot formed within the last ~65 sessions

 3. PIVOT BREAKOUT (book: "buy when the stock moves above the pivot point on expanding volume")
    - close is above the pivot for the FIRST time (no earlier close above it since the pivot)
    - close not more than 5% above pivot (book: don't chase)
    - breakout-day volume >= 1.4 x 50-day average  (ASSUMPTION - the book says
      "expanding volume" without a number; 1.4 is a configurable choice)

 Risk (book, ch. 12): stop = 8% below entry. Shown in the output, not used as a filter.

NOTE on RS rank: IBD's proprietary RS rating is not available. This uses a proxy:
  raw = 0.4*ret(3m) + 0.2*ret(6m) + 0.2*ret(9m) + 0.2*ret(12m)
ranked as a percentile across the scanned universe on each day. It is an approximation.

No screen is perfect. The book itself says failed bases are common. Run the backtest
before trusting the output.

Usage:
  python vcp_minervini_screener.py live
  python vcp_minervini_screener.py backtest --start 2024-01-01 --end 2026-10-31
"""

import argparse
import io
import os
import sys
import time
from datetime import date

import numpy as np
import pandas as pd
import requests
import yfinance as yf

# ----------------------------- CONFIG -----------------------------
SMA_FAST, SMA_MID, SMA_SLOW = 50, 150, 200
UP_MONTH = 22            # sessions the 200-day MA must have risen
HI52 = 252               # sessions in 52 weeks
LOW52_MULT = 1.30        # close >= 1.30 x 52-week low
HIGH52_MULT = 0.75       # close >= 0.75 x 52-week high
RS_MIN = 70              # relative strength percentile threshold

SWING_N = 3              # a swing high is the max high over +/- 3 sessions
BASE_LOOKBACK = 130      # sessions searched for the base
MAX_PIVOT_AGE = 65       # pivot must be formed within this many sessions
CONTRACT_RATIO = 0.75    # each pullback <= 75% of the previous one
MIN_CONTRACTIONS = 2     # trailing contracting pullbacks required
MAX_FIRST_DEPTH = 0.35   # first pullback of the run <= 35%
MAX_LAST_DEPTH = 0.10    # last pullback <= 10%
MAX_CHASE = 0.05         # close <= pivot x 1.05
VOL_MA = 50              # volume average used for dry-up and breakout
BREAKOUT_VOL_MULT = 1.4  # ASSUMPTION (see header)
STOP_PCT = 0.08          # risk shown in output

HORIZONS = {'1m': 21, '3m': 63, '6m': 126}
BENCH = '^NSEI'
COOLDOWN = 21
PAUSE = 0.1
WARMUP_DAYS = 460        # calendar days of history before the window

NSE_INDEX_LISTS = {
    'Nifty 50': 'https://archives.nseindia.com/content/indices/ind_nifty50list.csv',
    'Nifty Next 50': 'https://archives.nseindia.com/content/indices/ind_niftynext50list.csv',
    'Nifty Midcap 150': 'https://archives.nseindia.com/content/indices/ind_niftymidcap150list.csv',
    'Nifty Smallcap 250': 'https://archives.nseindia.com/content/indices/ind_niftysmallcap250list.csv',
}
NSE_HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', 'Accept': 'text/csv,*/*'}

# Used ONLY if the NSE index files cannot be downloaded.
FALLBACK_UNIVERSE = [
    'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'LT', 'MARUTI', 'BAJAJ-AUTO', 'SUNPHARMA',
    'WIPRO', 'TECHM', 'NTPC', 'ONGC', 'SBIN', 'POLYCAB', 'PAGEIND', 'BERGEPAINT', 'DIVISLAB', 'LUPIN',
    'SAIL', 'VEDL', 'IRFC', 'HAL', 'BEL', 'BHEL', 'RVNL', 'IRCON', 'NBCC', 'HFCL', 'TATAPOWER',
]


# ----------------------------- UNIVERSE -----------------------------
def load_universe():
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
def fetch_daily(symbol, start, end):
    """Daily OHLCV. Returns (df, reason). df is None if unusable."""
    try:
        # auto_adjust=True: prices adjusted for splits/bonuses, so a split is not read as a crash
        raw = yf.Ticker(symbol).history(start=start, end=end, interval='1d', auto_adjust=True)
    except Exception as exc:
        return None, f"exception: {exc}"
    if raw is None or raw.empty:
        return None, "empty response from Yahoo"
    df = raw[['High', 'Low', 'Close', 'Volume']].copy()
    idx = pd.DatetimeIndex(df.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    df.index = idx.normalize()
    df = df[~df.index.duplicated(keep='last')].sort_index()
    if len(df) < HI52 + 30:
        return None, f"only {len(df)} sessions (need {HI52 + 30})"
    return df, ""


def rs_raw(close):
    r = lambda n: close / close.shift(n) - 1
    return 0.4 * r(63) + 0.2 * r(126) + 0.2 * r(189) + 0.2 * r(252)


def trend_template(close):
    s50 = close.rolling(SMA_FAST).mean()
    s150 = close.rolling(SMA_MID).mean()
    s200 = close.rolling(SMA_SLOW).mean()
    lo52 = close.rolling(HI52).min()
    hi52 = close.rolling(HI52).max()
    ok = ((close > s150) & (close > s200)
          & (s150 > s200)
          & (s200 > s200.shift(UP_MONTH))
          & (s50 > s150) & (s50 > s200)
          & (close > s50)
          & (close >= LOW52_MULT * lo52)
          & (close >= HIGH52_MULT * hi52))
    return ok.fillna(False).to_numpy(bool)


# ----------------------------- VCP LOGIC -----------------------------
def find_vcp(high, low, close, vol, avg_vol, i):
    """Check signal day i. Returns dict or None. Arrays are numpy, avg_vol is the prior-50-day mean."""
    if i < BASE_LOOKBACK // 2:
        return None

    # 1) confirmed swing highs in the base window (need SWING_N bars after each)
    lo_j = max(SWING_N, i - BASE_LOOKBACK)
    swings = [j for j in range(lo_j, i - SWING_N)
              if high[j] == high[j - SWING_N:j + SWING_N + 1].max()]
    if len(swings) < 3:
        return None
    piv = swings[-1]
    if i - piv > MAX_PIVOT_AGE:
        return None
    pivot = high[piv]

    # 2) pullbacks between the last 5 swing highs (4 pullbacks, chronological)
    S = swings[-5:]
    depths = []
    for a, b in zip(S[:-1], S[1:]):
        depths.append((high[a] - low[a:b + 1].min()) / high[a])

    # 3) trailing run of contracting pullbacks (each <= CONTRACT_RATIO x previous)
    run = [depths[-1]]
    for k in range(len(depths) - 2, -1, -1):
        if run[0] <= CONTRACT_RATIO * depths[k]:
            run.insert(0, depths[k])
        else:
            break
    if len(run) < MIN_CONTRACTIONS:
        return None
    run = run[-4:]
    if run[0] > MAX_FIRST_DEPTH or run[-1] > MAX_LAST_DEPTH:
        return None

    # 4) breakout: first close above pivot since it formed, not chased
    if not (close[i] > pivot and close[i] <= pivot * (1 + MAX_CHASE)):
        return None
    if piv + 1 < i and close[piv + 1:i].max() > pivot:
        return None

    # 5) volume dry-up in the last contraction, and expansion on breakout
    if vol[S[-2]:piv + 1].mean() >= avg_vol:
        return None
    if vol[i] < BREAKOUT_VOL_MULT * avg_vol:
        return None

    return {
        'pivot': round(float(pivot), 2),
        'contractions': len(run),
        'depths_pct': '/'.join(f"{d * 100:.0f}" for d in run),
        'pct_above_pivot': round((close[i] / pivot - 1) * 100, 2),
        'vol_vs_50d': round(vol[i] / avg_vol, 2),
    }


def scan_symbol(sym, df, rs, start, end, bench):
    high = df['High'].to_numpy(float)
    low = df['Low'].to_numpy(float)
    close = df['Close'].to_numpy(float)
    vol = df['Volume'].to_numpy(float)
    dates = df.index
    n = len(df)

    tt = trend_template(df['Close'])
    avg_vol = pd.Series(vol).rolling(VOL_MA).mean().shift(1).to_numpy(float)
    rs_arr = rs.reindex(dates).to_numpy(float)

    out = []
    last = -10 ** 9
    for i in range(1, n):
        d = dates[i]
        if d < start or d > end or i - last < COOLDOWN:
            continue
        if not tt[i] or not (rs_arr[i] >= RS_MIN) or np.isnan(avg_vol[i]) or avg_vol[i] <= 0:
            continue
        if close[i] <= close[i - 1]:
            continue
        info = find_vcp(high, low, close, vol, avg_vol[i], i)
        if info is None:
            continue
        last = i
        row = {
            'symbol': sym.replace('.NS', ''),
            'signal_date': d.date(),
            'close': round(close[i], 2),
            'pivot': info['pivot'],
            'pct_above_pivot': info['pct_above_pivot'],
            'contractions': info['contractions'],
            'pullbacks_%': info['depths_pct'],
            'vol_vs_50d': info['vol_vs_50d'],
            'rs_rank': round(float(rs_arr[i]), 1),
            'stop_8pct': round(close[i] * (1 - STOP_PCT), 2),
        }
        for h, step in HORIZONS.items():
            j = i + step
            if j < n:
                row[h] = round((close[j] / close[i] - 1) * 100, 2)
                b0, b1 = bench.asof(d), bench.asof(dates[j])
                row['bench_' + h] = round((b1 / b0 - 1) * 100, 2) if b0 and b1 else np.nan
            else:
                row[h] = np.nan
                row['bench_' + h] = np.nan
        out.append(row)
    return out


# ----------------------------- REPORTING -----------------------------
def summarize(res):
    if res.empty:
        print("\nNo signals. Widen the date range, or the screen is genuinely strict on this period.")
        return
    print("\n" + "=" * 78)
    print("RESULTS (forward returns from signal-day close; Nifty 50 over the same dates)")
    print("=" * 78)
    print(f"Signals per month:\n{res.groupby(pd.to_datetime(res.signal_date).dt.to_period('M')).size().to_string()}\n")
    for h in HORIZONS:
        s = res[h].dropna()
        if s.empty:
            print(f"  {h}: no signals with a full forward window yet")
            continue
        b = res['bench_' + h].dropna()
        ex = (res[h] - res['bench_' + h]).dropna()
        print(f"  {h}: n={len(s):4d}  made money={(s > 0).mean() * 100:5.1f}%  "
              f"avg={s.mean():6.2f}%  median={s.median():6.2f}%  | Nifty avg={b.mean():5.2f}%  "
              f"beat Nifty={(ex > 0).mean() * 100:5.1f}%  avg excess={ex.mean():6.2f}%")
    print("=" * 78)


def send_email(df, subject):
    sender = os.getenv('SENDER_EMAIL', '')
    password = os.getenv('SENDER_PASSWORD', '')
    recipient = os.getenv('RECIPIENT_EMAIL', sender)
    if not sender or not password:
        print("Email skipped (SENDER_EMAIL / SENDER_PASSWORD not set)")
        return
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    msg = MIMEMultipart()
    msg['From'], msg['To'], msg['Subject'] = sender, recipient, subject
    msg.attach(MIMEText(df.to_html(index=False), 'html'))
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender, password)
        server.send_message(msg)
    print(f"Email sent to {recipient}")


# ----------------------------- MAIN -----------------------------
def main():
    ap = argparse.ArgumentParser(description='Minervini VCP breakout screener')
    ap.add_argument('mode', nargs='?', default='live', choices=['live', 'backtest'])
    ap.add_argument('--start', help='YYYY-MM-DD (backtest)')
    ap.add_argument('--end', help='YYYY-MM-DD (backtest)')
    args = ap.parse_args()

    today = pd.Timestamp(date.today())
    if args.mode == 'live':
        start, end = today - pd.Timedelta(days=5), today
    else:
        if not (args.start and args.end):
            sys.exit("backtest needs --start and --end (YYYY-MM-DD)")
        start, end = pd.Timestamp(args.start), pd.Timestamp(args.end)
        if start >= end:
            sys.exit("start must be before end")

    print("Loading universe:")
    symbols = load_universe()
    print(f"Universe size: {len(symbols)}")

    fetch_start = (start - pd.Timedelta(days=WARMUP_DAYS)).strftime('%Y-%m-%d')
    fetch_end = (max(end, today) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')

    bench_df, why = fetch_daily(BENCH, fetch_start, fetch_end)
    if bench_df is None:
        sys.exit(f"Could not load Nifty 50 ({BENCH}): {why}")
    bench = bench_df['Close']

    # Pass 1: download everything (needed for the cross-sectional RS rank)
    data, reasons = {}, []
    for n, sym in enumerate(symbols, 1):
        print(f"\r  download [{n}/{len(symbols)}] {sym:18s}", end='', flush=True)
        df, reason = fetch_daily(sym, fetch_start, fetch_end)
        if df is None:
            if len(reasons) < 5:
                reasons.append(f"{sym}: {reason}")
            continue
        data[sym] = df
        time.sleep(PAUSE)
    print(f"\n  Stocks with usable data: {len(data)}/{len(symbols)}")
    if not data:
        print("  ALL fetches failed. First errors:")
        for r in reasons:
            print(f"    {r}")
        return

    # Pass 2: RS percentile across the universe, each day
    panel = pd.DataFrame({sym: rs_raw(df['Close']) for sym, df in data.items()})
    rs_rank = panel.rank(axis=1, pct=True) * 100
    rs_map = {sym: rs_rank[sym] for sym in panel.columns}

    # Pass 3: scan
    rows = []
    for sym, df in data.items():
        rows += scan_symbol(sym, df, rs_map[sym], start, end, bench)

    res = pd.DataFrame(rows)
    if not res.empty:
        res = res.sort_values(['signal_date', 'symbol']).reset_index(drop=True)

    if args.mode == 'live':
        print(f"\nSignals in the last 5 days: {len(res)}")
        if not res.empty:
            print(res.drop(columns=[c for c in res.columns if c.startswith('bench_') or c in HORIZONS]).to_string(index=False))
    else:
        summarize(res)

    if res.empty:
        return
    fname = f"vcp_minervini_{args.mode}_{pd.Timestamp.now():%Y%m%d_%H%M}.csv"
    res.to_csv(fname, index=False)
    print(f"\nSaved: {os.path.abspath(fname)}")

    if args.mode == 'live':
        send_email(res, f"Minervini VCP signals - {today:%Y-%m-%d}")


if __name__ == '__main__':
    main()
