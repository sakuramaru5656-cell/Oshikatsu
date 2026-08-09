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
    
    /* 詳細カードのデザイン */
    .detail-card {
        background: #F8FAFC; border: 2px solid #3B82F6; border-radius: 16px;
        padding: 20px; margin: 20px 0; animation: fadeIn 0.3s;
    }
    .event-card {
        background: white; border-radius: 12px; padding: 16px;
        margin-bottom: 12px; border: 1px solid #EDF2F7;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .badge {
        display: inline-block; padding: 2px 10px; border-radius: 9999px;
        font-size: 11px; font-weight: 600; margin-right: 5px;
    }
    .time-badge { background-color: #3B82F6; color: white; }
    
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    
    /* カレンダーのサイズ調整 */
    .fc { font-size: 0.9em !important; max-width: 100%; height: 500px; }
    .fc-event { cursor: pointer; border: none !important; }
    .fc-event-title { font-size: 1.3em !important; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- カテゴリー定義 ---
GENRES = {
    "VTuber": {"emoji": "🌈", "words": ["ホロライブ", "さくらみこ", "星街すいせい", "にじさんじ"]},
    "ポケモン": {"emoji": "🐾", "words": ["ポケモンセンター", "ポケモン", "ピカチュウ"]},
    "ジャニーズ系": {"emoji": "🎤", "words": ["timelesz", "Hey! Say! JUMP", "King & Prince", "なにわ男子", "Snow Man"]},
    "ジャンプ": {"emoji": "👒", "words": ["ワンピース", "ONE PIECE", "ナルト", "NARUTO"]},
    "あんスタ": {"emoji": "✨", "words": ["あんさんぶるスターズ", "あんスタ"]},
    "その他": {"emoji": "🎁", "words": ["コラボカフェ", "アニメ展示"]}
}
TIMES = ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"]

# --- データ取得 ---
@st.cache_data(ttl=3600)
def fetch_events():
    all_events = []
    headers = {"User-Agent": "Mozilla/5.0"}
    curr_year = datetime.now().year
    
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
                    
                    # 日付解析
                    start_dt = None
                    date_match = re.search(r'(\d+)月(\d+)日', title)
                    if date_match:
                        try:
                            month, day = int(date_match.group(1)), int(date_match.group(2))
                            start_dt = datetime(curr_year, month, day)
                        except: pass
                    
                    # 時間判定
                    loc = "1時間半以内"
                    if any(x in title for x in ["宇都宮", "ベルモール"]): loc = "30分以内"
                    elif any(x in title for x in ["大宮", "さいたま"]): loc = "1時間以内"
                    elif any(x in title for x in ["横浜", "幕張", "ぴあアリーナ", "Kアリーナ"]): loc = "2時間半以内"
                    elif any(x in title for x in ["大阪", "名古屋", "ドーム"]): loc = "それ以上"

                    all_events.append({
                        "id": f"{kw}-{title[:10]}",
                        "title": emoji,
                        "full_title": title,
                        "start": start_dt.strftime("%Y-%m-%d") if start_dt else None,
                        "url": link,
                        "genre": genre_name,
                        "time": loc,
                        "has_date": start_dt is not None,
                        "emoji": emoji
                    })
            except: pass
    return all_events

# --- メインロジック ---
st.title("推しイベ")
st.caption("小山駅発 🚃 イベント検索＆スケジュール")

# ボタン形式のフィルター
st.write("### 🔍 フィルター")
selected_genres = st.pills("ジャンル", list(GENRES.keys()), selection_mode="multi", default=list(GENRES.keys()))
selected_times = st.pills("小山からの時間", TIMES, selection_mode="multi", default=["30分以内", "1時間以内", "1時間半以内"])

# データ準備
data = fetch_events()
filtered = [e for e in data if e['genre'] in selected_genres and e['time'] in selected_times]

# 1. カレンダー表示
st.write("### 📅 月間カレンダー")
cal_events = []
colors = {"VTuber": "#E0F2FE", "ポケモン": "#FFEDD5", "ジャニーズ系": "#FEF9C3", "ジャンプ": "#DBEAFE", "あんスタ": "#F3E8FF", "その他": "#F1F5F9"}

for e in [x for x in filtered if x['has_date']]:
    cal_events.append({
        "id": e['id'],
        "title": e['emoji'],
        "start": e['start'],
        "backgroundColor": colors.get(e['genre'], "#FFFFFF"),
        "borderColor": "#E2E8F0",
        "extendedProps": {"full_title": e['full_title'], "url": e['url'], "time": e['time'], "way": e['genre']}
    })

# カレンダーの実行
state = calendar(events=cal_events, options={"initialView": "dayGridMonth", "locale": "ja", "height": "500px"})

# 2. 【重要】クリックした詳細をカレンダーの下に表示
if state.get("eventClick"):
    clicked = state["eventClick"]["event"]
    props = clicked["extendedProps"]
    st.markdown(f"""
        <div class="detail-card">
            <h3>{clicked['title']} イベント詳細</h3>
            <p><strong>{props['full_title']}</strong></p>
            <p><span class="badge time-badge">📍 {props['time']}</span> ジャンル: {props['way']}</p>
            <p><small>栃木県小山駅から {props['time']} 圏内です</small></p>
            <a href="{props['url']}" target="_blank">
                <button style="background:#3B82F6; color:white; border:none; padding:10px 20px; border-radius:8px; cursor:pointer;">
                    公式サイトを開く ↗️
                </button>
            </a>
        </div>
    """, unsafe_allow_html=True)
else:
    st.info("💡 カレンダーの絵文字をタップすると、ここに詳細が表示されます。")

# 3. 週間表示（今週の予定）
st.divider()
st.write("### 📋 今週（1週間以内）の予定")
today = datetime.now().date()
one_week_later = today + timedelta(days=7)

weekly_events = [e for e in filtered if e['has_date'] and today <= datetime.strptime(e['start'], "%Y-%m-%d").date() <= one_week_later]

if not weekly_events:
    st.write("今週の予定はありません。")
else:
    for e in sorted(weekly_events, key=lambda x: x['start']):
        st.markdown(f"""
        <div class="event-card">
            <span class="badge" style="background:#F1F5F9;">{e['emoji']} {e['genre']}</span>
            <span class="badge time-badge">{e['time']}</span>
            <a href="{e['url']}" target="_blank" class="event-title">{e['full_title']}</a>
            <div style="font-size:12px; color:#64748B; margin-top:4px;">📅 {e['start']}</div>
        </div>
        """, unsafe_allow_html=True)

# 4. 全リスト（日付未定含む）
with st.expander("🔍 全てのリストを表示"):
    for e in sorted(filtered, key=lambda x: (not x['has_date'], x['start'] or "")):
        st.write(f"{e['emoji']} {e['start'] if e['has_date'] else '日付未定'} : [{e['full_title']}]({e['url']}) ({e['time']})")
