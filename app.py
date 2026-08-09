import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import re

# --- ページ設定 ---
st.set_page_config(page_title="推しイベ", page_icon="✨", layout="centered")

# --- ポップなUIデザイン ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@700;800&display=swap');
    html, body, [class*="css"] { font-family: 'M PLUS Rounded 1c', sans-serif; background-color: #FFFDF0; }
    .stApp { background: #FFFDF0; }
    .fc { background: white !important; border-radius: 20px !important; border: 4px solid #3B82F6 !important; padding: 10px; }
    .fc-event { border-radius: 8px !important; border: 1px solid rgba(0,0,0,0.1) !important; padding: 4px 6px !important; font-weight: 800 !important; cursor: pointer; }
    .pop-card { background: white; border-radius: 20px; padding: 20px; margin-top: 15px; border: 4px solid #3B82F6; box-shadow: 6px 6px 0px #BFDBFE; }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 50px; font-size: 11px; font-weight: bold; color: white; margin-right: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- ジャンル・交通設定 ---
GENRES = {
    "VTuber": {"emoji": "🌈", "words": ["ホロライブ", "さくらみこ", "にじさんじ"], "color": "#F472B6"},
    "ポケモン": {"emoji": "🐾", "words": ["ポケモンセンター", "ポケモン"], "color": "#3B82F6"},
    "アイドル": {"emoji": "🎤", "words": ["timelesz", "Hey! Say! JUMP", "King & Prince", "Snow Man", "ジャニーズ"], "color": "#FB923C"},
    "ジャンプ": {"emoji": "👒", "words": ["ワンピース", "ONE PIECE", "ナルト", "NARUTO"], "color": "#F87171"},
    "あんスタ": {"emoji": "✨", "words": ["あんさんぶるスターズ", "あんスタ"], "color": "#A78BFA"},
    "テーマパーク": {"emoji": "🎡", "words": ["富士急", "ピューロランド", "USJ", "ディズニー", "ナンジャ"], "color": "#10B981"},
    "その他": {"emoji": "🎁", "words": ["アニメ コラボ"], "color": "#94A3B8"}
}

def get_access_info(loc):
    guides = {"30分以内": "🚃 宇都宮線 (25分) / 🚗 40分", "1時間以内": "🚄 新幹線 (15分) / 🚃 快速 (45分)",
              "1時間半以内": "🚄 新幹線 (40分) / 🚃 上野東京ライン (80分)", "2時間半以内": "🚃 湘南新宿ライン (130分)", "それ以上": "🚄 新幹線 / ✈️ 飛行機"}
    return guides.get(loc, "交通機関を確認")

# --- 日付抽出エンジン（強化版） ---
def parse_dates_flexible(text):
    year = datetime.now().year
    # 期間形式 (◯/◯〜◯/◯)
    m = re.search(r'(\d{1,2})[./月](\d{1,2}).*?[〜~ー\-\s－]+(\d{1,2})[./月](\d{1,2})', text)
    if m:
        try:
            start = datetime(year, int(m.group(1)), int(m.group(2)))
            end = datetime(year, int(m.group(3)), int(m.group(4)))
            if end < start: end = datetime(year + 1, int(m.group(3)), int(m.group(4)))
            return start, end
        except: pass
    # 単発形式 (◯/◯)
    m = re.search(r'(\d{1,2})[./月](\d{1,2})', text)
    if m:
        try:
            dt = datetime(year, int(m.group(1)), int(m.group(2)))
            return dt, dt
        except: pass
    return None, None

@st.cache_data(ttl=1800)
def fetch_all_data():
    all_events = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    for gen, info in GENRES.items():
        for kw in info["words"][:3]:
            url = f"https://collabo-cafe.com/?s={kw}"
            try:
                res = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(res.text, 'html.parser')
                # 記事抽出のセレクタをより汎用的に
                articles = soup.find_all('article') or soup.select('.post-list-item')
                for art in articles[:5]:
                    title_el = art.find('h2') or art.select_one('.entry-title')
                    if not title_el: continue
                    title = title_el.get_text().strip()
                    link = art.find('a')['href']
                    
                    start, end = parse_dates_flexible(title)
                    loc = "1時間半以内"
                    if any(x in title for x in ["宇都宮", "ベルモール"]): loc = "30分以内"
                    elif any(x in title for x in ["大宮", "さいたま"]): loc = "1時間以内"
                    elif any(x in title for x in ["横浜", "幕張", "千葉", "富士急"]): loc = "2時間半以内"
                    elif any(x in title for x in ["大阪", "名古屋", "USJ"]): loc = "それ以上"

                    all_events.append({
                        "id": f"{kw}-{title[:10]}", "emoji_title": f"{info['emoji']} {kw}",
                        "full_title": title, "start": start, "end": end,
                        "genre": gen, "time": loc, "url": link, "color": info["color"], "has_date": start is not None
                    })
            except: pass
    return all_events

# --- メイン画面 ---
st.title("✨ 推しイベ")
st.write("栃木県小山駅発 🚃 開催期間を一本線で表示！")

c1, c2 = st.columns(2)
with c1: sel_gen = st.multiselect("ジャンル", list(GENRES.keys()), default=list(GENRES.keys()))
with c2: sel_time = st.multiselect("距離(時間)", list(get_access_info("").replace("交通機関を確認","").split("\n")) or ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"], default=["30分以内", "1時間以内", "1時間半以内"])

raw_data = fetch_all_data()
# フィルタリング
filtered = [e for e in raw_data if e['genre'] in sel_gen and e['time'] in sel_time]

# カレンダー表示
cal_events = []
for e in [x for x in filtered if x['has_date']]:
    cal_events.append({
        "id": e['id'], "title": e['emoji_title'], 
        "start": e['start'].strftime("%Y-%m-%d"), 
        "end": (e['end'] + timedelta(days=1)).strftime("%Y-%m-%d"),
        "backgroundColor": e['color'], "borderColor": "white",
        "extendedProps": {"full_title": e['full_title'], "url": e['url'], "time": e['time'], "gen": e['genre']}
    })

state = calendar(events=cal_events, options={"initialView": "dayGridMonth", "locale": "ja", "height": "auto"})

if state.get("eventClick"):
    p = state["eventClick"]["event"]["extendedProps"]
    st.markdown(f"""<div class="pop-card"><h3>✨ 詳細データ</h3><b>{p['full_title']}</b><br><br>
                <span class="badge" style="background:{GENRES[p['gen']]['color']}">{p['gen']}</span>
                <span class="badge" style="background:#3B82F6">📍 小山から{p['time']}</span><br><br>
                <small>🚃 経路目安: {get_access_info(p['time'])}</small><br><br>
                <a href="{p['url']}" target="_blank"><button style="width:100%; background:#3B82F6; color:white; border:none; padding:12px; border-radius:10px; cursor:pointer;">公式サイトへ GO!</button></a></div>""", unsafe_allow_html=True)

# 週間・全件リスト
st.subheader("📋 イベントリスト")
if not filtered:
    st.info("条件に合うイベントが見つかりませんでした。ジャンルを増やしてみてください。")
else:
    for e in sorted(filtered, key=lambda x: (not x['has_date'], x['start'] if x['has_date'] else datetime.max)):
        date_str = f"{e['start'].strftime('%m/%d')}〜{e['end'].strftime('%m/%d')}" if e['has_date'] else "日付不明"
        st.markdown(f"""<div style="background:white; border-radius:15px; padding:15px; margin-bottom:10px; border-left:8px solid {e['color']}; box-shadow:2px 2px 5px rgba(0,0,0,0.05);">
                    <small>{date_str} | {e['genre']}</small><br><b>{e['full_title']}</b><br>
                    <small style="color:#3B82F6;">🚃 {get_access_info(e['time'])}</small></div>""", unsafe_allow_html=True)
