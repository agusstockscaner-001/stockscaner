"""
=============================================================
 AI STOCK SCANNER - MOBILE APP (Streamlit)
=============================================================
 Cara install di HP:
 1. Deploy ke Streamlit Cloud (gratis): share.streamlit.io
 2. Buka URL di HP browser
 3. "Add to Home Screen" → jadi PWA
=============================================================
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time as time_module
import json

# ─── PAGE CONFIG ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI Stock Scanner",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'About': "AI Stock Scanner v2 - Swing 2-5 hari dengan target 5%+"
    }
)

# ─── CUSTOM CSS (Mobile-Friendly) ────────────────────────────
st.markdown("""
<style>
    /* Mobile-first design */
    .main { padding: 0.5rem 0.5rem; }
    .block-container { padding-top: 1rem !important; max-width: 100%; }
    
    /* Hide Streamlit branding */
    #MainMenu, footer, header { visibility: hidden; }
    
    /* Custom cards */
    .stock-card {
        background: linear-gradient(135deg, #0f1520 0%, #131929 100%);
        border: 1px solid #1a2535;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 10px;
    }
    .priority-card {
        background: linear-gradient(135deg, #0f2520 0%, #143029 100%);
        border: 1px solid #2d5a3d;
        box-shadow: 0 0 15px rgba(0, 255, 136, 0.15);
    }
    .gem-card {
        background: linear-gradient(135deg, #0a2030 0%, #0f2540 100%);
        border: 1px solid #1a3a5a;
    }
    .trap-card {
        background: linear-gradient(135deg, #2a0a0a 0%, #3a0f0f 100%);
        border: 1px solid #5a1a1a;
    }
    
    /* Score badges */
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
        font-family: 'Courier New', monospace;
    }
    .badge-buy { background: #00ff88; color: #000; }
    .badge-watch { background: #ffd32a; color: #000; }
    .badge-avoid { background: #ff4757; color: #fff; }
    
    /* Mobile-optimized buttons */
    .stButton button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
    }
    
    /* Metric styling */
    [data-testid="stMetricValue"] {
        font-family: 'Courier New', monospace;
        font-weight: 700;
    }
    
    /* Dark theme tweaks */
    .stProgress > div > div { background: linear-gradient(90deg, #0066cc, #00ccff); }
    
    /* Responsive grid */
    @media (max-width: 768px) {
        .stock-card { padding: 12px; font-size: 13px; }
        h1 { font-size: 22px !important; }
        h2 { font-size: 18px !important; }
        h3 { font-size: 15px !important; }
    }
</style>
""", unsafe_allow_html=True)

# ─── CONFIG ─────────────────────────────────────────────────
SEKTOR = {
    "BANK": ["BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "BRIS.JK", "BBTN.JK"],
    "TELCO": ["TLKM.JK", "ISAT.JK", "EXCL.JK", "TOWR.JK"],
    "TAMBANG": ["ADRO.JK", "ITMG.JK", "PTBA.JK", "ANTM.JK", "INCO.JK", "MDKA.JK", "AMMN.JK"],
    "KONSUMER": ["ICBP.JK", "INDF.JK", "CPIN.JK", "JPFA.JK", "AMRT.JK", "UNVR.JK", "MYOR.JK"],
    "ENERGI": ["PGAS.JK", "MEDC.JK", "ADMR.JK"],
    "INDUSTRI": ["ASII.JK", "UNTR.JK", "AKRA.JK", "SMGR.JK", "INTP.JK"],
    "PROPERTI": ["CTRA.JK", "SMRA.JK", "PWON.JK"],
    "KESEHATAN": ["KLBF.JK", "SIDO.JK"],
    "RITEL": ["ACES.JK", "MAPI.JK", "MAPA.JK"],
    "TEKNOLOGI": ["GOTO.JK"]
}

WATCHLIST = [s for daftar in SEKTOR.values() for s in daftar]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Stock Scanner)"}

# ─── DATA FETCHING ──────────────────────────────────────────
@st.cache_data(ttl=300)  # cache 5 menit
def fetch_chart(symbol, range_data="6mo", interval="1d"):
    """Fetch OHLCV daily."""
    proxies = [
        f"https://corsproxy.io/?https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={range_data}&interval={interval}",
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={range_data}&interval={interval}",
    ]
    for url in proxies:
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                continue
            data = r.json()
            result = data["chart"]["result"][0]
            q = result["indicators"]["quote"][0]
            clean = []
            for o, h, l, c, v in zip(q["open"], q["high"], q["low"], q["close"], q["volume"]):
                if all(x is not None for x in [o, h, l, c, v]) and o > 0:
                    clean.append((o, h, l, c, v))
            if len(clean) < 30:
                continue
            o, h, l, c, v = zip(*clean)
            return {"open": list(o), "high": list(h), "low": list(l), "close": list(c), "volume": list(v)}
        except Exception:
            continue
    return None

@st.cache_data(ttl=3600)  # cache 1 jam (fundamental jarang berubah)
def fetch_fundamental(symbol):
    """Fetch PER, PBV, ROE, DER."""
    url = f"https://corsproxy.io/?https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}?modules=defaultKeyStatistics,financialData,summaryDetail"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        result = data["quoteSummary"]["result"][0]
        ks = result.get("defaultKeyStatistics", {})
        fd = result.get("financialData", {})
        sd = result.get("summaryDetail", {})

        def safe(d, key):
            v = d.get(key, {})
            return v.get("raw") if isinstance(v, dict) else None

        return {
            "per": safe(sd, "trailingPE") or safe(ks, "trailingPE"),
            "pbv": safe(ks, "priceToBook"),
            "roe": safe(fd, "returnOnEquity"),
            "der": safe(fd, "debtToEquity"),
            "eps_growth": safe(ks, "earningsQuarterlyGrowth"),
        }
    except Exception:
        return None

# ─── INDICATORS ─────────────────────────────────────────────
def ema(data, period):
    if len(data) < period: return []
    out = [sum(data[:period]) / period]
    mult = 2 / (period + 1)
    for p in data[period:]:
        out.append((p - out[-1]) * mult + out[-1])
    return out

def rsi(data, period=14):
    if len(data) < period + 1: return 50
    g, l = 0, 0
    for i in range(1, period + 1):
        d = data[-i] - data[-i-1]
        if d >= 0: g += d
        else: l += abs(d)
    avg_g, avg_l = g/period, l/period
    if avg_l == 0: return 100
    return 100 - (100 / (1 + avg_g/avg_l))

def macd(data):
    e12, e26 = ema(data, 12), ema(data, 26)
    if not e12 or not e26: return 0, 0
    n = min(len(e12), len(e26))
    m = [e12[-n+i] - e26[-n+i] for i in range(n)]
    s = ema(m, 9)
    return m[-1], (s[-1] if s else 0)

# ─── SCORING ────────────────────────────────────────────────
def score_fundamental(fund):
    if not fund: return 50, "N/A"
    score, count = 0, 0
    if fund.get("per") and fund["per"] > 0:
        per = fund["per"]
        s = 90 if per < 10 else 80 if per < 15 else 65 if per < 20 else 45 if per < 30 else 25
        score += s; count += 1
    if fund.get("pbv") and fund["pbv"] > 0:
        pbv = fund["pbv"]
        s = 95 if pbv < 1 else 80 if pbv < 2 else 60 if pbv < 3 else 40 if pbv < 5 else 20
        score += s; count += 1
    if fund.get("roe") is not None:
        roe = fund["roe"] * 100
        s = 95 if roe > 20 else 80 if roe > 15 else 60 if roe > 10 else 40 if roe > 5 else 25 if roe > 0 else 5
        score += s; count += 1
    if fund.get("der") is not None:
        der = fund["der"]
        s = 90 if der < 50 else 75 if der < 100 else 55 if der < 150 else 35 if der < 200 else 15
        score += s; count += 1
    if count == 0: return 50, "N/A"
    final = score / count
    label = "💎 EXCELLENT" if final >= 75 else "✅ GOOD" if final >= 60 else "⚠️ FAIR" if final >= 45 else "❌ POOR"
    return final, label

def analyze(symbol, market_bonus):
    data = fetch_chart(symbol)
    if not data: return None

    op, hi, lo, cl, vol = data["open"], data["high"], data["low"], data["close"], data["volume"]
    harga = cl[-1]
    e20, e50 = ema(cl, 20), ema(cl, 50)
    if not e20 or not e50: return None

    avg_vol = sum(vol[-20:]) / 20
    vr = vol[-1] / avg_vol if avg_vol > 0 else 0
    rsi_v = rsi(cl)
    m_line, m_sig = macd(cl)

    score = 0
    if harga > e20[-1]: score += 3
    if harga > e50[-1]: score += 3
    if e20[-1] > e50[-1]: score += 4
    if 45 <= rsi_v <= 68: score += 4
    elif rsi_v > 75: score -= 4
    if m_line > m_sig: score += 4
    if vr >= 1.8: score += 5
    elif vr >= 1.3: score += 3
    score += market_bonus

    support = min(lo[-20:])
    resistance = max(hi[-21:-1])
    rr = (resistance - harga) / (harga - support) if harga > support else 0

    candle_range = hi[-1] - lo[-1]
    if candle_range <= 0: return None
    close_pos = (cl[-1] - lo[-1]) / candle_range
    near_high = close_pos >= 0.7

    of = 0
    if near_high: of += 4
    if vr >= 1.5: of += 4
    if cl[-1] > op[-1]: of += 2

    cont = 0
    if lo[-1] > lo[-2]: cont += 3
    if near_high: cont += 2
    if vr >= 1.3: cont += 2

    upper = hi[-1] - cl[-1]
    body = abs(cl[-1] - op[-1])
    dist = vr >= 2 and upper > body and close_pos < 0.5
    if dist: score -= 6

    absorb = vr >= 1.5 and near_high and (hi[-1] - lo[-1]) / lo[-1] * 100 < 4
    if absorb: score += 4

    breakout = harga > resistance and vr >= 1.3 and near_high
    if breakout: score += 5

    fake = hi[-1] > resistance and harga < resistance and vr >= 1.3
    if fake: score -= 7

    final_power = score + of + cont

    # Fundamental
    fund = fetch_fundamental(symbol)
    fund_score, fund_label = score_fundamental(fund)
    if fund_score < 30: final_power -= 8

    # Decision
    if fake or dist: decision = "🚫 AVOID"
    elif final_power >= 32 and rr >= 1.5 and fund_score >= 50: decision = "🔥 PRIORITY BUY"
    elif final_power >= 25 and fund_score >= 45: decision = "🎯 SWING TARGET"
    elif final_power >= 18: decision = "👀 WATCH"
    else: decision = "🚫 AVOID"

    if fake or dist or fund_score < 30: risk = "HIGH"
    elif rr >= 1.8 and near_high and fund_score >= 60: risk = "LOW"
    else: risk = "MEDIUM"

    confidence = max(0, min(95, int(final_power * 2.2 + (fund_score - 50) * 0.2)))
    target_pct = ((resistance - harga) / harga) * 100
    sl_pct = ((harga - support) / harga) * 100

    flow = "🐋 ACCUMULATION" if absorb else "⚠️ DISTRIBUTION" if dist else "NORMAL"
    is_gem = final_power >= 25 and fund_score >= 70
    is_trap = final_power >= 25 and fund_score < 40

    sector = next((s for s, l in SEKTOR.items() if symbol in l), "LAINNYA")

    return {
        "symbol": symbol.replace(".JK", ""), "full_symbol": symbol, "sector": sector,
        "harga": harga, "change": (cl[-1] - cl[-2]) / cl[-2] * 100,
        "final_power": final_power, "rr": rr, "confidence": confidence, "risk": risk,
        "flow": flow, "decision": decision, "fund_score": fund_score, "fund_label": fund_label,
        "fund_raw": fund, "target_pct": target_pct, "sl_pct": sl_pct,
        "support": support, "resistance": resistance, "rsi": rsi_v,
        "vol_ratio": vr, "is_gem": is_gem, "is_trap": is_trap,
        "chart_data": cl[-30:]  # last 30 days for sparkline
    }

def check_market_regime():
    data = fetch_chart("^JKSE")
    if not data: return "UNKNOWN", 0
    cl = data["close"]
    e20, e50 = ema(cl, 20), ema(cl, 50)
    if not e20 or not e50: return "UNKNOWN", 0
    h = cl[-1]
    if h > e20[-1] > e50[-1]: return "🟢 STRONG BULLISH", 4
    elif h > e50[-1]: return "🟡 NEUTRAL", 0
    else: return "🔴 BEARISH", -4

# ─── UI ─────────────────────────────────────────────────────
# Header
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("# 🎯 AI Stock Scanner")
    st.caption(f"LQ45 · Swing 2-5 hari · Target 5%+ · {datetime.now().strftime('%d %b %Y · %H:%M')}")
with col2:
    if st.button("🔄 Refresh", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()

# Market Status
with st.container():
    regime, bonus = check_market_regime()
    st.info(f"**Market Regime IHSG:** {regime}")

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔥 Hotlist", "💎 Hidden Gem", "⚠️ Value Trap", "📊 Semua", "ℹ️ Info"])

# Scan all stocks
if 'results' not in st.session_state:
    st.session_state.results = None

# Auto-scan on first load
if st.session_state.results is None:
    progress = st.progress(0, text="Memindai saham...")
    results = []
    for i, sym in enumerate(WATCHLIST):
        progress.progress((i + 1) / len(WATCHLIST), text=f"Scanning {sym}... ({i+1}/{len(WATCHLIST)})")
        r = analyze(sym, bonus)
        if r: results.append(r)
    progress.empty()
    st.session_state.results = sorted(results, key=lambda x: x["confidence"], reverse=True)

results = st.session_state.results or []

# ─── HELPER: Render Stock Card ──────────────────────────────
def render_card(s, card_class="stock-card"):
    decision_color = {
        "🔥 PRIORITY BUY": "#00ff88",
        "🎯 SWING TARGET": "#4da6ff",
        "👀 WATCH": "#ffd32a",
        "🚫 AVOID": "#ff4757"
    }
    color = decision_color.get(s["decision"], "#888")
    target_price = s["harga"] * (1 + s["target_pct"] / 100)
    sl_price = s["harga"] * (1 - s["sl_pct"] / 100)

    change_color = "#00ff88" if s["change"] >= 0 else "#ff4757"
    change_sign = "+" if s["change"] >= 0 else ""

    st.markdown(f"""
    <div class="{card_class}" style="margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
            <div>
                <div style="font-size: 20px; font-weight: 800; color: #fff;">{s['symbol']}</div>
                <div style="font-size: 11px; color: #888;">{s['sector']}</div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 18px; font-weight: 700; color: #fff;">Rp {s['harga']:,.0f}</div>
                <div style="font-size: 12px; color: {change_color};">{change_sign}{s['change']:.2f}%</div>
            </div>
        </div>
        <div style="background: #0a0d14; border-radius: 8px; padding: 10px; margin-bottom: 10px;">
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; text-align: center;">
                <div>
                    <div style="font-size: 10px; color: #666;">CONFIDENCE</div>
                    <div style="font-size: 18px; font-weight: 700; color: {color};">{s['confidence']}%</div>
                </div>
                <div>
                    <div style="font-size: 10px; color: #666;">TARGET</div>
                    <div style="font-size: 16px; font-weight: 700; color: #00ff88;">+{s['target_pct']:.1f}%</div>
                </div>
                <div>
                    <div style="font-size: 10px; color: #666;">R/R</div>
                    <div style="font-size: 16px; font-weight: 700; color: #ffd32a;">{s['rr']:.1f}x</div>
                </div>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px; font-size: 12px;">
            <div style="background: #0a0d14; padding: 6px 10px; border-radius: 6px;">
                <span style="color: #666;">🎯 Target:</span> <span style="color: #fff;">Rp {target_price:,.0f}</span>
            </div>
            <div style="background: #0a0d14; padding: 6px 10px; border-radius: 6px;">
                <span style="color: #666;">🛑 Stop:</span> <span style="color: #fff;">Rp {sl_price:,.0f}</span>
            </div>
        </div>
        <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 6px;">
            <span class="badge" style="background: {color}22; color: {color}; border: 1px solid {color}66;">{s['decision']}</span>
            <span class="badge" style="background: #2a4060; color: #ccc;">Fund: {s['fund_label']}</span>
            <span class="badge" style="background: #2a4060; color: #ccc;">Risk: {s['risk']}</span>
        </div>
        <div style="font-size: 11px; color: #666; padding-top: 4px;">
            RSI: {s['rsi']:.0f} · Vol: {s['vol_ratio']:.1f}x · Flow: {s['flow']}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ─── TAB 1: HOTLIST ─────────────────────────────────────────
with tab1:
    hotlist = [s for s in results if "PRIORITY BUY" in s["decision"] or "SWING TARGET" in s["decision"]]
    st.markdown(f"### 🔥 {len(hotlist)} Sinyal Buy")
    st.caption("Confidence ≥70% · Fundamental layak · Setup teknikal kuat")
    if not hotlist:
        st.info("Tidak ada sinyal kuat saat ini. Coba refresh atau tunggu market lebih aktif.")
    for s in hotlist:
        render_card(s, "stock-card priority-card")

# ─── TAB 2: HIDDEN GEM ──────────────────────────────────────
with tab2:
    gems = [s for s in results if s["is_gem"]]
    st.markdown(f"### 💎 {len(gems)} Hidden Gem")
    st.caption("Power kuat + Fundamental SANGAT BAGUS (≥70). Kualitas tertinggi.")
    if not gems:
        st.info("Belum ada hidden gem terdeteksi.")
    for s in gems:
        render_card(s, "stock-card gem-card")

# ─── TAB 3: VALUE TRAP ──────────────────────────────────────
with tab3:
    traps = [s for s in results if s["is_trap"]]
    st.markdown(f"### ⚠️ {len(traps)} Value Trap")
    st.caption("Chart menggoda TAPI fundamental jelek (<40). HATI-HATI — sering jadi jebakan.")
    if not traps:
        st.info("Tidak ada value trap terdeteksi.")
    for s in traps:
        render_card(s, "stock-card trap-card")

# ─── TAB 4: SEMUA SAHAM ─────────────────────────────────────
with tab4:
    st.markdown(f"### 📊 Semua Saham ({len(results)})")
    
    # Filter controls
    col1, col2 = st.columns(2)
    with col1:
        min_conf = st.slider("Min Confidence", 0, 95, 50, 5)
    with col2:
        sektor_filter = st.selectbox("Sektor", ["Semua"] + list(SEKTOR.keys()))
    
    filtered = [
        s for s in results 
        if s["confidence"] >= min_conf and (sektor_filter == "Semua" or s["sector"] == sektor_filter)
    ]
    
    st.caption(f"Menampilkan {len(filtered)} saham")
    
    # Quick table view
    if filtered:
        df = pd.DataFrame([{
            "Saham": s["symbol"],
            "Sektor": s["sector"],
            "Harga": f"Rp {s['harga']:,.0f}",
            "Conf%": s["confidence"],
            "Target%": f"+{s['target_pct']:.1f}",
            "SL%": f"-{s['sl_pct']:.1f}",
            "R/R": f"{s['rr']:.1f}x",
            "Fund": s["fund_label"].split()[1] if " " in s["fund_label"] else s["fund_label"],
            "Sinyal": s["decision"].split()[1] if " " in s["decision"] else s["decision"]
        } for s in filtered])
        st.dataframe(df, use_container_width=True, hide_index=True, height=500)

# ─── TAB 5: INFO ────────────────────────────────────────────
with tab5:
    st.markdown("""
    ### 📱 Cara Install di HP
    
    **Android (Chrome):**
    1. Buka URL app ini
    2. Tap menu (⋮) di pojok kanan atas
    3. Pilih **"Add to Home screen"** atau **"Install app"**
    4. Icon app muncul di home screen
    
    **iPhone (Safari):**
    1. Buka URL app ini di Safari
    2. Tap tombol Share (□↑)
    3. Pilih **"Add to Home Screen"**
    4. Icon app muncul seperti app native
    
    ---
    
    ### 🎯 Cara Pakai
    
    1. **🔥 Hotlist** — Saham dengan sinyal beli kuat
    2. **💎 Hidden Gem** — Best of best: teknikal + fundamental sama-sama bagus
    3. **⚠️ Value Trap** — Chart menggoda tapi fundamental bermasalah, HINDARI
    4. **📊 Semua** — Filter manual semua saham
    5. **🔄 Refresh** — Update data Yahoo Finance (cache 5 menit)
    
    ---
    
    ### 📊 Penjelasan Score
    
    **Confidence** — Skor 0-95% gabungan teknikal + fundamental
    
    **Faktor Teknikal:**
    - Trend (EMA20, EMA50)
    - Momentum (RSI 45-68 sweet spot)
    - MACD signal
    - Volume surge
    - Support/Resistance
    - Orderflow (close near high)
    - Continuation pattern
    - Distribution/absorption
    - Fake breakout detection
    
    **Faktor Fundamental:**
    - PER (Price/Earnings)
    - PBV (Price/Book Value)
    - ROE (Return on Equity)
    - DER (Debt/Equity)
    
    ---
    
    ### ⚠️ Disclaimer
    
    - Data Yahoo Finance, **delay ~15 menit**
    - Confidence adalah estimasi probabilistik, **BUKAN jaminan profit**
    - Win rate realistis swing strategy: **55-65%**
    - Selalu pakai stop loss
    - Jangan investasi uang yang tidak siap rugi
    - Tools ini untuk edukasi, bukan rekomendasi investasi
    
    ---
    
    ### 🔧 Tech Stack
    
    - Streamlit (UI)
    - Yahoo Finance API (data)
    - Python (analisis)
    - Deployed di Streamlit Cloud (gratis)
    """)
    
    st.markdown("---")
    st.caption("Made with ❤️ for Indonesian traders")
