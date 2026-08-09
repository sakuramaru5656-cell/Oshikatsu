import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import re

# --- ページ設定とポケモン風CSS ---
st.set_page_config(page_title="推しイベ", page_icon="🐾", layout="centered")

st.markdown("""
    <style>
    /* ポケモン風カラーテーマ */
    @import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'M PLUS Rounded 1c', sans-serif;
        background-color: #FFDE00; /* ピカチュウイエロー */
    }
    
    .stApp { background: #FFDE00; }

    /* ポケモン図鑑風カード */
    .pokedex-card {
        background: white;
        border: 4px solid #3B4CCA; /* ブルー */
        border-radius: 20px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 8px 8px 0px #CC0000; /* レッド */
    }

    /* ポップなバッジ */
    .type-badge {
        display: inline-block;
        padding: 5px 15px;
        border-radius: 50px;
        font-size: 12px;
        font-weight: bold;
        color: white;
        margin-right: 5px;
        border: 2px solid rgba(0,0,0,0.1);
    }
    
    .transport-tag {
        background: #f0f0f0;
        color: #333;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        margin-top: 5px;
        display: inline-block;
    }

    /* カレンダーのカスタマイズ */
    .fc { background: white; border-radius: 15px; padding: 10px; border: 4px solid #3B4CCA; }
    .fc-event { border-radius: 5px !important; border: none !important; font-weight: bold !important; }
    
    /* ボタンのカスタマイズ */
    .stButton>button {
        background-color: #CC0000;
        color: white;
        border-radius: 20px;
        border: 3px solid #3B4CCA;
    }
    </style>
    """, unsafe_allow_html=True)

# --- カテゴリー・絵文字定義 ---
GENRES = {
    "VTuber": {"emoji": "🌈", "words": ["ホロライブ", "さくらみこ", "星街すいせい", "にじさんじ"], "color": "#FF69B4"},
    "ポケモン": {"emoji": "🐾", "words": ["ポケモンセンター", "ポケモン", "ピカチュウ"], "color": "#3B4CCA"},
    "ジャニーズ系": {"emoji": "🎤", "words": ["timelesz", "Hey! Say! JUMP", "King & Prince", "なにわ男子", "Snow Man"], "color": "#FF8C00"},
    "ジャンプ": {"emoji": "👒", "words": ["ワンピース", "ONE PIECE", "ナルト", "NARUTO"], "color": "#FF0000"},
    "あんスタ": {"emoji": "✨", "words": ["あんさんぶるスターズ", "あんスタ"], "color": "#9370DB"},
    "その他": {"emoji": "🎁", "words": ["コラボカフェ", "展示会"], "color": "#4CAF50"}
}
TIMES = ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"]

# --- 交通手段計算ロジック (小山駅起点) ---
def get_transport_info(loc_label):
    if loc_label == "30分以内":
        return "🚃 JR宇都宮線 (約25分) / 🚗 車 (約40分)"
    elif loc_label == "1時間以内":
        return "🚄 新幹線なすの (約15分) / 🚃 JR快速 (約45分) / 🚗 車 (約1時間)"
    elif loc_label == "1時間半以内":
        return "🚄 新幹線 (約40分) / 🚃 上野東京ライン (約80分)"
    elif loc_label == "2時間半以内":
        return "🚃 湘南新宿ライン (約130分) / 🚄 新幹線+JR"
    else:
        return "🚄 新幹線・飛行機・長距離バス"

# --- 日付・期間抽出エンジン ---
def extract_date_range(text):
    year = datetime.now().year
    # 期間: 8/1〜8/30
    m = re.search(r'(\d{1,2})[./月](\d{1,2}).*?[〜~ー\-](\d{1,2})[./月](\d{1,2})', text)
    if m:
        start = datetime(year, int(m.group(1)), int(m.group(2)))
        end = datetime(year, int(m.group(3)), int(m.group(4)))
        return start, end
    # 単発: 8/1
    m = re.search(r'(\d{1,2})[./月](\d{1,2})', text)
    if m:
        dt = datetime(year, int(m.group(1)), int(m.group(2)))
        return dt, dt
    return None, None

