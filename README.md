# VCP Screener

Daily NSE stock screener using Minervini's VCP (Volatility Contraction Pattern).

## Features
- Scans 70+ Nifty 50 and mid-cap stocks
- Runs automatically every weekday at 4 PM IST
- Emails results with breakout details
- GitHub Actions - no server needed

## Formula
- Today's Range > Sum(Last 3 Days Ranges)
- AND Volume > Sum(Last 3 Days Volumes)

## Results
Saved to Artifacts in GitHub Actions runs
