import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import re

# --- ページ設定 ---
st.set_page_config(page_title="推しイベ", page_icon="📅", layout="centered")

# --- UIデザイン ---
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
    /* カレンダー内のイベントの文字を大きく、中央に */
    .fc-event-title { font-size: 1.2em !important; font-weight: bold !important; text-align: center !important; }
    .fc { font-size: 0.85em !important; }
    </style>
    """, unsafe_allow_html=True)

# --- カテゴリー定義 ---
GENRES = {
    "VTuber": {"emoji": "🌈", "words": ["ホロライブ", "さくらみこ", "星街すいせい", "にじさんじ"]},
    "ポケモン": {"emoji": "🐾", "words": ["ポケモンセンター", "ポケモン", "ピカチュウ"]},
    "ジャニーズ系": {"emoji": "🎤", "words": ["timelesz", "Hey! Say! JUMP", "King & Prince", "なにわ男子", "Snow Man", "SixTONES"]},
    "ジャンプ": {"emoji": "👒", "words": ["ワンピース", "ONE PIECE", "ナルト", "NARUTO"]},
    "あんスタ": {"emoji": "✨", "words": ["あんさんぶるスターズ", "あんスタ"]},
    "その他": {"emoji": "🎁", "words": ["コラボカフェ", "展示会"]}
}

TIMES = ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"]

# --- データ取得エンジン ---
@st.cache_data(ttl=3600)
def fetch_events():
    all_events = []
    headers = {"User-Agent": "Mozilla/5.0"}
    current_year = datetime.now().year
    
    for genre_name, info in GENRES.items():
        emoji = info["emoji"]
        for kw in info["words"][:3]:
            url = f"https://collabo-cafe.com/?s={kw}"
            try:
                res = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(res.text, 'html.parser')
                for art in soup.select('article')[:5]:
                    title = art.select_one('.entry-title').get_text().strip()
                    link = art.find('a')['href']
                    
                    # 日付解析 (現在年に合わせる)
                    start_dt = None
                    date_match = re.search(r'(\d+)月(\d+)日', title)
                    if date_match:
                        try:
                            month, day = int(date_match.group(1)), int(date_match.group(2))
                            start_dt = datetime(current_year, month, day)
                            # 12月に1月の記事が出た場合などの年越し対応
                            if month < datetime.now().month - 2:
                                start_dt = datetime(current_year + 1, month, day)
                        except: pass
                    
                    # 小山駅からの時間
                    loc_label = "1時間半以内"
                    if any(x in title for x in ["宇都宮", "ベルモール"]): loc_label = "30分以内"
                    elif any(x in title for x in ["大宮", "さいたま"]): loc_label = "1時間以内"
                    elif any(x in title for x in ["横浜", "幕張", "千葉", "ぴあアリーナ", "Kアリーナ"]): loc_label = "2時間半以内"
                    elif any(x in title for x in ["大阪", "名古屋", "福岡", "札幌"]): loc_label = "それ以上"

                    all_events.append({
                        "emoji": emoji,
                        "title_for_cal": f"{emoji} {kw}", # カレンダー表示用
                        "full_title": title,
                        "start": start_dt.strftime("%Y-%m-%d") if start_dt else None,
                        "url": link,
                        "genre": genre_name,
                        "time": loc_label,
                        "has_date": start_dt is not None
                    })
            except: pass
    return all_events

# --- メイン画面 ---
st.title("推しイベ")

# フィルタボタン（カレンダーの上）
st.markdown("### 🔍 ジャンル")
selected_genres = st.pills("ジャンル", list(GENRES.keys()), selection_mode="multi", default=list(GENRES.keys()), label_visibility="collapsed")

st.markdown("### ⏳ 小山駅からの時間")
selected_times = st.pills("時間", TIMES, selection_mode="multi", default=["30分以内", "1時間以内", "1時間半以内"], label_visibility="collapsed")

# フィルタリング
data = fetch_events()
filtered = [e for e in data if e['genre'] in selected_genres and e['time'] in selected_times]

tab1, tab2 = st.tabs(["📅 カレンダー", "📋 全リスト"])

with tab1:
    cal_events = []
    # ジャンル別カラー（背景色をパステル調に）
    colors = {
        "VTuber": "#E0F2FE", "ポケモン": "#FFEDD5", "ジャニーズ系": "#FEF9C3", 
        "ジャンプ": "#DBEAFE", "あんスタ": "#F3E8FF", "その他": "#F1F5F9"
    }
    
    # 日付があるイベントをカレンダー形式に変換
    for e in [x for x in filtered if x['has_date']]:
        cal_events.append({
            "title": e['emoji'], # カレンダー内には絵文字をメインに表示
            "start": e['start'],
            "url": e['url'],
            "backgroundColor": colors.get(e['genre'], "#FFFFFF"),
            "borderColor": colors.get(e['genre'], "#CBD5E1"),
            "textColor": "#000000",
            "display": "block"
        })
    
    if not cal_events:
        st.info("現在、カレンダーに表示できる日付確定イベントがありません。全リストを確認してください。")
    else:
        calendar_options = {
            "initialView": "dayGridMonth",
            "height": "480px",
            "locale": "ja",
            "headerToolbar": {"left": "prev,next", "center": "title", "right": ""},
            "editable": False,
            "dayMaxEvents": True,
        }
        calendar(events=cal_events, options=calendar_options)
        st.caption("💡 カレンダーの絵文字をタップすると詳細が開きます。")

with tab2:
    if not filtered:
        st.info("該当するイベントがありません。")
    else:
        # 日付順に並び替え
        sorted_list = sorted(filtered, key=lambda x: (not x['has_date'], x['start'] or ""))
        for e in sorted_list:
            st.markdown(f"""
            <div class="event-card">
                <span class="badge time-badge">📍 {e['time']}</span>
                <span class="badge" style="background:#F1F5F9;">{e['emoji']} {e['genre']}</span>
                <a href="{e['url']}" target="_blank" class="event-title">{e['full_title']}</a>
                <div style="font-size:12px; color:#64748B; margin-top:4px;">📅 {e['start'] if e['has_date'] else '日付不明'} | 🚃 小山駅発</div>
            </div>
            """, unsafe_allow_html=True)
