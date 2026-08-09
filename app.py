import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import re

# --- ページ設定とポップなデザインCSS ---
st.set_page_config(page_title="推しイベ", page_icon="✨", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'M PLUS Rounded 1c', sans-serif;
        background-color: #FFFDF0; /* ポップなイエロー背景 */
    }
    .stApp { background: #FFFDF0; }

    /* カレンダー自体のポップなデザイン */
    .fc { 
        background: #FFFFFF !important; 
        border-radius: 20px !important; 
        border: 4px solid #3B82F6 !important;
        padding: 10px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.05);
    }
    .fc-toolbar-title { 
        color: #1E40AF !important; 
        font-size: 1.2em !important;
        background: #DBEAFE;
        padding: 5px 15px;
        border-radius: 50px;
    }

    /* イベントバー（一本線） */
    .fc-event {
        border-radius: 6px !important;
        border: none !important;
        padding: 4px 6px !important;
        font-weight: 800 !important;
        cursor: pointer;
    }

    /* ポップな詳細カード */
    .pop-card {
        background: white; border-radius: 20px; padding: 20px;
        margin-top: 15px; border: 4px solid #3B82F6;
        box-shadow: 6px 6px 0px #BFDBFE;
    }
    .badge {
        display: inline-block; padding: 4px 12px; border-radius: 50px;
        font-size: 11px; font-weight: bold; color: white; margin-right: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 固定カテゴリー設定 ---
GENRES = {
    "VTuber": {"emoji": "🌈", "words": ["ホロライブ", "さくらみこ", "にじさんじ"], "color": "#F472B6"},
    "ポケモン": {"emoji": "🐾", "words": ["ポケモンセンター", "ポケモン"], "color": "#3B82F6"},
    "ジャニーズ": {"emoji": "🎤", "words": ["timelesz", "Hey! Say! JUMP", "King & Prince", "Snow Man"], "color": "#FB923C"},
    "ジャンプ": {"emoji": "👒", "words": ["ワンピース", "ONE PIECE", "ナルト", "NARUTO"], "color": "#F87171"},
    "あんスタ": {"emoji": "✨", "words": ["あんさんぶるスターズ", "あんスタ"], "color": "#A78BFA"},
    "テーマパーク": {"emoji": "🎡", "words": ["富士急", "ピューロランド", "USJ", "ディズニー"], "color": "#10B981"},
    "その他": {"emoji": "🎁", "words": ["コラボカフェ"], "color": "#94A3B8"}
}

TIMES = ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"]

def get_access_info(loc):
    guides = {
        "30分以内": "🚃 JR宇都宮線 (約25分) / 🚗 車 (約40分)",
        "1時間以内": "🚄 新幹線なすの (約15分) / 🚃 JR快速 (約45分)",
        "1時間半以内": "🚄 新幹線 (約40分) / 🚃 上野東京ライン (約80分)",
        "2時間半以内": "🚃 湘南新宿ライン (約130分) / 🚄 新幹線+JR",
        "それ以上": "🚄 新幹線 / ✈️ 飛行機 / 🚌 高速バス"
    }
    return guides.get(loc, "交通機関を確認してください")

# --- 日付・期間抽出エンジン ---
def extract_dates(text):
    year = datetime.now().year
    sep = r'[〜~ー\-\s－]+'
    # 期間形式
    m = re.search(r'(\d{1,2})[./月](\d{1,2}).*?{sep}(\d{1,2})[./月](\d{1,2})'.format(sep=sep), text)
    if m:
        try:
            start = datetime(year, int(m.group(1)), int(m.group(2)))
            end = datetime(year, int(m.group(3)), int(m.group(4)))
            if end < start: end = datetime(year + 1, int(m.group(3)), int(m.group(4)))
            return start, end
        except: pass
    # 単発形式
    m = re.search(r'(\d{1,2})[./月](\d{1,2})', text)
    if m:
        try:
            dt = datetime(year, int(m.group(1)), int(m.group(2)))
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
                for art in soup.select('article')[:5]:
                    title = (art.find('h2') or art.select_one('.entry-title')).get_text().strip()
                    link = art.find('a')['href']
                    start_dt, end_dt = extract_dates(title)
                    
                    # エリア判定 (小山駅起点)
                    loc = "1時間半以内"
                    if any(x in title for x in ["宇都宮", "ベルモール"]): loc = "30分以内"
                    elif any(x in title for x in ["大宮", "さいたま"]): loc = "1時間以内"
                    elif any(x in title for x in ["横浜", "幕張", "千葉", "富士急"]): loc = "2時間半以内"
                    elif any(x in title for x in ["大阪", "名古屋", "USJ"]): loc = "それ以上"

                    if start_dt:
                        all_events.append({
                            "id": f"{kw}-{title[:10]}", "title": f"{info['emoji']} {kw}",
                            "full_title": title, "start": start_dt.strftime("%Y-%m-%d"),
                            "end": (end_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
                            "genre": gen, "time": loc, "url": link, "color": info["color"]
                        })
            except: pass
    return all_events

# --- メイン表示 ---
st.title("✨ 推しイベ")
st.write("栃木県小山駅発 🚃 スケジュール・マップ")

# フィルター
c1, c2 = st.columns(2)
with c1: sel_gen = st.multiselect("ジャンル", list(GENRES.keys()), default=list(GENRES.keys()))
with c2: sel_time = st.multiselect("小山からの時間", TIMES, default=["30分以内", "1時間以内", "1時間半以内"])

data = fetch_data()
filtered = [e for e in data if e['genre'] in sel_gen and e['time'] in sel_time]

# 1. カレンダー表示
cal_events = []
for e in filtered:
    cal_events.append({
        "id": e['id'], "title": e['title'], "start": e['start'], "end": e['end'],
        "backgroundColor": e['color'], "borderColor": "white",
        "extendedProps": {"full_title": e['full_title'], "url": e['url'], "time": e['time'], "gen": e['genre']}
    })

# height='auto' でスクロールなし
state = calendar(events=cal_events, options={"initialView": "dayGridMonth", "locale": "ja", "height": "auto", "headerToolbar": {"left": "prev,next", "center": "title", "right": ""}})

# 2. 詳細表示 (カレンダーの下)
if state.get("eventClick"):
    p = state["eventClick"]["event"]["extendedProps"]
    st.markdown(f"""
        <div class="pop-card">
            <h3 style='color:#1E40AF; margin-top:0;'>✨ イベント詳細</h3>
            <p style='font-size:1.1em; font-weight:800; line-height:1.4;'>{p['full_title']}</p>
            <div style='margin-bottom:15px;'>
                <span style='background:{GENRES[p['gen']]['color']}; color:white; padding:4px 12px; border-radius:50px; font-size:12px; font-weight:bold;'>{p['gen']}</span>
                <span style='background:#3B82F6; color:white; padding:4px 12px; border-radius:50px; font-size:12px; font-weight:bold; margin-left:5px;'>📍 小山から{p['time']}</span>
            </div>
            <p style='background:#F8FAFC; padding:10px; border-radius:10px; font-size:0.9em; border:1px dashed #3B82F6;'>
                <b>🚃 小山駅からのルート目安:</b><br>{get_access_info(p['time'])}
            </p>
            <a href="{p['url']}" target="_blank" style="text-decoration:none;">
                <button style="width:100%; background:#3B82F6; color:white; border:none; padding:15px; border-radius:15px; font-weight:bold; cursor:pointer;">公式サイトを見に行く！ ➔</button>
            </a>
        </div>
    """, unsafe_allow_html=True)

# 3. 週間ピックアップ
st.subheader("📋 今週の予定")
today = datetime.now().date()
week_later = today + timedelta(days=7)
for e in sorted(filtered, key=lambda x: x['start']):
    evt_start = datetime.strptime(e['start'], "%Y-%m-%d").date()
    if today <= evt_start <= week_later:
        st.markdown(f"""
        <div style="background:white; border-radius:15px; padding:15px; margin-bottom:10px; border-left:8px solid {e['color']}; box-shadow:2px 2px 10px rgba(0,0,0,0.05);">
            <small style='color:#64748B;'>{e['start']} | {e['genre']}</small><br>
            <b style='color:#1E293B;'>{e['full_title']}</b><br>
            <small style='color:#3B82F6;'>🚃 {get_access_info(e['time'])}</small>
        </div>
        """, unsafe_allow_html=True)
