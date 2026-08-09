import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import re
from concurrent.futures import ThreadPoolExecutor

# --- ページ設定とポップなデザイン ---
st.set_page_config(page_title="推しイベ", page_icon="✨", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@700;800&display=swap');
    html, body, [class*="css"] { font-family: 'M PLUS Rounded 1c', sans-serif; background-color: #FFFDF0; }
    .stApp { background: #FFFDF0; }
    
    /* ポップなカレンダー */
    .fc { background: white !important; border-radius: 20px !important; border: 4px solid #3B82F6 !important; padding: 10px; box-shadow: 0 8px 20px rgba(0,0,0,0.05); }
    .fc-event { border-radius: 8px !important; border: none !important; padding: 4px 6px !important; font-weight: 800 !important; cursor: pointer; }
    .fc-toolbar-title { color: #1E40AF !important; font-size: 1.2em !important; background: #DBEAFE; padding: 5px 15px; border-radius: 50px; }
    
    /* ポケモン図鑑風カード */
    .pop-card { background: white; border-radius: 20px; padding: 20px; margin-top: 15px; border: 4px solid #3B82F6; box-shadow: 6px 6px 0px #BFDBFE; }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 50px; font-size: 11px; font-weight: bold; color: white; margin-right: 5px; }
    
    /* フィルタエリア */
    .filter-box { background: white; border-radius: 15px; padding: 15px; border: 2px solid #3B82F6; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- ジャンル・絵文字設定 ---
GENRES = {
    "VTuber": {"emoji": "🌈", "keys": ["ホロライブ", "にじさんじ", "ぶいすぽ", "さくらみこ", "星街", "マリン"], "color": "#F472B6"},
    "ポケモン": {"emoji": "🐾", "keys": ["ポケモン", "ピカチュウ", "ポケカ", "ポケセン"], "color": "#3B82F6"},
    "アイドル": {"emoji": "🎤", "keys": ["timelesz", "JUMP", "King & Prince", "なにわ男子", "Snow Man", "SixTONES", "WEST", "Aぇ"], "color": "#FB923C"},
    "あんスタ": {"emoji": "✨", "keys": ["あんスタ", "あんさんぶるスターズ"], "color": "#A78BFA"},
    "ジャンプ": {"emoji": "👒", "keys": ["ワンピース", "ONE PIECE", "ナルト", "NARUTO"], "color": "#F87171"},
    "テーマパーク": {"emoji": "🎡", "words": ["富士急", "ピューロランド", "USJ", "ユニバ", "ディズニー", "ナンジャタウン", "ジョイポリス"], "color": "#10B981"},
    "その他": {"emoji": "🎁", "keys": ["コラボ", "カフェ", "フェア", "一番くじ"], "color": "#94A3B8"}
}

TIME_OPTIONS = ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"]

def get_access_info(loc):
    guides = {
        "30分以内": "🚃 宇都宮線 (25分) / 🚗 40分",
        "1時間以内": "🚄 新幹線 (15分) / 🚃 快速 (45分)",
        "1時間半以内": "🚄 新幹線 (40分) / 🚃 在来線 (80分)",
        "2時間半以内": "🚃 湘南新宿ライン (130分)",
        "それ以上": "🚄 新幹線 / ✈️ 飛行機 / 🚌 高速バス"
    }
    return guides.get(loc, "交通機関を確認")

# --- 日付解析ロジック ---
def parse_dates_v4(text):
    year = 2026 # 2026年8月として処理
    sep = r'[〜~ー\-\s－]+'
    # 期間: 8/1〜8/31
    m = re.search(r'(\d{1,2})[./月](\d{1,2}).*?{sep}(\d{1,2})[./月](\d{1,2})'.format(sep=sep), text)
    if m:
        try:
            s = datetime(year, int(m.group(1)), int(m.group(2)))
            e = datetime(year, int(m.group(3)), int(m.group(4)))
            if e < s: e = datetime(year + 1, int(m.group(3)), int(m.group(4)))
            return s, e
        except: pass
    # 単発
    m = re.search(r'(\d{1,2})[./月](\d{1,2})', text)
    if m:
        try:
            dt = datetime(year, int(m.group(1)), int(m.group(2)))
            return dt, dt
        except: pass
    return None, None

@st.cache_data(ttl=1800)
def fetch_latest_events():
    """最新記事一覧から一括取得してフィルタリングする"""
    all_events = []
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # 最新1〜3ページ程度をスキャン（検索に頼らず新着から拾う）
    for page in range(1, 4):
        url = f"https://collabo-cafe.com/page/{page}/"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            for art in soup.select('article'):
                title = (art.find('h2') or art.select_one('.entry-title')).get_text().strip()
                link = art.find('a')['href']
                
                # ジャンル判定
                matched_genre = "その他"
                for g_name, info in GENRES.items():
                    target_keys = info.get("keys", []) + info.get("words", [])
                    if any(k in title for k in target_keys):
                        matched_genre = g_name
                        break
                
                start, end = parse_dates_v4(title)
                if not start: continue # 日付不明はスキップ
                
                # エリア判定
                loc = "1時間半以内"
                if any(x in title for x in ["宇都宮", "ベルモール"]): loc = "30分以内"
                elif any(x in title for x in ["大宮", "さいたま"]): loc = "1時間以内"
                elif any(x in title for x in ["横浜", "幕張", "千葉", "富士急"]): loc = "2時間半以内"
                elif any(x in title for x in ["大阪", "名古屋", "USJ"]): loc = "それ以上"

                all_events.append({
                    "id": f"{matched_genre}-{title[:10]}",
                    "emoji_title": f"{GENRES[matched_genre]['emoji']} {matched_genre}",
                    "full_title": title, "start": start, "end": end,
                    "genre": matched_genre, "time": loc, "url": link, "color": GENRES[matched_genre]['color']
                })
        except: pass
    return pd.DataFrame(all_events).drop_duplicates(subset=['full_title']).to_dict('records')

# --- メイン画面 ---
st.title("✨ 推しイベ")

# カレンダーの上の操作パネル
with st.container():
    st.markdown('<div class="filter-box">', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: sel_gen = st.multiselect("🌈 ジャンル", list(GENRES.keys()), default=list(GENRES.keys()))
    with c2: sel_time = st.multiselect("⏳ 小山からの時間", TIME_OPTIONS, default=TIME_OPTIONS)
    if st.button("🔄 最新の情報に更新する"):
        st.cache_data.clear()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with st.spinner("🚀 最新のイベントをスキャン中..."):
    data = fetch_latest_events()
    filtered = [e for e in data if e['genre'] in sel_gen and e['time'] in sel_time]

# カレンダー表示
st.subheader("📅 スケジュール")
if not filtered:
    st.warning("イベントが見つかりませんでした。更新ボタンを押すか、ジャンルを増やしてみてください。")
else:
    cal_events = []
    for e in filtered:
        cal_events.append({
            "id": e['id'], "title": e['emoji_title'], 
            "start": e['start'].strftime("%Y-%m-%d"), 
            "end": (e['end'] + timedelta(days=1)).strftime("%Y-%m-%d"),
            "backgroundColor": e['color'], "borderColor": "white",
            "extendedProps": {"full_title": e['full_title'], "url": e['url'], "time": e['time'], "gen": e['genre']}
        })

    state = calendar(events=cal_events, options={"initialView": "dayGridMonth", "locale": "ja", "height": "auto", "headerToolbar": {"left": "prev,next", "center": "title", "right": ""}})

    if state.get("eventClick"):
        p = state["eventClick"]["event"]["extendedProps"]
        st.markdown(f"""
            <div class="pop-card">
                <h3>✨ 詳細データ</h3>
                <b>{p['full_title']}</b><br><br>
                <span class="badge" style="background:{GENRES[p['gen']]['color']}">{p['gen']}</span>
                <span class="badge" style="background:#3B82F6">📍 小山から{p['time']}</span><br><br>
                <small>🚃 経路目安: {get_access_info(p['time'])}</small><br><br>
                <a href="{p['url']}" target="_blank"><button style="width:100%; background:#3B82F6; color:white; border:none; padding:12px; border-radius:10px; cursor:pointer; font-weight:bold;">公式サイトへ GO!</button></a>
            </div>
        """, unsafe_allow_html=True)

# 週間・全件リスト
st.subheader("📋 ピックアップ")
for e in sorted(filtered, key=lambda x: x['start']):
    st.markdown(f"""
        <div style="background:white; border-radius:15px; padding:15px; margin-bottom:10px; border-left:8px solid {e['color']}; box-shadow:2px 2px 5px rgba(0,0,0,0.05);">
            <small>{e['start'].strftime('%m/%d')} 〜 {e['end'].strftime('%m/%d')} | {e['genre']}</small><br>
            <b>{e['full_title']}</b><br>
            <small style="color:#3B82F6;">🚃 {get_access_info(e['time'])}</small>
        </div>
    """, unsafe_allow_html=True)
