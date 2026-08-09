import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import re

# --- ページ設定とポップなデザイン ---
st.set_page_config(page_title="推しイベ", page_icon="✨", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'M PLUS Rounded 1c', sans-serif;
        background-color: #FFFDF0;
    }
    .stApp { background: #FFFDF0; }

    /* カレンダー自体のポップ化 */
    .fc { 
        background: #FFFFFF !important; 
        border-radius: 20px !important; 
        border: 4px solid #3B82F6 !important;
        padding: 10px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.05);
    }
    
    /* イベントバー（一本線）の視認性向上 */
    .fc-event {
        border-radius: 8px !important;
        border: 1px solid rgba(0,0,0,0.1) !important;
        padding: 4px 6px !important;
        font-weight: 800 !important;
        font-size: 0.9em !important;
        cursor: pointer;
        transition: opacity 0.2s;
    }
    .fc-event:hover { opacity: 0.8; }

    /* ポップな詳細カード */
    .pop-detail-card {
        background: white; border-radius: 25px; padding: 25px;
        margin-top: 20px; border: 4px solid #3B82F6;
        box-shadow: 6px 6px 0px #BFDBFE;
    }

    .transport-tag {
        display: inline-block; background: #E0F2FE;
        padding: 6px 12px; border-radius: 10px;
        font-size: 0.9em; margin-top: 8px;
        color: #0369A1; border: 1px solid #BAE6FD;
    }
    </style>
    """, unsafe_allow_html=True)

# --- カテゴリー定義 ---
GENRES = {
    "VTuber": {"emoji": "🌈", "words": ["ホロライブ", "さくらみこ", "星街すいせい", "にじさんじ"], "color": "#F472B6"},
    "ポケモン": {"emoji": "🐾", "words": ["ポケモンセンター", "ポケモン", "ピカチュウ"], "color": "#3B82F6"},
    "ジャニーズ": {"emoji": "🎤", "words": ["timelesz", "Hey! Say! JUMP", "King & Prince", "Snow Man"], "color": "#FB923C"},
    "ジャンプ": {"emoji": "👒", "words": ["ワンピース", "ONE PIECE", "ナルト", "NARUTO"], "color": "#F87171"},
    "あんスタ": {"emoji": "✨", "words": ["あんさんぶるスターズ", "あんスタ"], "color": "#A78BFA"},
    "テーマパーク": {"emoji": "🎡", "words": ["富士急", "ピューロランド", "USJ", "ディズニー", "ナンジャ"], "color": "#10B981"},
    "その他": {"emoji": "🎁", "words": ["コラボカフェ", "アニメイベント"], "color": "#94A3B8"}
}
TIMES = ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"]

# --- 交通アクセス (小山駅発) ---
def get_access_info(loc):
    guides = {
        "30分以内": "🚃 **JR宇都宮線** (25分) / 🚗 **車** (40分)",
        "1時間以内": "🚄 **新幹線なすの** (15分) / 🚃 **JR快速** (45分)",
        "1時間半以内": "🚄 **新幹線** (40分) / 🚃 **上野東京ライン** (80分)",
        "2時間半以内": "🚃 **湘南新宿ライン** (130分) / 🚄 **新幹線+JR**",
        "それ以上": "🚄 **新幹線** / ✈️ **飛行機** / 🚌 **高速バス**"
    }
    return guides.get(loc, "交通機関を確認してください")

# --- 高度な期間抽出エンジン (AI的解析) ---
def extract_date_range_v2(text):
    year = datetime.now().year
    # あらゆる日付区切り記号に対応: 〜 ~ ー - － 
    sep = r'[〜~ー\-\s－]+'
    
    # 1. 期間形式: 8/1〜8/30, 8月1日〜9月5日
    range_pattern = r'(\d{1,2})[./月](\d{1,2})[日]?{sep}(\d{1,2})[./月](\d{1,2})[日]?'.format(sep=sep)
    m = re.search(range_pattern, text)
    if m:
        m1, d1, m2, d2 = map(int, m.groups())
        try:
            start = datetime(year, m1, d1)
            end = datetime(year, m2, d2)
            # 月を跨いで1月などになった場合の年越し処理
            if m2 < m1: end = datetime(year + 1, m2, d2)
            return start, end
        except: pass

    # 2. 単発形式: 8/1, 8月1日
    single_pattern = r'(\d{1,2})[./月](\d{1,2})[日]?'
    m = re.search(single_pattern, text)
    if m:
        m, d = map(int, m.groups())
        try:
            dt = datetime(year, m, d)
            return dt, dt
        except: pass
    
    return None, None

@st.cache_data(ttl=3600)
def fetch_data():
    all_events = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for gen, info in GENRES.items():
        for kw in info["words"][:3]:
            url = f"https://collabo-cafe.com/?s={kw}"
            try:
                res = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(res.text, 'html.parser')
                for art in soup.select('article')[:6]:
                    title = art.select_one('.entry-title').get_text().strip()
                    link = art.find('a')['href']
                    
                    # 期間抽出
                    start_dt, end_dt = extract_date_range_v2(title)
                    
                    # 小山駅からの時間判定
                    loc = "1時間半以内"
                    if any(x in title for x in ["宇都宮", "ベルモール"]): loc = "30分以内"
                    elif any(x in title for x in ["大宮", "さいたまスーパーアリーナ"]): loc = "1時間以内"
                    elif any(x in title for x in ["横浜", "幕張", "千葉", "富士急", "ピューロランド"]): loc = "2時間半以内"
                    elif any(x in title for x in ["大阪", "名古屋", "USJ"]): loc = "それ以上"

                    if start_dt:
                        all_events.append({
                            "id": f"{kw}-{title[:10]}",
                            "title": f"{info['emoji']} {kw}",
                            "full_title": title,
                            "start": start_dt.strftime("%Y-%m-%d"),
                            # FullCalendarの終了日は「含まない」設定のため、表示上+1日する
                            "end": (end_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
                            "genre": gen, "time": loc, "url": link, "color": info["color"]
                        })
            except: pass
    return all_events

# --- メイン表示 ---
st.title("✨ 推しイベ")
st.caption("栃木県小山駅発 🚃 開催期間を一本線で表示！")

c1, c2 = st.columns(2)
with c1: sel_gen = st.multiselect("ジャンル", list(GENRES.keys()), default=list(GENRES.keys()))
with c2: sel_time = st.multiselect("距離(時間)", TIMES, default=["30分以内", "1時間以内", "1時間半以内"])

data = fetch_data()
filtered = [e for e in data if e['genre'] in sel_gen and e['time'] in sel_time]

# 1. カレンダー表示
cal_events = []
for e in filtered:
    cal_events.append({
        "id": e['id'], "title": e['title'], "start": e['start'], "end": e['end'],
        "backgroundColor": e['color'], "borderColor": "rgba(255,255,255,0.5)",
        "extendedProps": {"full_title": e['full_title'], "url": e['url'], "time": e['time'], "gen": e['genre']}
    })

# カレンダーの高さを自動調整(スクロールなし)
state = calendar(events=cal_events, options={
    "initialView": "dayGridMonth",
    "locale": "ja",
    "height": "auto",
    "headerToolbar": {"left": "prev,next", "center": "title", "right": ""},
})

# 2. 詳細表示 (カレンダーの下)
if state.get("eventClick"):
    p = state["eventClick"]["event"]["extendedProps"]
    st.markdown(f"""
        <div class="pop-detail-card">
            <h3 style='color:#1E40AF; margin-top:0;'>✨ イベント図鑑</h3>
            <p style='font-size:1.1em; font-weight:800; line-height:1.4;'>{p['full_title']}</p>
            <div style='margin-bottom:15px;'>
                <span style='background:{GENRES[p['gen']]['color']}; color:white; padding:4px 12px; border-radius:50px; font-size:12px; font-weight:bold;'>{p['gen']}</span>
                <span style='background:#3B82F6; color:white; padding:4px 12px; border-radius:50px; font-size:12px; font-weight:bold; margin-left:5px;'>📍 小山から{p['time']}</span>
            </div>
            <div class="transport-tag">
                <b>🚃 小山駅からのルート目安:</b><br>
                {get_access_info(p['time'])}
            </div>
            <a href="{p['url']}" target="_blank" style="text-decoration:none;">
                <button style="width:100%; background:#3B82F6; color:white; border:none; padding:15px; border-radius:15px; font-weight:bold; cursor:pointer; font-size:16px; margin-top:15px; box-shadow:0 4px 0 #1E40AF;">
                    公式サイトを見に行く！ ➔
                </button>
            </a>
        </div>
    """, unsafe_allow_html=True)

# 3. 週間表示
st.subheader("📋 今週のピックアップ")
today = datetime.now().date()
week_later = today + timedelta(days=7)
for e in sorted(filtered, key=lambda x: x['start']):
    evt_start = datetime.strptime(e['start'], "%Y-%m-%d").date()
    if today <= evt_start <= week_later:
        st.markdown(f"""
        <div style="background:white; border-radius:15px; padding:15px; margin-bottom:10px; border-left:8px solid {e['color']}; box-shadow:2px 2px 10px rgba(0,0,0,0.05);">
            <small style='color:#64748B;'>{e['start']} 〜 {e['genre']}</small><br>
            <b style='color:#1E293B;'>{e['full_title']}</b><br>
            <small style='color:#3B82F6;'>🚃 {get_access_info(e['time'])}</small>
        </div>
        """, unsafe_allow_html=True)
