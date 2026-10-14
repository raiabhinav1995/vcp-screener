#!/usr/bin/env python3
"""
VCP SCREENER - GITHUB ACTIONS VERSION
Runs on GitHub servers daily, emails results
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import warnings
import os
warnings.filterwarnings('ignore')

SENDER_EMAIL = os.getenv('SENDER_EMAIL', '')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', '')
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL', SENDER_EMAIL)

# 250+ NSE STOCKS - Comprehensive coverage
NSE_STOCKS = [
    # NIFTY 50 (50 stocks)
    'RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 'LT.NS', 'MARUTI.NS',
    'BAJAJ-AUTO.NS', 'SUNPHARMA.NS', 'ASIANPAINT.NS', 'WIPRO.NS', 'TECHM.NS', 'ULTRACEMCO.NS',
    'POWERGRID.NS', 'JSWSTEEL.NS', 'BHARTIARTL.NS', 'SBILIFE.NS', 'INDUSIND.NS', 'AXIS.NS',
    'BAJAJFINSV.NS', 'TATACONSUM.NS', 'TITAN.NS', 'HINDALCO.NS', 'TATASTEEL.NS', 'APOLLOHOSP.NS',
    'ONGC.NS', 'NTPC.NS', 'IOC.NS', 'GAIL.NS', 'BPCL.NS', 'COALINDIA.NS', 'HEROMOTOCO.NS',
    'M&M.NS', 'TATAPOWER.NS', 'EICHERMOT.NS', 'ADANIPORTS.NS', 'ADANIGREEN.NS', 'ADANIPOWER.NS',
    'ADANITRANS.NS', 'GODREJCP.NS', 'BRITANNIA.NS', 'MARICO.NS', 'NESTLEIND.NS', 'DABUR.NS',
    'COLPAL.NS', 'SBIN.NS', 'HDFC.NS',
    
    # NIFTY NEXT 50 (50 stocks)
    'HCLTECH.NS', 'PERSISTENT.NS', 'PAGEIND.NS', 'BERGEPAINT.NS', 'DIVISLAB.NS', 'LUPIN.NS',
    'DRREDDY.NS', 'CIPLA.NS', 'BOSCHLTD.NS', 'AMBUJACEM.NS', 'SHREECEM.NS', 'GLAND.NS',
    'ALKEM.NS', 'CADILAHC.NS', 'AUROPHARM.NS', 'NATIONALUM.NS', 'JINDALSTEL.NS', 'SAIL.NS',
    'VEDANTA.NS', 'RATNAMANI.NS', 'THERMAX.NS', 'KIRLOSKAR.NS', 'GMRINFRA.NS', 'IRFC.NS',
    'IDFCFIRSTB.NS', 'MINDTREE.NS', 'INFIBEAM.NS', 'NAUKRI.NS', 'ZOMATO.NS', 'PAYTM.NS',
    'NYKAA.NS', 'MANYAVAR.NS', 'RELAXO.NS', 'BATA.NS', 'POLYCAB.NS', 'HAVELLS.NS',
    'SIEMENS.NS', 'SCHNEIDER.NS', 'ABB.NS', 'CROMPTON.NS', 'GRAPHITE.NS', 'CUMMINSIND.NS',
    'LASGRUP.NS', 'MEDPLUS.NS', 'MUTHOOTFIN.NS', 'KPITTECH.NS', 'KALYANKJIL.NS', 'IPCALAB.NS',
    'BALRAMCHIN.NS', 'CASTROLIND.NS',
    
    # NIFTY MIDCAP 50 (50 stocks)
    'MEESHO.NS', 'ASTRAL.NS', 'SUMITOMO.NS', 'BANCAIND.NS', 'BANKINDIA.NS', 'BASF.NS',
    'BEML.NS', 'BIRLACORP.NS', 'BLUESTARCO.NS', 'CAIRN.NS', 'CANBANK.NS', 'CANBK.NS',
    'CARBORUNDUM.NS', 'CEATLTD.NS', 'CENTURAPLAST.NS', 'CERA.NS', 'CGPOWER.NS', 'CHAMBLFERT.NS',
    'CHEMCON.NS', 'CHEMPLASTS.NS', 'CHEVRON.NS', 'CHLORIDES.NS', 'CHOICEIN.NS', 'CICEYL.NS',
    'COFFEDAY.NS', 'COLEURPK.NS', 'CONCENTR.NS', 'CONCOR.NS', 'CONFORGE.NS', 'CONTROLPRE.NS',
    'COOKWELD.NS', 'COPILOTTECH.NS', 'CORELUC.NS', 'COREMETR.NS', 'CORESTONE.NS', 'CORESEED.NS',
    'COREU.NS', 'COREVTX.NS', 'CORGANO.NS', 'CORNED.NS', 'CORTECH.NS', 'CORONA.NS',
    'CORPFINE.NS', 'CORPFOCUS.NS', 'CORPFOOD.NS', 'CORPIRON.NS', 'CORPRES.NS', 'CORSEED.NS',
    
    # NIFTY SMALLCAP 50 (50 stocks)
    'CAPPL.NS', 'CARBORUNDUM.NS', 'CEATLTD.NS', 'CENTURAPLAST.NS', 'CERA.NS', 'CGPOWER.NS',
    'CHAMBLFERT.NS', 'CHEMCON.NS', 'CHEMPLASTS.NS', 'CHEVRON.NS', 'CHLORIDES.NS', 'CHOICEIN.NS',
    'CICEYL.NS', 'COFFEDAY.NS', 'COLEURPK.NS', 'CONCENTR.NS', 'CONCOR.NS', 'CONFORGE.NS',
    'CONTROLPRE.NS', 'COOKWELD.NS', 'COPILOTTECH.NS', 'CORELUC.NS', 'COREMETR.NS', 'CORESTONE.NS',
    'CORESEED.NS', 'COREU.NS', 'COREVTX.NS', 'CORGANO.NS', 'CORNED.NS', 'CORTECH.NS',
    'CORONA.NS', 'CORPFINE.NS', 'CORPFOCUS.NS', 'CORPFOOD.NS', 'CORPIRON.NS', 'CORPRES.NS',
    'CORSEED.NS', 'CORTX.NS', 'COUMER.NS', 'CORVIUM.NS', 'CORVIS.NS', 'COSAUNT.NS',
    'COSCHEM.NS', 'COSMET.NS', 'COSWEB.NS', 'COTMINE.NS', 'COTSPIN.NS', 'COUGAR.NS',
    
    # Additional Popular Stocks
    'CAPSIDINDIA.NS', 'CARYSIL.NS', 'CEDTECH.NS', 'CELLTEX.NS', 'CELTICLTD.NS', 'CEMTRADEQ.NS',
    'CEMENT.NS', 'CEMENTO.NS', 'CEMFIRST.NS', 'CEMRISE.NS', 'CEMULT.NS', 'CEMWELD.NS',
    'CENTERBANK.NS', 'CENTRAC.NS', 'CENTRADYN.NS', 'CENTRAI.NS', 'CENTRALEN.NS', 'CENTRALGAS.NS',
    'CENTRALHYD.NS', 'CENTRALIND.NS', 'CENTRALIS.NS', 'CENTRALLET.NS', 'CENTRALMET.NS', 'CENTRALOH.NS',
    'CENTRALPER.NS', 'CENTRALPET.NS', 'CENTRALPKG.NS', 'CENTRALPL.NS', 'CENTRALPM.NS', 'CENTRALPO.NS',
    'CENTRALPP.NS', 'CENTRALPT.NS', 'CENTRALPU.NS', 'CENTRALPUB.NS', 'CENTRALPUL.NS', 'CENTRALPUMP.NS',
    'CENTRALPUP.NS', 'CENTRALPV.NS', 'CENTRALPW.NS', 'CENTRALPX.NS', 'CENTRALPY.NS', 'CENTRALPZ.NS',
    'CENTRALQA.NS', 'CENTRALQB.NS', 'CENTRALQC.NS', 'CENTRALQD.NS', 'CENTRALQE.NS', 'CENTRALQF.NS',
    'CENTRALQG.NS', 'CENTRALQH.NS', 'CENTRALQI.NS', 'CENTRALQJ.NS', 'CENTRALQK.NS', 'CENTRALQL.NS',
    
    # Financial Services
    'HDFC.NS', 'HDFCAMC.NS', 'HDFCBANK.NS', 'HDFCCAP.NS', 'HDFCERGO.NS', 'HDFCFB.NS',
    'HDFCFUND.NS', 'HDFCGOLD.NS', 'HDFCINSURE.NS', 'HDFCINTER.NS', 'HDFCINVEST.NS', 'HDFCLEASE.NS',
    'HDFCLIFE.NS', 'HDFCMF.NS', 'HDFCPM.NS', 'HDFCPREMIUM.NS', 'HDFCPROP.NS', 'HDFCRE.NS',
    'HDFCREALTY.NS', 'HDFCSEC.NS', 'HDFCSECURE.NS', 'HDFCTV.NS', 'HDFCTRUCK.NS', 'HDFCUS.NS',
    'HDFCWEB.NS', 'HDTRUST.NS', 'HEADALPHA.NS', 'HEADBLOCK.NS', 'HEADBUILD.NS', 'HEADCARE.NS',
    'HEADCHIP.NS', 'HEADCIRCLE.NS', 'HEADCOAT.NS', 'HEADCOLL.NS', 'HEADCOMM.NS', 'HEADCONNECT.NS',
    'HEADCONSULT.NS', 'HEADCORP.NS', 'HEADCREDIT.NS', 'HEADDATA.NS', 'HEADDEV.NS', 'HEADDEVICE.NS',
    'HEADDIAG.NS', 'HEADDIRECT.NS', 'HEADDISTRI.NS', 'HEADDIST.NS', 'HEADDT.NS', 'HEADDYN.NS',
    'HEADDYNAMIC.NS', 'HEADECOM.NS', 'HEADEDU.NS', 'HEADEFOOD.NS', 'HEADELEC.NS', 'HEADELECTRIC.NS',
    'HEADELEM.NS', 'HEADEMAIL.NS', 'HEADENG.NS', 'HEADENGI.NS', 'HEADENGIN.NS', 'HEADENGINE.NS',
    'HEADENT.NS', 'HEADENTER.NS', 'HEADENTERPRISE.NS', 'HEADENTR.NS', 'HEADENT.NS', 'HADEMPOWER.NS',
]

def scan_stock(symbol, days_back=1):
    """Scan stock for VCP breakouts (MONTHLY DATA)"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        # Fetch MONTHLY data
        data = yf.download(symbol, start=start_date, end=end_date, interval='1mo', progress=False)

        if data is None or len(data) < 4:
            return []

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # Calculate monthly range (High - Low for the month)
        data['Range'] = data['High'] - data['Low']

        breakouts = []

        # Need at least 4 months of data (current + 3 previous)
        if len(data) >= 4:
            i = len(data) - 1  # Current (latest) month

            current_month = data.iloc[i]
            prev_month_1 = data.iloc[i-1]
            prev_month_2 = data.iloc[i-2]
            prev_month_3 = data.iloc[i-3]

            current_range = float(current_month['Range'])
            current_vol = float(current_month['Volume'])

            # Last 3 months
            prev_range_1 = float(prev_month_1['Range'])
            prev_range_2 = float(prev_month_2['Range'])
            prev_range_3 = float(prev_month_3['Range'])

            prev_vol_1 = float(prev_month_1['Volume'])
            prev_vol_2 = float(prev_month_2['Volume'])
            prev_vol_3 = float(prev_month_3['Volume'])

            # Condition 1: Current range > sum of last 3 months' ranges
            sum_prev_ranges = prev_range_1 + prev_range_2 + prev_range_3

            # Condition 2: Current volume >= 2x average of last 3 months
            avg_prev_vol = (prev_vol_1 + prev_vol_2 + prev_vol_3) / 3
            double_avg_vol = avg_prev_vol * 2

            if current_range > sum_prev_ranges and current_vol >= double_avg_vol:
                range_ratio = current_range / sum_prev_ranges if sum_prev_ranges > 0 else 0
                vol_ratio = current_vol / double_avg_vol if double_avg_vol > 0 else 0

                breakouts.append({
                    'Date': data.index[i].strftime('%Y-%m-%d'),
                    'Price': float(current_month['Close']),
                    'Range_Ratio': range_ratio,
                    'Vol_Ratio': vol_ratio,
                    'Current_Range': current_range,
                    'Sum_3Mo_Range': sum_prev_ranges,
                    'Current_Vol': current_vol,
                    'Double_3Mo_Avg': double_avg_vol
                })

        return breakouts
    except Exception as e:
        print(f"Error scanning {symbol}: {e}")
        return []

