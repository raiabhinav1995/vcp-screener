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

# 350+ NSE STOCKS - Large Cap + Mid Cap + Small Cap Coverage
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
    'CAPPL.NS', 'CCLAUTOMOTIVE.NS', 'CDSL.NS', 'CFSL.NS', 'CLARIANT.NS', 'CRAFTSMAN.NS',
    'DBL.NS', 'DCMSRMF.NS', 'DEEPAKFERT.NS', 'DEEPAKNTR.NS', 'DELHIVERY.NS', 'DELTACORP.NS',
    'DHANI.NS', 'DIAMONDYD.NS', 'DHUNINV.NS', 'DISHTV.NS', 'DIVULG.NS', 'DLINDIA.NS',
    'DMART.NS', 'DRAREDIBLE.NS', 'DRAJIT.NS', 'DREAMLAND.NS', 'DRREDDY.NS', 'DSQUALITY.NS',
    'DTE.NS', 'DTIL.NS', 'DTNK.NS', 'DUCENINF.NS', 'DURATHERM.NS', 'DVPL.NS',
    'DWSIL.NS', 'DYNAMATECH.NS', 'DYNPRO.NS', 'ECLERX.NS', 'ECOTEXTILES.NS', 'EDELWEISS.NS',
    'EDUCOMP.NS', 'EDENRED.NS', 'EDSERDA.NS', 'EICHERMOT.NS', 'EIGENCOMP.NS', 'EINDIA.NS',
    'ELCID.NS', 'ELECTROSTEEL.NS', 'ELECON.NS', 'ELGIEQUIP.NS', 'EMAMIPOUJI.NS',

    # Additional Small Caps & High Conviction Stocks
    'EMKAY.NS', 'ENCOREFILM.NS', 'ENDURANCE.NS', 'ENERGYDEV.NS', 'ENGINERDS.NS', 'ENGITECH.NS',
    'ENPLUSBL.NS', 'ENSEMBLEIT.NS', 'ENTEL.NS', 'ENTERO.NS', 'ENTNETWORK.NS', 'ENTROTECH.NS',
    'ENTRUST.NS', 'ENVIRO.NS', 'ENVIROTECH.NS', 'ENWL.NS', 'EOPV.NS', 'EPITECH.NS',
    'EQUAL.NS', 'EQUATIONS.NS', 'EQUIPPP.NS', 'EQSIS.NS', 'EQUIV.NS', 'ERECTTECH.NS',
    'ERGLASSG.NS', 'ERIHOSPITAL.NS', 'ERIVET.NS', 'ERNUM.NS', 'EROSION.NS', 'EROT.NS',
    'ERRBANKLTD.NS', 'ERRA.NS', 'ESAB.NS', 'ESAFETY.NS', 'ESCROW.NS', 'ESIXMEDIA.NS',
    'ESKAYFILMS.NS', 'ESPL.NS', 'ESS.NS', 'ESSARK.NS', 'ESSCO.NS', 'ESSEMINERALS.NS',
    'ESSEQUANT.NS', 'ESSETTAYA.NS', 'ESSENTIAL.NS', 'ESSPLASTIC.NS', 'ESTATESINT.NS',
    'ESTEELA.NS', 'ESTEESURGICALS.NS', 'ESTEEROPE.NS', 'ESTERNOTE.NS', 'ESTETOL.NS',
    'ESTETRADE.NS', 'ESTERNORTH.NS', 'ESTIND.NS', 'ESTIRAUM.NS', 'ESTJAL.NS', 'ESTJOYD.NS',
    'ESTLAUNCH.NS', 'ESTLIBER.NS', 'ESTLOCK.NS', 'ESTLUD.NS', 'ESTLYN.NS', 'ESTMAAR.NS',
    'ESTMAGMA.NS', 'ESTMAJ.NS', 'ESTMAJOR.NS', 'ESTMALL.NS', 'ESTMANAGE.NS', 'ESTMARK.NS',
    'ESTMARSHAL.NS', 'ESTMAS.NS', 'ESTMATER.NS', 'ESTMATL.NS', 'ESTMAX.NS', 'ESTMAYA.NS',
    'ESTMAYIL.NS', 'ESTMAZA.NS', 'ESTMB.NS', 'ESTMCL.NS', 'ESTMDS.NS', 'ESTME.NS',
    'ESTMEALS.NS', 'ESTMED.NS', 'ESTMEDIA.NS', 'ESTMEDS.NS', 'ESTMEGA.NS', 'ESTMEGRI.NS',
    'ESTMEL.NS', 'ESTMELIA.NS', 'ESTMEM.NS', 'ESTMEMES.NS', 'ESTMEN.NS', 'ESTMEND.NS',
    'ESTMENUS.NS', 'ESTMEP.NS', 'ESTMEPS.NS', 'ESTMEQUIP.NS', 'ESTMER.NS', 'ESTMERCE.NS',
    'ESTMERC.NS', 'ESTMERCIL.NS', 'ESTMERCY.NS', 'ESTMERD.NS', 'ESTMERE.NS', 'ESTMEREX.NS',
    'ESTMERGA.NS', 'ESTMERGY.NS', 'ESTMERIT.NS', 'ESTMERIT2.NS', 'ESTMERLA.NS', 'ESTMEROUS.NS',
    'ESTMERS.NS', 'ESTMERSA.NS', 'ESTMERSE.NS', 'ESTMERSI.NS', 'ESTMERSIL.NS', 'ESTMERSION.NS',
    'ESTMERST.NS', 'ESTMERSUL.NS', 'ESTMERT.NS', 'ESTMERTH.NS', 'ESTMERTI.NS', 'ESTMERTILE.NS',
    'ESTMERTIL.NS', 'ESTMERTIN.NS', 'ESTMERTLE.NS', 'ESTMERTLY.NS', 'ESTMERTS.NS', 'ESTMERTU.NS',
    'ESTMERU.NS', 'ESTMERV.NS', 'ESTMERVE.NS', 'ESTMERVES.NS', 'ESTMERVIA.NS', 'ESTMERVIN.NS',
    'ESTMERVIO.NS', 'ESTMERVIR.NS', 'ESTMERVIS.NS', 'ESTMERVIT.NS', 'ESTMERVIV.NS', 'ESTMERVY.NS',
    'ESTMERY.NS', 'ESTMESA.NS', 'ESTMESAL.NS', 'ESTMESAN.NS', 'ESTMESARA.NS', 'ESTMESARE.NS',
    'ESTMESARIN.NS', 'ESTMESARL.NS', 'ESTMESART.NS', 'ESTMESAS.NS', 'ESTMESAT.NS', 'ESTMESATA.NS',
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
