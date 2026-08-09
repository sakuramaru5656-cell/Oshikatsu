import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import re

# --- ページ設定とデザインCSS ---
st.set_page_config(page_title="推しイベ", page_icon="✨", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@700;800&display=swap');
    html, body, [class*="css"] { font-family: 'M PLUS Rounded 1c', sans-serif; background-color: #FFFDF0; }
    .stApp { background: #FFFDF0; }
    .fc { background: #FFFFFF !important; border-radius: 20px !important; border: 4px solid #3B82F6 !important; padding: 10px; }
    .fc-event { border-radius: 6px !important; border: none !important; padding: 4px 6px !important; font-weight: 800 !important; cursor: pointer; }
    .pop-card { background: white; border-radius: 20px; padding: 20px; margin-top: 15px; border: 4px solid #3B82F6; box-shadow: 6px 6px 0px #BFDBFE; }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 50px; font-size: 11px; font-weight: bold; color: white; margin-right: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 設定データ ---
GENRES = {
    "VTuber": {"emoji": "🌈", "words": ["ホロライブ", "にじさんじ", "ぶいすぽ"], "color": "#F472B6"},
    "ポケモン": {"emoji": "🐾", "words": ["ポケモンセンター", "ポケモン", "ポケカ"], "color": "#3B82F6"},
    "アイドル": {"emoji": "🎤", "words": ["timelesz", "Hey! Say! JUMP", "King & Prince", "なにわ男子", "Snow Man", "SixTONES"], "color": "#FB923C"},
    "あんスタ": {"emoji": "✨", "words": ["あんスタ", "あんさんぶるスターズ"], "color": "#A78BFA"},
    "ジャンプ": {"emoji": "👒", "words": ["ワンピース", "ONE PIECE", "ナルト", "NARUTO"], "color": "#F87171"},
    "テーマパーク": {"emoji": "🎡", "words": ["富士急", "ピューロランド", "USJ", "ディズニー", "ナンジャタウン"], "color": "#10B981"},
    "その他": {"emoji": "🎁", "words": ["アニメ コラボ", "原画展"], "color": "#94A3B8"}
}

AREAS = ["栃木", "埼玉", "東京", "神奈川", "千葉", "遠方"]
TIME_LABELS = ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"]

def get_access_info(base_station, loc):
    guides = {
        "30分以内": "🚃 在来線 (約25分) / 🚗 約40分",
        "1時間以内": "🚄 新幹線 (約15分) / 🚃 快速 (約45分)",
        "1時間半以内": "🚄 新幹線 (約40分) / 🚃 在来線 (約80分)",
        "2時間半以内": "🚃 湘南新宿ライン等 (約130分)",
        "それ以上": "🚄 新幹線 / ✈️ 飛行機 / 🚌 高速バス"
    }
    return f"{base_station}駅から " + guides.get(loc, "交通機関を確認")

def parse_dates(text):
    year = datetime.now().year
    sep = r'[〜~ー\-\s－]+'
    m = re.search(r'(\d{1,2})[./月](\d{1,2}).*?{sep}(\d{1,2})[./月](\d{1,2})'.format(sep=sep), text)
    if m:
        try:
            start = datetime(year, int(m.group(1)), int(m.group(2)))
            end = datetime(year, int(m.group(3)), int(m.group(4)))
            if end < start: end = datetime(year + 1, int(m.group(3)), int(m.group(4)))
            return start, end
        except: pass
    m = re.search(r'(\d{1,2})[./月](\d{1,2})', text)
    if m:
        try:
            dt = datetime(year, int(m.group(1)), int(m.group(2)))
            return dt, dt
        except: pass
    return None, None

@st.cache_data(ttl=1800)
def fetch_data(selected_genres, custom_keywords):
    all_events = []
    keywords = []
    for g in selected_genres: keywords.extend(GENRES[g]["words"])
    if custom_keywords: keywords.extend([k.strip() for k in custom_keywords.split(",")])

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"}
    
    for kw in list(set(keywords))[:12]:
        url = f"https://collabo-cafe.com/?s={kw}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            # セレクタを柔軟に変更
            articles = soup.select('article') or soup.select('.post-list-item')
            for art in articles[:5]:
                title_tag = art.find('h2') or art.select_one('.entry-title')
                if not title_tag: continue
                title = title_tag.get_text().strip()
                link = art.find('a')['href']
                
                start, end = parse_dates(title)
                
                # エリア・時間判定
                loc_name, dist = "東京", "1時間半以内"
                if any(x in title for x in ["宇都宮", "ベルモール", "栃木"]): loc_name, dist = "栃木", "30分以内"
                elif any(x in title for x in ["大宮", "さいたま", "浦和"]): loc_name, dist = "埼玉", "1時間以内"
                elif any(x in title for x in ["横浜", "ぴあアリーナ", "Kアリーナ"]): loc_label, dist = "神奈川", "2時間半以内"
                elif any(x in title for x in ["幕張", "千葉", "富士急"]): loc_name, dist = "千葉", "2時間半以内"
                elif any(x in title for x in ["大阪", "名古屋", "USJ", "福岡"]): loc_name, dist = "遠方", "それ以上"

                emoji, color = "🔍", "#94A3B8"
                for g, info in GENRES.items():
                    if any(w in title or w in kw for w in info["words"]):
                        emoji, color = info["emoji"], info["color"]
                        break

                all_events.append({
                    "id": f"{kw}-{title[:10]}", "title": f"{emoji} {kw}",
                    "full_title": title, "start": start, "end": end,
                    "time": dist, "area": loc_name, "url": link, "color": color,
                    "has_date": start is not None
                })
        except: pass
    return all_events

# --- メイン画面 ---
st.title("✨ 推しイベ")

with st.sidebar:
    st.header("🚉 出発設定")
    departure_station = st.text_input("出発駅", value="小山")
    st.header("🔍 検索")
    sel_gen = st.multiselect("ジャンル", list(GENRES.keys()), default=["VTuber", "ポケモン", "アイドル", "テーマパーク"])
    custom_input = st.text_input("自由検索ワード", help="カンマ区切り")
    st.header("📍 エリア・距離")
    sel_areas = st.multiselect("開催エリア", AREAS, default=AREAS)
    sel_time = st.multiselect("所要時間", TIME_LABELS, default=["30分以内", "1時間以内", "1時間半以内", "2時間半以内"])

with st.status("イベント情報をスキャン中...") as status:
    raw_data = fetch_data(sel_gen, custom_input)
    filtered = [e for e in raw_data if e['time'] in sel_time and (e['area'] in sel_areas or e['area']=="遠方" and "遠方" in str(sel_areas))]
    status.update(label="スキャン完了！", state="complete")

# 1. カレンダー
st.subheader("📅 スケジュール")
cal_events = []
for e in [x for x in filtered if x['has_date']]:
    cal_events.append({
        "id": e['id'], "title": e['title'], 
        "start": e['start'].strftime("%Y-%m-%d"), 
        "end": (e['end'] + timedelta(days=1)).strftime("%Y-%m-%d"),
        "backgroundColor": e['color'], "borderColor": "white",
        "extendedProps": {"full_title": e['full_title'], "url": e['url'], "time": e['time'], "area": e['area']}
    })

if not cal_events:
    st.info("カレンダーに表示できる日付確定イベントが現在ありません。下のリストを確認してください。")
else:
    state = calendar(events=cal_events, options={"initialView": "dayGridMonth", "locale": "ja", "height": "auto"})
    if state.get("eventClick"):
        p = state["eventClick"]["event"]["extendedProps"]
        st.markdown(f"""<div class="pop-card"><h3>✨ 詳細</h3><b>{p['full_title']}</b><br><br>
        <span class="badge" style="background:#3B82F6">📍 {p['area']}</span><br><br>
        <small>🚃 {get_access_info(departure_station, p['time'])}</small><br><br>
        <a href="{p['url']}" target="_blank"><button style="width:100%; background:#3B82F6; color:white; border:none; padding:12px; border-radius:10px; cursor:pointer; font-weight:bold;">公式サイト GO!</button></a></div>""", unsafe_allow_html=True)

# 2. リスト
st.subheader("📋 ピックアップリスト")
if not filtered:
    st.warning("イベントが見つかりませんでした。条件を広げてみてください。")
else:
    for e in sorted(filtered, key=lambda x: (not x['has_date'], x['start'] if x['has_date'] else datetime.max)):
        date_str = f"{e['start'].strftime('%m/%d')} 〜 {e['end'].strftime('%m/%d')}" if e['has_date'] else "📅 日付はリンク先で確認"
        st.markdown(f"""<div style="background:white; border-radius:15px; padding:15px; margin-bottom:10px; border-left:8px solid {e['color']}; box-shadow:2px 2px 5px rgba(0,0,0,0.05);">
        <small>{date_str} | {e['area']}</small><br><b>{e['full_title']}</b><br>
        <small style="color:#3B82F6;">🚃 {get_access_info(departure_station, e['time'])}</small></div>""", unsafe_allow_html=True)