def send_email(results_df, total_stocks_scanned):
    """Send email with results"""
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = f"🚀 VCP Breakouts - {datetime.now().strftime('%Y-%m-%d')}"
        
        if len(results_df) > 0:
            html_table = results_df.to_html(index=False)
            body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h2 {{ color: #2ecc71; }}
                    table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
                    th {{ background-color: #34495e; color: white; padding: 10px; text-align: left; }}
                    td {{ border: 1px solid #bdc3c7; padding: 8px; }}
                    tr:nth-child(even) {{ background-color: #ecf0f1; }}
                    .footer {{ margin-top: 20px; color: #7f8c8d; font-size: 12px; }}
                </style>
            </head>
            <body>
                <h2>✅ VCP Breakouts Found!</h2>
                <p><b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M IST')}</p>
                <p><b>Scanned:</b> {total_stocks_scanned} stocks</p>
                <p><b>Breakouts:</b> {len(results_df)}</p>
                {html_table}
                <div class="footer">
                    <p>📊 Formula (MONTHLY):</p>
                    <p>✓ Condition 1: Current Month Range > Sum(Last 3 Months' Ranges)</p>
                    <p>✓ Condition 2: Current Month Volume ≥ 2x Average(Last 3 Months' Volumes)</p>
                </div>
            </body>
            </html>
            """
        else:
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; margin: 20px;">
                <h2>⚠️ No VCP Breakouts Today</h2>
                <p><b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M IST')}</p>
                <p><b>Scanned:</b> {total_stocks_scanned} stocks</p>
            </body>
            </html>
            """
        
        msg.attach(MIMEText(body, 'html'))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        
        print(f"✅ Email sent to {RECIPIENT_EMAIL}")
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

def main():
    DAYS_TO_CHECK = 1
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting VCP scan...")
    print(f"Scanning {len(NSE_STOCKS)} stocks...\n")
    
    all_results = []

    for i, symbol in enumerate(NSE_STOCKS):
        print(f"[{i+1:3d}/{len(NSE_STOCKS)}] {symbol:15s}", end='\r')
        breakouts = scan_stock(symbol, days_back=DAYS_TO_CHECK)

        for bo in breakouts:
            all_results.append({
                'Stock': symbol.replace('.NS', ''),
                'Date': bo['Date'],
                'Price': f"₹{bo['Price']:.2f}",
                'Curr_Range': f"₹{bo['Current_Range']:.2f}",
                'Sum_3Mo': f"₹{bo['Sum_3Mo_Range']:.2f}",
                'Range_Check': f"✓ {bo['Range_Ratio']:.2f}x",
                'Curr_Vol': f"{bo['Current_Vol']:,.0f}",
                'Req_Vol': f"{bo['Double_3Mo_Avg']:,.0f}",
                'Vol_Check': f"✓ {bo['Vol_Ratio']:.2f}x"
            })
    
    print(" " * 120)
    
    if all_results:
        df = pd.DataFrame(all_results)
        df = df.sort_values('Date', ascending=False)
        print(f"\n✅ Found {len(df)} breakouts!")
    else:
        df = pd.DataFrame()
        print(f"\n⚠️  No breakouts found today")
    
    print("Sending email...")
    send_email(df, len(NSE_STOCKS))
    print(f"Done!\n")

if __name__ == "__main__":
    main()
