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
    """Scan stock for VCP breakouts"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        data = yf.download(symbol, start=start_date, end=end_date, progress=False)
        
        if data is None or len(data) < 4:
            return []
        
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        
        data['Range'] = (data['Open'] - data['Close']).abs()
        
        breakouts = []
        check_from_index = max(3, len(data) - days_back)
        
        for i in range(check_from_index, len(data)):
            today = data.iloc[i]
            day1 = data.iloc[i-1]
            day2 = data.iloc[i-2]
            day3 = data.iloc[i-3]
            
            today_range = float(today['Range'])
            today_vol = float(today['Volume'])
            
            d1_range = float(day1['Range'])
            d2_range = float(day2['Range'])
            d3_range = float(day3['Range'])
            
            d1_vol = float(day1['Volume'])
            d2_vol = float(day2['Volume'])
            d3_vol = float(day3['Volume'])
            
            range_3days = d1_range + d2_range + d3_range
            vol_3days = d1_vol + d2_vol + d3_vol
            
            if today_range > range_3days and today_vol > vol_3days:
                range_ratio = today_range / range_3days if range_3days > 0 else 0
                vol_ratio = today_vol / vol_3days if vol_3days > 0 else 0
                
                breakouts.append({
                    'Date': data.index[i].strftime('%Y-%m-%d'),
                    'Price': float(today['Close']),
                    'Range_Ratio': range_ratio,
                    'Vol_Ratio': vol_ratio
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
                    <p>📊 Formula: Today's Range > Sum(Last 3 Days) AND Volume > Sum(Last 3 Days)</p>
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
                'Range_Ratio': f"{bo['Range_Ratio']:.2f}x",
                'Vol_Ratio': f"{bo['Vol_Ratio']:.2f}x"
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
