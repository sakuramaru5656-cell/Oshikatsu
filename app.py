import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import re

# ページ設定
st.set_page_config(page_title="推し活カレンダー(小山発)", layout="wide")

# --- 背景・スタイル ---
st.markdown("""
    <style>
    .stApp { background-color: #f0f2f5; }
    .event-card { 
        border-left: 5px solid; 
        padding: 15px; 
        margin-bottom: 15px; 
        background: white; 
        border-radius: 8px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🌟 推し事アクセスカレンダー")
st.caption("小山駅から、アイドル・アニメイベント会場までの時間を自動計算")

# --- サイドバー：検索ワード設定 ---
with st.sidebar:
    st.header("🔎 追っかけ対象")
    # 初期値にご要望の項目を追加
    default_keywords = "timelesz, Hey! Say! JUMP, King & Prince, ワンピース, NARUTO, ポケモン, ホロライブ, さくらみこ"
    keywords = st.text_area("検索ワード（カンマ区切り）", value=default_keywords, height=150)
    
    st.header("⏳ 移動時間で絞り込み")
    selected_times = st.multiselect(
        "小山駅からの所要時間",
        ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"],
        default=["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"]
    )
    st.divider()
    st.info("📍 起点：栃木県小山市 (小山駅)")

# --- データ取得・解析エンジン ---
@st.cache_data(ttl=1800)
def fetch_all_events(keywords_str):
    all_events = []
    kw_list = [k.strip() for k in keywords_str.split(",")]
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for kw in kw_list:
        # コラボカフェ系サイトからの検索
        url = f"https://collabo-cafe.com/?s={kw}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            for art in soup.select('article')[:12]:
                title = art.select_one('.entry-title').get_text().strip() if art.select_one('.entry-title') else ""
                link = art.find('a')['href'] if art.find('a') else ""
                if not title: continue

                # --- 開催場所・アクセスの高度な判定 ---
                loc_label = "都内"
                # 会場名や地名から小山駅ベースの時間を判定
                if any(x in title for x in ["宇都宮", "栃木", "ベルモール"]): 
                    loc_label = "宇都宮"
                elif any(x in title for x in ["大宮", "さいたまスーパーアリーナ", "レイクタウン", "浦和"]): 
                    loc_label = "大宮"
                elif any(x in title for x in ["池袋", "秋葉原", "新宿", "渋谷", "東京ドーム", "日本武道館", "代々木体育館", "スカイツリー", "日本橋", "有明", "ガーデンシアター"]): 
                    loc_label = "都内"
                elif any(x in title for x in ["横浜", "幕張", "ぴあアリーナ", "Kアリーナ", "日産スタジアム", "千葉"]): 
                    loc_label = "横浜・千葉"
                elif any(x in title for x in ["大阪", "名古屋", "福岡", "札幌", "ドーム", "富士急", "仙台"]): 
                    loc_label = "遠方"

                access_map = {
                    "宇都宮": (30, "30分以内", "#28a745", "JR宇都宮線 (約25分)"),
                    "大宮": (50, "1時間以内", "#007bff", "新幹線または快速 (約45分)"),
                    "都内": (85, "1時間半以内", "#f1c40f", "上野東京ライン (約80分)"),
                    "横浜・千葉": (135, "2時間半以内", "#e67e22", "湘南新宿ライン/京葉線 (約130分)"),
                    "遠方": (240, "それ以上", "#e74c3c", "新幹線・飛行機が必要"),
                }
                mins, label, color, way = access_map.get(loc_label, (90, "1時間半以内", "#f1c40f", "JR線"))
                
                # --- 日付抽出 ---
                date_found = None
                date_patterns = [r'(\d+)月(\d+)日', r'(\d+)/(\d+)']
                for pattern in date_patterns:
                    match = re.search(pattern, title)
                    if match:
                        month, day = int(match.group(1)), int(match.group(2))
                        try:
                            date_found = datetime(datetime.now().year, month, day)
                            if date_found < datetime.now() - timedelta(days=60): # 過去すぎるのは来年と判断
                                date_found = datetime(datetime.now().year + 1, month, day)
                        except: pass
                        break
                
                if not date_found:
                    date_found = datetime.now() + timedelta(days=len(all_events) % 20) # 分散表示用

                all_events.append({
                    "title": f"【{kw}】{title}",
                    "start": date_found.strftime("%Y-%m-%d"),
                    "color": color,
                    "url": link,
                    "cat": label,
                    "way": way,
                    "loc": loc_label,
                    "kw": kw
                })
        except: pass
            
    return all_events

# --- メインロジック ---
data = fetch_all_events(keywords)
filtered_data = [e for e in data if e['cat'] in selected_times]

# モード切替
mode = st.radio("表示切り替え", ["📅 カレンダー", "📋 直近の週間予定", "🔍 全件リスト"], horizontal=True)

if not filtered_data:
    st.warning("イベントが見つかりません。キーワードを調整してみてください。")
else:
    if mode == "📅 カレンダー":
        calendar_options = {
            "initialView": "dayGridMonth",
            "headerToolbar": {"left": "prev,next today", "center": "title", "right": ""},
            "locale": "ja"
        }
        calendar(events=filtered_data, options=calendar_options)
        st.info("💡 カレンダーの予定をクリックすると公式サイトへ飛びます")

    elif mode == "📋 直近の週間予定":
        today = datetime.now().date()
        week_end = today + timedelta(days=7)
        st.subheader(f"📅 {today} 〜 {week_end} の予定")
        
        week_events = [e for e in filtered_data if today <= datetime.strptime(e['start'], "%Y-%m-%d").date() <= week_end]
        
        if not week_events:
            st.write("この1週間の予定はありません。")
        else:
            for e in sorted(week_events, key=lambda x: x['start']):
                st.markdown(f"""
                <div class="event-card" style="border-color: {e['color']};">
                    <span style="color: {e['color']}; font-weight: bold;">{e['cat']}</span> | 🚃 {e['way']}<br>
                    <strong>{e['start']}</strong><br>
                    <a href="{e['url']}" target="_blank" style="text-decoration: none; color: #1f77b4; font-size: 1.1em;">{e['title']}</a>
                </div>
                """, unsafe_allow_html=True)

    else:
        # 全件表示
        for kw in keywords.split(","):
            kw = kw.strip()
            kw_events = [e for e in filtered_data if e['kw'] == kw]
            if kw_events:
                with st.expander(f"{kw} 関連 ({len(kw_events)}件)"):
                    for e in kw_events:
                        st.write(f"{e['start']} : [{e['title']}]({e['url']}) ({e['cat']})")

st.divider()
st.caption("※日付が不明なものは今日以降に割り振られています。正確な日程はリンク先をご確認ください。")
