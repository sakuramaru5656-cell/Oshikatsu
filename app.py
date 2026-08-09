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
    html, body, [class*="css"] { font-family: 'M PLUS Rounded 1c', sans-serif; background-color: #FFFDF0; }
    .stApp { background: #FFFDF0; }
    
    /* カレンダーデザイン */
    .fc { background: white !important; border-radius: 20px !important; border: 4px solid #3B82F6 !important; padding: 10px; }
    .fc-event { border-radius: 8px !important; border: none !important; padding: 4px 6px !important; font-weight: 800 !important; cursor: pointer; }
    
    /* ポップなカード */
    .pop-card { background: white; border-radius: 20px; padding: 20px; margin-top: 15px; border: 4px solid #3B82F6; box-shadow: 6px 6px 0px #BFDBFE; }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 50px; font-size: 11px; font-weight: bold; color: white; margin-right: 5px; }
    
    /* フィルター部分のスタイル */
    .filter-container { background: #FFFFFF; border-radius: 15px; padding: 20px; border: 2px solid #3B82F6; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 定数定義 ---
GENRES = {
    "VTuber": {"emoji": "🌈", "words": ["ホロライブ", "にじさんじ", "ぶいすぽ", "さくらみこ", "宝鐘マリン", "星街すいせい"], "color": "#F472B6"},
    "ポケモン": {"emoji": "🐾", "words": ["ポケモンセンター", "ポケモン", "ポケカ", "ピカチュウ"], "color": "#3B82F6"},
    "アイドル": {"emoji": "🎤", "words": ["Snow Man", "King & Prince", "なにわ男子", "SixTONES", "Hey! Say! JUMP", "timelesz", "ライブ", "ツアー"], "color": "#FB923C"},
    "あんスタ": {"emoji": "✨", "words": ["あんスタ", "あんさんぶるスターズ"], "color": "#A78BFA"},
    "ジャンプ": {"emoji": "👒", "words": ["ワンピース", "ONE PIECE", "ナルト", "NARUTO", "ジャンプショップ"], "color": "#F87171"},
    "テーマパーク": {"emoji": "🎡", "words": ["富士急ハイランド", "サンリオピューロランド", "USJ", "ディズニー", "ナンジャタウン"], "color": "#10B981"},
    "その他": {"emoji": "🎁", "words": ["コラボ", "イベント", "ポップアップ"], "color": "#94A3B8"}
}

TIME_OPTIONS = ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"]

def get_access_info(loc):
    guides = {
        "30分以内": "🚃 宇都宮線 (25分) / 🚗 車 (40分)",
        "1時間以内": "🚄 新幹線 (15分) / 🚃 快速 (45分)",
        "1時間半以内": "🚄 新幹線 (40分) / 🚃 在来線 (80分)",
        "2時間半以内": "🚃 湘南新宿ライン (130分) / 🚄 新幹線+JR",
        "それ以上": "🚄 新幹線 / ✈️ 飛行機 / 🚌 高速バス"
    }
    return guides.get(loc, "交通機関を確認してください")

# --- 高度な日付抽出エンジン ---
def parse_dates_v3(text):
    year = datetime.now().year
    sep = r'[〜~ー\-\s－]+'
    # 期間形式
    m = re.search(r'(\d{1,2})[./月](\d{1,2})[日]?{sep}(\d{1,2})[./月](\d{1,2})[日]?'.format(sep=sep), text)
    if m:
        try:
            start = datetime(year, int(m.group(1)), int(m.group(2)))
            end = datetime(year, int(m.group(3)), int(m.group(4)))
            if end < start: end = datetime(year + 1, int(m.group(3)), int(m.group(4)))
            return start, end
        except: pass
    # 単発
    m = re.search(r'(\d{1,2})[./月](\d{1,2})[日]?', text)
    if m:
        try:
            dt = datetime(year, int(m.group(1)), int(m.group(2)))
            return dt, dt
        except: pass
    return None, None

@st.cache_data(ttl=1800)
def fetch_more_events(selected_genres, custom_kw):
    all_events = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    # 検索キーワードを広げる
    keywords = []
    for g in selected_genres:
        keywords.extend(GENRES[g]["words"][:4])
    if custom_kw:
        keywords.extend([k.strip() for k in custom_kw.split(",")])

    for kw in list(set(keywords))[:20]: # 検索上限を拡大
        url = f"https://collabo-cafe.com/?s={kw}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            articles = soup.find_all('article')
            for art in articles[:8]: # 取得件数をアップ
                title_el = art.find('h2') or art.select_one('.entry-title')
                if not title_el: continue
                title = title_el.get_text().strip()
                link = art.find('a')['href']
                
                start, end = parse_dates_v3(title)
                loc = "1時間半以内"
                if any(x in title for x in ["宇都宮", "ベルモール"]): loc = "30分以内"
                elif any(x in title for x in ["大宮", "さいたま", "スーパーアリーナ"]): loc = "1時間以内"
                elif any(x in title for x in ["横浜", "幕張", "千葉", "Kアリーナ", "ぴあアリーナ", "富士急"]): loc = "2時間半以内"
                elif any(x in title for x in ["大阪", "名古屋", "USJ", "福岡"]): loc = "それ以上"

                if start:
                    emoji = "🔍"
                    color = "#94A3B8"
                    for g_name, info in GENRES.items():
                        if any(w in title or w in kw for w in info["words"]):
                            emoji, color = info["emoji"], info["color"]
                            break

                    all_events.append({
                        "id": f"{kw}-{title[:10]}", "emoji_title": f"{emoji} {kw}",
                        "full_title": title, "start": start, "end": end,
                        "genre": g_name if 'g_name' in locals() else "その他",
                        "time": loc, "url": link, "color": color
                    })
        except: pass
    return all_events

# --- メイン画面 ---
st.title("✨ 推しイベ")
st.write("栃木県小山駅発 🚃 スケジュール図鑑")

# --- 検索パネル（カレンダーの上に配置） ---
st.markdown('<div class="filter-container">', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    sel_gen = st.multiselect("🌈 ジャンル選択", list(GENRES.keys()), default=["VTuber", "ポケモン", "アイドル", "あんスタ"])
with c2:
    sel_time = st.multiselect("⏳ 小山からの時間", TIME_OPTIONS, default=["30分以内", "1時間以内", "1時間半以内", "2時間半以内"])

custom_input = st.text_input("🔍 自由検索ワード (例: 呪術廻戦, アイナナ)", help="カンマ区切りで入力")
st.markdown('</div>', unsafe_allow_html=True)

# データ取得
with st.spinner("最新の推し情報をスキャン中..."):
    data = fetch_more_events(sel_gen, custom_input)
    filtered = [e for e in data if e['time'] in sel_time]

# --- カレンダー表示 ---
st.subheader("📅 推しカレンダー")
cal_events = []
for e in filtered:
    cal_events.append({
        "id": e['id'], "title": e['emoji_title'], 
        "start": e['start'].strftime("%Y-%m-%d"), 
        "end": (e['end'] + timedelta(days=1)).strftime("%Y-%m-%d"),
        "backgroundColor": e['color'], "borderColor": "white",
        "extendedProps": {"full_title": e['full_title'], "url": e['url'], "time": e['time'], "gen": e['genre']}
    })

state = calendar(events=cal_events, options={"initialView": "dayGridMonth", "locale": "ja", "height": "auto"})

# 詳細表示
if state.get("eventClick"):
    p = state["eventClick"]["event"]["extendedProps"]
    st.markdown(f"""
        <div class="pop-card">
            <h3 style='color:#1E40AF; margin-top:0;'>✨ イベント詳細</h3>
            <b>{p['full_title']}</b><br><br>
            <span class="badge" style="background:{GENRES.get(p['gen'], {'color': '#94A3B8'})['color']}">{p['gen']}</span>
            <span class="badge" style="background:#3B82F6">📍 小山から{p['time']}</span><br><br>
            <small>🚃 経路目安: {get_access_info(p['time'])}</small><br><br>
            <a href="{p['url']}" target="_blank">
                <button style="width:100%; background:#3B82F6; color:white; border:none; padding:12px; border-radius:10px; cursor:pointer; font-weight:bold;">公式サイトへ GO!</button>
            </a>
        </div>
    """, unsafe_allow_html=True)

# 週間・全件リスト
st.subheader("📋 直近のリスト")
if not filtered:
    st.info("条件に合うイベントが現在見つかりませんでした。自由検索ワードに推しの名前を入れてみてください！")
else:
    for e in sorted(filtered, key=lambda x: x['start'])[:15]:
        date_str = f"{e['start'].strftime('%m/%d')} 〜 {e['end'].strftime('%m/%d')}"
        st.markdown(f"""
            <div style="background:white; border-radius:15px; padding:15px; margin-bottom:10px; border-left:8px solid {e['color']}; box-shadow:2px 2px 5px rgba(0,0,0,0.05);">
                <small>{date_str} | 小山から{e['time']}</small><br>
                <b>{e['full_title']}</b><br>
                <small style="color:#3B82F6;">🚃 {get_access_info(e['time'])}</small>
            </div>
        """, unsafe_allow_html=True)