@st.cache_data(ttl=3600)
def fetch_events():
    all_events = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for genre, info in GENRES.items():
        for kw in info["words"][:3]:
            url = f"https://collabo-cafe.com/?s={kw}"
            try:
                res = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(res.text, 'html.parser')
                for art in soup.select('article')[:5]:
                    title = art.select_one('.entry-title').get_text().strip()
                    link = art.find('a')['href']
                    
                    loc = "1時間半以内"
                    if any(x in title for x in ["宇都宮", "ベルモール"]): loc = "30分以内"
                    elif any(x in title for x in ["大宮", "さいたま"]): loc = "1時間以内"
                    elif any(x in title for x in ["横浜", "幕張", "千葉", "Kアリーナ"]): loc = "2時間半以内"
                    elif any(x in title for x in ["大阪", "名古屋", "福岡"]): loc = "それ以上"

                    start_dt, end_dt = extract_date_range(title)
                    
                    all_events.append({
                        "id": f"{kw}-{title[:10]}",
                        "title": info["emoji"],
                        "full_title": title,
                        "start": start_dt.strftime("%Y-%m-%d") if start_dt else None,
                        # FullCalendarの終了日は「その日の0時まで」なので表示上+1日する
                        "end": (end_dt + timedelta(days=1)).strftime("%Y-%m-%d") if end_dt else None,
                        "url": link,
                        "genre": genre,
                        "time": loc,
                        "transport": get_transport_info(loc),
                        "has_date": start_dt is not None,
                        "color": info["color"]
                    })
            except: pass
    return all_events

# --- メイン画面 ---
st.title("🐾 推しイベ・アドベンチャー")
st.write("栃木県小山駅から出発！キミの推しを見つけよう！")

# ポップなフィルター
col1, col2 = st.columns([1, 1])
with col1:
    selected_genres = st.multiselect("タイプ（ジャンル）", list(GENRES.keys()), default=list(GENRES.keys()))
with col2:
    selected_times = st.multiselect("きょり（時間）", TIMES, default=["30分以内", "1時間以内", "1時間半以内"])

data = fetch_events()
filtered = [e for e in data if e['genre'] in selected_genres and e['time'] in selected_times]

# カレンダー表示
st.subheader("📅 スケジュール・マップ")
cal_events = []
for e in [x for x in filtered if x['has_date']]:
    cal_events.append({
        "id": e['id'], "title": e['title'], "start": e['start'], "end": e['end'],
        "backgroundColor": e['color'], "borderColor": "white",
        "extendedProps": {"full_title": e['full_title'], "url": e['url'], "time": e['time'], "transport": e['transport'], "genre": e['genre']}
    })

state = calendar(events=cal_events, options={"initialView": "dayGridMonth", "locale": "ja", "height": "500px"})

# 詳細表示（図鑑風）
if state.get("eventClick"):
    p = state["eventClick"]["event"]["extendedProps"]
    st.markdown(f"""
        <div class="pokedex-card">
            <h2 style='color:#3B4CCA; margin-top:0;'>📕 イベント図鑑</h2>
            <p style='font-size:1.1em; font-weight:bold;'>{p['full_title']}</p>
            <span class="type-badge" style="background:{GENRES[p['genre']]['color']}">{p['genre']}</span>
            <span class="type-badge" style="background:#3B82F6">📍 小山から{p['time']}</span>
            <div class="transport-tag">🚃 行きかた: {p['transport']}</div>
            <br><br>
            <a href="{p['url']}" target="_blank">
                <button style="width:100%; padding:10px; cursor:pointer; font-weight:bold;">公式サイトへ GO!</button>
            </a>
        </div>
    """, unsafe_allow_html=True)
else:
    st.info("💡 カレンダーの絵文字をタップして、イベント図鑑をひらこう！")

# 週間リスト
st.subheader("📋 今週のクエスト")
today = datetime.now().date()
for e in sorted([x for x in filtered if x['has_date']], key=lambda x: x['start']):
    evt_start = datetime.strptime(e['start'], "%Y-%m-%d").date()
    if today <= evt_start <= today + timedelta(days=7):
        st.markdown(f"""
        <div class="pokedex-card" style="padding:15px; border-width:2px;">
            <span style='font-size:0.8em; color:#666;'>{e['start']}</span><br>
            <strong>{GENRES[e['genre']]['emoji']} {e['full_title']}</strong><br>
            <small>小山駅発: {e['transport']}</small>
        </div>
        """, unsafe_allow_html=True)
