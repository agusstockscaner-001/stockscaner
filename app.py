"""
AI Stock Scanner - Versi Cloudflare Proxy
Data Yahoo Finance lewat Cloudflare Worker (anti-block)
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from urllib.parse import quote

st.set_page_config(page_title="AI Stock Scanner", page_icon="🎯", layout="wide", initial_sidebar_state="collapsed")

# ============================================================
# GANTI URL INI DENGAN URL CLOUDFLARE WORKER KAMU
# ============================================================
PROXY = "https://yahoo-proxy.agusstockscaner.workers.dev/?url="
# ============================================================

st.markdown("""
<style>
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 1rem !important; max-width: 100%; }
    .stock-card { background: linear-gradient(135deg,#0f1520,#131929); border:1px solid #1a2535; border-radius:12px; padding:14px; margin-bottom:10px; }
    .priority-card { border:1px solid #2d5a3d; box-shadow:0 0 15px rgba(0,255,136,0.15); }
    .gem-card { border:1px solid #1a3a5a; }
    .trap-card { border:1px solid #5a1a1a; }
    .badge { display:inline-block; padding:3px 10px; border-radius:12px; font-size:11px; font-weight:700; font-family:monospace; }
    .stButton button { width:100%; border-radius:8px; font-weight:600; }
    @media (max-width:768px){ .stock-card{padding:12px;font-size:13px;} h1{font-size:22px!important;} }
</style>
""", unsafe_allow_html=True)

SEKTOR = {
    "BANK": ["BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","BBTN.JK","BRIS.JK"],
    "TELCO": ["TLKM.JK","ISAT.JK","EXCL.JK","TOWR.JK"],
    "TAMBANG": ["ADRO.JK","ITMG.JK","PTBA.JK","ANTM.JK","INCO.JK","MDKA.JK","AMMN.JK"],
    "KONSUMER": ["ICBP.JK","INDF.JK","CPIN.JK","JPFA.JK","AMRT.JK","UNVR.JK","MYOR.JK"],
    "ENERGI": ["PGAS.JK","MEDC.JK","ADMR.JK"],
    "INDUSTRI": ["ASII.JK","UNTR.JK","AKRA.JK","SMGR.JK","INTP.JK"],
    "PROPERTI": ["CTRA.JK","SMRA.JK","PWON.JK"],
    "KESEHATAN": ["KLBF.JK","SIDO.JK"],
    "RITEL": ["ACES.JK","MAPI.JK","MAPA.JK"],
    "TEKNOLOGI": ["GOTO.JK"],
}
WATCHLIST = [s for l in SEKTOR.values() for s in l]

@st.cache_data(ttl=300)
def fetch_chart(symbol):
    yahoo = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=6mo&interval=1d"
    try:
        r = requests.get(PROXY + quote(yahoo, safe=""), timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
        result = data["chart"]["result"][0]
        q = result["indicators"]["quote"][0]
        clean = []
        for o,h,l,c,v in zip(q["open"],q["high"],q["low"],q["close"],q["volume"]):
            if all(x is not None for x in [o,h,l,c,v]) and o>0:
                clean.append((o,h,l,c,v))
        if len(clean) < 30:
            return None
        o,h,l,c,v = zip(*clean)
        return {"open":list(o),"high":list(h),"low":list(l),"close":list(c),"volume":list(v)}
    except Exception:
        return None

@st.cache_data(ttl=3600)
def fetch_fundamental(symbol):
    yahoo = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}?modules=defaultKeyStatistics,financialData,summaryDetail"
    try:
        r = requests.get(PROXY + quote(yahoo, safe=""), timeout=15)
        if r.status_code != 200:
            return None
        result = r.json()["quoteSummary"]["result"][0]
        ks = result.get("defaultKeyStatistics",{})
        fd = result.get("financialData",{})
        sd = result.get("summaryDetail",{})
        def safe(d,k):
            v = d.get(k,{})
            return v.get("raw") if isinstance(v,dict) else None
        return {"per":safe(sd,"trailingPE") or safe(ks,"trailingPE"),"pbv":safe(ks,"priceToBook"),
                "roe":safe(fd,"returnOnEquity"),"der":safe(fd,"debtToEquity"),"eps_growth":safe(ks,"earningsQuarterlyGrowth")}
    except Exception:
        return None

def ema(d,p):
    if len(d)<p: return []
    out=[sum(d[:p])/p]; m=2/(p+1)
    for x in d[p:]: out.append((x-out[-1])*m+out[-1])
    return out
def rsi(d,p=14):
    if len(d)<p+1: return 50
    g=l=0
    for i in range(1,p+1):
        x=d[-i]-d[-i-1]
        if x>=0: g+=x
        else: l+=abs(x)
    ag,al=g/p,l/p
    if al==0: return 100
    return 100-(100/(1+ag/al))
def macd(d):
    e12,e26=ema(d,12),ema(d,26)
    if not e12 or not e26: return 0,0
    n=min(len(e12),len(e26))
    m=[e12[-n+i]-e26[-n+i] for i in range(n)]
    s=ema(m,9)
    return m[-1],(s[-1] if s else 0)

def score_fund(f):
    if not f: return 50,"N/A"
    sc,n=0,0
    if f.get("per") and f["per"]>0:
        per=f["per"]; sc+=90 if per<10 else 80 if per<15 else 65 if per<20 else 45 if per<30 else 25; n+=1
    if f.get("pbv") and f["pbv"]>0:
        pbv=f["pbv"]; sc+=95 if pbv<1 else 80 if pbv<2 else 60 if pbv<3 else 40 if pbv<5 else 20; n+=1
    if f.get("roe") is not None:
        roe=f["roe"]*100; sc+=95 if roe>20 else 80 if roe>15 else 60 if roe>10 else 40 if roe>5 else 25 if roe>0 else 5; n+=1
    if f.get("der") is not None:
        der=f["der"]; sc+=90 if der<50 else 75 if der<100 else 55 if der<150 else 35 if der<200 else 15; n+=1
    if n==0: return 50,"N/A"
    fin=sc/n
    lbl="💎 EXCELLENT" if fin>=75 else "✅ GOOD" if fin>=60 else "⚠️ FAIR" if fin>=45 else "❌ POOR"
    return fin,lbl

def analyze(symbol, mbonus):
    d=fetch_chart(symbol)
    if not d: return None
    op,hi,lo,cl,vol=d["open"],d["high"],d["low"],d["close"],d["volume"]
    harga=cl[-1]
    e20,e50=ema(cl,20),ema(cl,50)
    if not e20 or not e50: return None
    avgv=sum(vol[-20:])/20
    vr=vol[-1]/avgv if avgv>0 else 0
    rv=rsi(cl); ml,ms=macd(cl)
    score=0
    if harga>e20[-1]: score+=3
    if harga>e50[-1]: score+=3
    if e20[-1]>e50[-1]: score+=4
    if 45<=rv<=68: score+=4
    elif rv>75: score-=4
    if ml>ms: score+=4
    if vr>=1.8: score+=5
    elif vr>=1.3: score+=3
    score+=mbonus
    sup=min(lo[-20:]); res=max(hi[-21:-1])
    rr=(res-harga)/(harga-sup) if harga>sup else 0
    crange=hi[-1]-lo[-1]
    if crange<=0: return None
    cpos=(cl[-1]-lo[-1])/crange
    nearhigh=cpos>=0.7
    of=0
    if nearhigh: of+=4
    if vr>=1.5: of+=4
    if cl[-1]>op[-1]: of+=2
    cont=0
    if lo[-1]>lo[-2]: cont+=3
    if nearhigh: cont+=2
    if vr>=1.3: cont+=2
    upper=hi[-1]-cl[-1]; body=abs(cl[-1]-op[-1])
    dist=vr>=2 and upper>body and cpos<0.5
    if dist: score-=6
    absorb=vr>=1.5 and nearhigh and (hi[-1]-lo[-1])/lo[-1]*100<4
    if absorb: score+=4
    bo=harga>res and vr>=1.3 and nearhigh
    if bo: score+=5
    fake=hi[-1]>res and harga<res and vr>=1.3
    if fake: score-=7
    fp=score+of+cont
    fund=fetch_fundamental(symbol)
    fs,fl=score_fund(fund)
    if fs<30: fp-=8
    if fake or dist: dec="🚫 AVOID"
    elif fp>=32 and rr>=1.5 and fs>=50: dec="🔥 PRIORITY BUY"
    elif fp>=25 and fs>=45: dec="🎯 SWING TARGET"
    elif fp>=18: dec="👀 WATCH"
    else: dec="🚫 AVOID"
    if fake or dist or fs<30: risk="HIGH"
    elif rr>=1.8 and nearhigh and fs>=60: risk="LOW"
    else: risk="MEDIUM"
    conf=max(0,min(95,int(fp*2.2+(fs-50)*0.2)))
    tpct=((res-harga)/harga)*100
    slpct=((harga-sup)/harga)*100
    flow="🐋 ACCUMULATION" if absorb else "⚠️ DISTRIBUTION" if dist else "NORMAL"
    sector=next((s for s,l in SEKTOR.items() if symbol in l),"LAINNYA")
    return {"symbol":symbol.replace(".JK",""),"sector":sector,"harga":harga,
            "change":(cl[-1]-cl[-2])/cl[-2]*100,"fp":fp,"rr":rr,"conf":conf,"risk":risk,
            "flow":flow,"dec":dec,"fs":fs,"fl":fl,"tpct":tpct,"slpct":slpct,"rsi":rv,"vr":vr,
            "is_gem":fp>=25 and fs>=70,"is_trap":fp>=25 and fs<40,"chart":cl[-30:]}

def regime():
    d=fetch_chart("^JKSE")
    if not d: return "UNKNOWN",0
    cl=d["close"]; e20,e50=ema(cl,20),ema(cl,50)
    if not e20 or not e50: return "UNKNOWN",0
    h=cl[-1]
    if h>e20[-1]>e50[-1]: return "🟢 STRONG BULLISH",4
    elif h>e50[-1]: return "🟡 NEUTRAL",0
    else: return "🔴 BEARISH",-4

fmtp=lambda p:"Rp "+format(round(p),",")
GRADE=lambda c:("#00ff88" if c>=82 else "#2ed573" if c>=74 else "#a3ff6e" if c>=65 else "#ffd32a" if c>=55 else "#ff6b81")

# UI
c1,c2=st.columns([3,1])
with c1:
    st.markdown("# 🎯 AI Stock Scanner")
    st.caption(f"LQ45 · Swing 2-5 hari · Target 5%+ · {datetime.now().strftime('%d %b %Y · %H:%M')}")
with c2:
    if st.button("🔄 Refresh", use_container_width=True, type="primary"):
        st.cache_data.clear(); st.rerun()

reg,bonus=regime()
if reg=="UNKNOWN":
    st.error("⚠️ Gagal ambil data IHSG. Lihat detail error di bawah.")
    # Diagnostic
    with st.expander("🔍 Detail Diagnosa (klik untuk lihat)"):
        test_url = "https://query1.finance.yahoo.com/v8/finance/chart/BBCA.JK?range=6mo&interval=1d"
        full = PROXY + quote(test_url, safe="")
        st.write("URL yang dipakai app:")
        st.code(full)
        try:
            tr = requests.get(full, timeout=15)
            st.write(f"Status code: {tr.status_code}")
            st.write(f"Response (200 char pertama):")
            st.code(tr.text[:200])
        except Exception as e:
            st.write(f"Error koneksi: {e}")
else:
    st.info(f"**Market Regime IHSG:** {reg}")

if 'results' not in st.session_state:
    st.session_state.results=None
if st.session_state.results is None:
    prog=st.progress(0,text="Memindai saham...")
    res=[]
    for i,s in enumerate(WATCHLIST):
        prog.progress((i+1)/len(WATCHLIST),text=f"Scanning {s}... ({i+1}/{len(WATCHLIST)})")
        r=analyze(s,bonus)
        if r: res.append(r)
    prog.empty()
    st.session_state.results=sorted(res,key=lambda x:x["conf"],reverse=True)
results=st.session_state.results or []

if not results:
    st.warning("Belum ada data saham yang berhasil dimuat. Klik Refresh atau cek URL proxy.")

def card(s,cls="stock-card"):
    color={"🔥 PRIORITY BUY":"#00ff88","🎯 SWING TARGET":"#4da6ff","👀 WATCH":"#ffd32a","🚫 AVOID":"#ff4757"}.get(s["dec"],"#888")
    tp=s["harga"]*(1+s["tpct"]/100); sl=s["harga"]*(1-s["slpct"]/100)
    cc="#00ff88" if s["change"]>=0 else "#ff4757"; cs="+" if s["change"]>=0 else ""
    st.markdown(f"""<div class="stock-card {cls}">
    <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
    <div><div style="font-size:20px;font-weight:800;color:#fff;">{s['symbol']}</div>
    <div style="font-size:11px;color:#888;">{s['sector']}</div></div>
    <div style="text-align:right;"><div style="font-size:18px;font-weight:700;color:#fff;">{fmtp(s['harga'])}</div>
    <div style="font-size:12px;color:{cc};">{cs}{s['change']:.2f}%</div></div></div>
    <div style="background:#0a0d14;border-radius:8px;padding:10px;margin-bottom:10px;">
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;text-align:center;">
    <div><div style="font-size:10px;color:#666;">CONFIDENCE</div><div style="font-size:18px;font-weight:700;color:{color};">{s['conf']}%</div></div>
    <div><div style="font-size:10px;color:#666;">TARGET</div><div style="font-size:16px;font-weight:700;color:#00ff88;">+{s['tpct']:.1f}%</div></div>
    <div><div style="font-size:10px;color:#666;">R/R</div><div style="font-size:16px;font-weight:700;color:#ffd32a;">{s['rr']:.1f}x</div></div></div></div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;font-size:12px;">
    <div style="background:#0a0d14;padding:6px 10px;border-radius:6px;"><span style="color:#666;">🎯 Target:</span> <span style="color:#fff;">{fmtp(tp)}</span></div>
    <div style="background:#0a0d14;padding:6px 10px;border-radius:6px;"><span style="color:#666;">🛑 Stop:</span> <span style="color:#fff;">{fmtp(sl)}</span></div></div>
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px;">
    <span class="badge" style="background:{color}22;color:{color};border:1px solid {color}66;">{s['dec']}</span>
    <span class="badge" style="background:#2a4060;color:#ccc;">Fund: {s['fl']}</span>
    <span class="badge" style="background:#2a4060;color:#ccc;">Risk: {s['risk']}</span></div>
    <div style="font-size:11px;color:#666;">RSI: {s['rsi']:.0f} · Vol: {s['vr']:.1f}x · Flow: {s['flow']}</div></div>""",unsafe_allow_html=True)

t1,t2,t3,t4,t5=st.tabs(["🔥 Hotlist","💎 Hidden Gem","⚠️ Value Trap","📊 Semua","ℹ️ Info"])
with t1:
    hot=[s for s in results if "PRIORITY BUY" in s["dec"] or "SWING TARGET" in s["dec"]]
    st.markdown(f"### 🔥 {len(hot)} Sinyal Buy")
    if not hot: st.info("Tidak ada sinyal kuat saat ini.")
    for s in hot: card(s,"priority-card")
with t2:
    gems=[s for s in results if s["is_gem"]]
    st.markdown(f"### 💎 {len(gems)} Hidden Gem")
    if not gems: st.info("Belum ada hidden gem.")
    for s in gems: card(s,"gem-card")
with t3:
    traps=[s for s in results if s["is_trap"]]
    st.markdown(f"### ⚠️ {len(traps)} Value Trap")
    if not traps: st.info("Tidak ada value trap.")
    for s in traps: card(s,"trap-card")
with t4:
    st.markdown(f"### 📊 Semua ({len(results)})")
    mc=st.slider("Min Confidence",0,95,50,5)
    fil=[s for s in results if s["conf"]>=mc]
    if fil:
        df=pd.DataFrame([{"Saham":s["symbol"],"Sektor":s["sector"],"Harga":fmtp(s["harga"]),
            "Conf%":s["conf"],"Target%":f"+{s['tpct']:.1f}","R/R":f"{s['rr']:.1f}x",
            "Sinyal":s["dec"].split()[1] if " " in s["dec"] else s["dec"]} for s in fil])
        st.dataframe(df,use_container_width=True,hide_index=True,height=500)
with t5:
    st.markdown("""
    ### ℹ️ Info
    **Data:** Yahoo Finance via Cloudflare Worker proxy (anti-block).
    **Confidence:** gabungan teknikal (70%) + fundamental (30%).
    
    ### ⚠️ Disclaimer
    - Data delay ~15 menit
    - Confidence = estimasi, BUKAN jaminan profit
    - Win rate realistis swing: 55-65%
    - Selalu pakai stop loss
    - Tools edukasi, bukan rekomendasi investasi
    """)
