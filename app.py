import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import re
from concurrent.futures import ThreadPoolExecutor

# --- ページ設定とデザイン ---
st.set_page_config(page_title="推しイベ", page_icon="✨", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@700;800&display=swap');
    html, body, [class*="css"] { font-family: 'M PLUS Rounded 1c', sans-serif; background-color: #FFFDF0; }
    .stApp { background: #FFFDF0; }
    .fc { background: white !important; border-radius: 20px !important; border: 4px solid #3B82F6 !important; padding: 10px; box-shadow: 0 8px 20px rgba(0,0,0,0.05); }
    .fc-event { border-radius: 8px !important; border: none !important; padding: 4px 6px !important; font-weight: 800 !important; cursor: pointer; }
    .pop-card { background: white; border-radius: 20px; padding: 20px; margin-top: 15px; border: 4px solid #3B82F6; box-shadow: 6px 6px 0px #BFDBFE; }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 50px; font-size: 11px; font-weight: bold; color: white; margin-right: 5px; }
    .stButton>button { width: 100%; border-radius: 20px; font-weight: 800; border: 2px solid #3B82F6; }
    </style>
    """, unsafe_allow_html=True)

# --- ジャンル設定 ---
GENRES = {
    "VTuber": {"emoji": "🌈", "words": ["ホロライブ", "にじさんじ", "ぶいすぽ"], "color": "#F472B6"},
    "ポケモン": {"emoji": "🐾", "words": ["ポケモンセンター", "ポケモン"], "color": "#3B82F6"},
    "アイドル": {"emoji": "🎤", "words": ["Snow Man", "なにわ男子", "King & Prince", "timelesz", "Hey! Say! JUMP"], "color": "#FB923C"},
    "あんスタ": {"emoji": "✨", "words": ["あんさんぶるスターズ", "あんスタ"], "color": "#A78BFA"},
    "ジャンプ": {"emoji": "👒", "words": ["ワンピース", "ONE PIECE", "ナルト"], "color": "#F87171"},
    "テーマパーク": {"emoji": "🎡", "words": ["富士急ハイランド", "ピューロランド", "USJ", "ディズニー"], "color": "#10B981"},
    "その他": {"emoji": "🎁", "words": ["アニメ コラボ", "カフェ"], "color": "#94A3B8"}
}

TIME_OPTIONS = ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"]

def get_access_info(loc):
    guides = {
        "30分以内": "🚃 宇都宮線 (25分) / 🚗 車 (40分)",
        "1時間以内": "🚄 新幹線 (15分) / 🚃 快速 (45分)",
        "1時間半以内": "🚄 新幹線 (40分) / 🚃 上野東京ライン (80分)",
        "2時間半以内": "🚃 湘南新宿ライン (130分) / 🚄 新幹線+JR",
        "それ以上": "🚄 新幹線 / ✈️ 飛行機"
    }
    return guides.get(loc, "交通機関を確認")

# --- 日付抽出エンジン (2026年対応) ---
def extract_dates(text):
    year = 2026
    sep = r'[〜~ー\-\s－]+'
    m = re.search(r'(\d{1,2})[./月](\d{1,2}).*?{sep}(\d{1,2})[./月](\d{1,2})'.format(sep=sep), text)
    if m:
        try:
            s, e = datetime(year, int(m.group(1)), int(m.group(2))), datetime(year, int(m.group(3)), int(m.group(4)))
            if e < s: e = datetime(year + 1, int(m.group(3)), int(m.group(4)))
            return s, e
        except: pass
    m = re.search(r'(\d{1,2})[./月](\d{1,2})', text)
    if m:
        try:
            dt = datetime(year, int(m.group(1)), int(m.group(2)))
            return dt, dt
        except: pass
    # 日付がない場合は今日を表示（カレンダーのどこかに出るようにする）
    today = datetime.now()
    return today, today

# --- スクレイピング (スレッド用) ---
def fetch_keyword(kw, gen, emoji, color):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    url = f"https://collabo-cafe.com/?s={kw}"
    res_list = []
    try:
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for art in soup.select('article')[:6]:
                title = (art.find('h2') or art.select_one('.entry-title')).get_text().strip()
                link = art.find('a')['href']
                start, end = extract_dates(title)
                
                loc = "1時間半以内"
                if any(x in title for x in ["宇都宮", "ベルモール"]): loc = "30分以内"
                elif any(x in title for x in ["大宮", "さいたま"]): loc = "1時間以内"
                elif any(x in title for x in ["横浜", "幕張", "千葉", "富士急"]): loc = "2時間半以内"
                elif any(x in title for x in ["大阪", "名古屋", "USJ"]): loc = "それ以上"

                res_list.append({
                    "id": f"{kw}-{title[:10]}", "title": f"{emoji} {kw}",
                    "full_title": title, "start": start, "end": end,
                    "genre": gen, "time": loc, "url": link, "color": color
                })
    except: pass
    return res_list

@st.cache_data(ttl=1800)
def fetch_all_data():
    all_data = []
    # 検索を安定させるため、主要な単語に絞る
    tasks = []
    for gen, info in GENRES.items():
        for kw in info["words"][:2]: # 1ジャンル2単語に絞って質を上げる
            tasks.append((kw, gen, info["emoji"], info["color"]))

    with ThreadPoolExecutor(max_workers=5) as executor: # スレッドを5に下げて安定化
        futures = [executor.submit(fetch_keyword, *t) for t in tasks]
        for f in futures:
            all_data.extend(f.result())
    
    if not all_data: return []
    # 重複削除
    df = pd.DataFrame(all_data).drop_duplicates(subset=['full_title'])
    return df.to_dict('records')

# --- メイン ---
st.title("✨ 推しイベ")
st.write("栃木県小山駅発 🚃 冒険スケジュール")

if st.button("🔄 最新の情報に更新する"):
    st.cache_data.clear()
    st.rerun()

c1, c2 = st.columns(2)
with c1: sel_gen = st.multiselect("🌈 ジャンル", list(GENRES.keys()), default=list(GENRES.keys()))
with c2: sel_time = st.multiselect("⏳ 時間", TIME_OPTIONS, default=TIME_OPTIONS)

with st.spinner("🚀 スキャン中..."):
    data = fetch_all_data()
    filtered = [e for e in data if e['genre'] in sel_gen and e['time'] in sel_time]

if not filtered:
    st.warning("現在イベントが取得できませんでした。時間をおいて『更新』ボタンを押してください。")
else:
    cal_events = []
    for e in filtered:
        cal_events.append({
            "id": e['id'], "title": e['title'], "start": e['start'].strftime("%Y-%m-%d"), 
            "end": (e['end'] + timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": e['color'], "borderColor": "white",
            "extendedProps": {"full_title": e['full_title'], "url": e['url'], "time": e['time'], "gen": e['genre']}
        })

    state = calendar(events=cal_events, options={"initialView": "dayGridMonth", "locale": "ja", "height": "auto", "headerToolbar": {"left": "prev,next", "center": "title", "right": ""}})

    if state.get("eventClick"):
        p = state["eventClick"]["event"]["extendedProps"]
        st.markdown(f"""<div class="pop-card"><h3>✨ 詳細</h3><b>{p['full_title']}</b><br><br>
            <span class="badge" style="background:{GENRES[p['gen']]['color']}">{p['gen']}</span>
            <span class="badge" style="background:#3B82F6">📍 小山から{p['time']}</span><br><br>
            <small>🚃 経路目安: {get_access_info(p['time'])}</small><br><br>
            <a href="{p['url']}" target="_blank"><button style="background:#3B82F6; color:white; border:none; padding:12px; border-radius:10px; cursor:pointer;">公式サイトへ GO!</button></a></div>""", unsafe_allow_html=True)

    st.subheader("📋 ピックアップ")
    for e in sorted(filtered, key=lambda x: x['start'])[:15]:
        st.markdown(f"""<div style="background:white; border-radius:15px; padding:15px; margin-bottom:10px; border-left:8px solid {e['color']}; box-shadow:2px 2px 5px rgba(0,0,0,0.05);">
            <small>{e['start'].strftime('%m/%d')} 〜 {e['end'].strftime('%m/%d')} | {e['genre']}</small><br>
            <b>{e['full_title']}</b><br><small style="color:#3B82F6;">🚃 {get_access_info(e['time'])}</small></div>""", unsafe_allow_html=True)
