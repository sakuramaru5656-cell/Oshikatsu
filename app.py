import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import re

# --- ページ設定 ---
st.set_page_config(page_title="推しイベ", page_icon="📅", layout="centered")

# --- モダンUIデザイン ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #FFFFFF; }
    
    .event-card {
        background: white; border-radius: 12px; padding: 16px;
        margin-bottom: 12px; border: 1px solid #EDF2F7;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .badge {
        display: inline-block; padding: 2px 10px; border-radius: 9999px;
        font-size: 11px; font-weight: 600; margin-right: 5px;
    }
    .time-badge { background-color: #EDF2F7; color: #4A5568; }
    .event-title {
        font-size: 16px; font-weight: 600; color: #1A202C;
        text-decoration: none; display: block; margin-top: 5px;
    }
    /* カレンダーを小さくする */
    .fc { font-size: 0.85em !important; }
    .fc .fc-toolbar-title { font-size: 1.2em !important; }
    </style>
    """, unsafe_allow_html=True)

# --- カテゴリー・絵文字定義 ---
GENRES = {
    "VTuber": {"emoji": "🌈", "words": ["ホロライブ", "さくらみこ", "星街すいせい", "にじさんじ"]},
    "ポケモン": {"emoji": "🐾", "words": ["ポケモンセンター", "ポケモン", "ピカチュウ"]},
    "ジャニーズ系": {"emoji": "🎤", "words": ["timelesz", "Hey! Say! JUMP", "King & Prince", "なにわ男子", "Snow Man", "SixTONES", "WEST.", "Aぇ! group", "ライブ", "コンサート"]},
    "ジャンプ(OP/ナルト)": {"emoji": "👒", "words": ["ワンピース", "ONE PIECE", "NARUTO", "ナルト"]},
    "あんスタ": {"emoji": "✨", "words": ["あんさんぶるスターズ", "あんスタ"]},
    "その他": {"emoji": "🎁", "words": ["コラボカフェ", "展示会"]}
}

TIMES = ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"]

# --- データ取得 ---
@st.cache_data(ttl=3600)
def fetch_events():
    all_events = []
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for genre_name, info in GENRES.items():
        emoji = info["emoji"]
        for kw in info["words"][:5]: # 各ワード上位
            url = f"https://collabo-cafe.com/?s={kw}"
            try:
                res = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(res.text, 'html.parser')
                for art in soup.select('article')[:6]:
                    title = art.select_one('.entry-title').get_text().strip()
                    link = art.find('a')['href']
                    
                    # 小山駅からの時間判定
                    loc_label = "都内"
                    if any(x in title for x in ["宇都宮", "ベルモール"]): loc_label = "30分以内"
                    elif any(x in title for x in ["大宮", "さいたま"]): loc_label = "1時間以内"
                    elif any(x in title for x in ["横浜", "幕張", "千葉", "Kアリーナ"]): loc_label = "2時間半以内"
                    elif any(x in title for x in ["大阪", "名古屋", "福岡", "札幌"]): loc_label = "それ以上"
                    else: loc_label = "1時間半以内"

                    # 日付解析
                    start_dt = None
                    date_match = re.search(r'(\d+)月(\d+)日', title)
                    if date_match:
                        try: start_dt = datetime(2024, int(date_match.group(1)), int(date_match.group(2)))
                        except: pass
                    
                    all_events.append({
                        "title": f"{emoji} {kw}", # カレンダーには絵文字+ワード
                        "full_title": title,
                        "start": start_dt.strftime("%Y-%m-%d") if start_dt else None,
                        "url": link,
                        "genre": genre_name,
                        "time": loc_label,
                        "has_date": start_dt is not None
                    })
            except: pass
    return all_events

# --- アプリ画面構成 ---
st.title("推しイベ")

# 1. フィルターボタン (カレンダーの上に配置)
col1, col2 = st.columns([2, 1])
with col1:
    selected_genres = st.pills("ジャンル", list(GENRES.keys()), selection_mode="multi", default=list(GENRES.keys()))
with col2:
    selected_times = st.pills("移動時間", TIMES, selection_mode="multi", default=["30分以内", "1時間以内", "1時間半以内"])

# データ取得とフィルタリング
data = fetch_events()
filtered = [e for e in data if e['genre'] in selected_genres and e['time'] in selected_times]

# 2. カレンダー表示 (小さめに設定)
tab1, tab2 = st.tabs(["📅 カレンダー", "📋 リスト形式"])

with tab1:
    cal_events = []
    # カレンダー用カラー設定
    colors = {"VTuber": "#E2E8F0", "ポケモン": "#FEE2E2", "ジャニーズ系": "#FEF9C3", "ジャンプ(OP/ナルト)": "#DBEAFE", "あんスタ": "#F3E8FF"}
    
    for e in [x for x in filtered if x['has_date']]:
        cal_events.append({
            "title": e['title'], 
            "start": e['start'], 
            "url": e['url'], 
            "color": colors.get(e['genre'], "#EDF2F7"),
            "textColor": "#1A202C"
        })
    
    calendar_options = {
        "initialView": "dayGridMonth",
        "height": "450px", # 高さを一段階小さく
        "locale": "ja",
        "headerToolbar": {"left": "prev,next", "center": "title", "right": ""},
    }
    calendar(events=cal_events, options=calendar_options)
    st.caption("※カレンダーの絵文字をタップすると詳細（外部サイト）が開きます")

with tab2:
    if not filtered:
        st.write("該当するイベントはありません")
    else:
        for e in sorted(filtered, key=lambda x: (not x['has_date'], x['start'] or "")):
            st.markdown(f"""
            <div class="event-card">
                <span class="badge time-badge">📍 {e['time']}</span>
                <span class="badge" style="background:#F7FAFC;">{GENRES[e['genre']]['emoji']} {e['genre']}</span>
                <a href="{e['url']}" target="_blank" class="event-title">{e['full_title']}</a>
                <div style="font-size:12px; color:#718096; margin-top:4px;">📅 {e['start'] if e['has_date'] else '日付未定'}</div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")
st.caption("小山駅を起点に計算しています。")
