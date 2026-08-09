import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import re

# --- ページ設定とモダンUI用のCSS ---
st.set_page_config(page_title="HoloPoke Access", page_icon="🌸", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #F8FAFC; }
    
    /* カードのデザイン */
    .event-card {
        background: white; border-radius: 16px; padding: 20px;
        margin-bottom: 16px; border: 1px solid #F1F5F9;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* バッジ */
    .badge {
        display: inline-block; padding: 4px 12px; border-radius: 9999px;
        font-size: 12px; font-weight: 600; margin-right: 8px; margin-bottom: 8px;
    }
    .time-30 { background-color: #DCFCE7; color: #166534; }
    .time-60 { background-color: #DBEAFE; color: #1E40AF; }
    .time-90 { background-color: #FEF9C3; color: #854D0E; }
    .time-150 { background-color: #FFEDD5; color: #9A3412; }
    .time-far { background-color: #FEE2E2; color: #991B1B; }
    
    .event-title {
        font-size: 18px; font-weight: 600; color: #1E293B;
        text-decoration: none; margin-top: 8px; display: block;
    }
    .event-title:hover { color: #3B82F6; }
    .info-text { color: #64748B; font-size: 14px; margin-top: 4px; }
    </style>
    """, unsafe_allow_html=True)

# --- カテゴリー定義 ---
CATEGORIES = {
    "VTuber (ホロライブ)": ["ホロライブ", "さくらみこ", "星街すいせい"],
    "ポケモン": ["ポケモンセンター", "ポケモン", "ピカチュウ"],
    "ジャニーズ系": ["timelesz", "Hey! Say! JUMP", "King & Prince"],
    "ジャンプ系": ["ワンピース", "NARUTO", "呪術廻戦"],
    "その他": ["コラボカフェ", "アニメ展示"]
}

# --- 高度な日付抽出関数 ---
def extract_dates(text):
    """タイトルや抜粋文から日付(開始・終了)を探す"""
    year = datetime.now().year
    # 期間形式: 8/10〜9/1, 8.10-9.1, 8月10日〜
    range_match = re.search(r'(\d{1,2})[./月](\d{1,2}).*?[〜~ー\-](\d{1,2})[./月](\d{1,2})', text)
    if range_match:
        m1, d1, m2, d2 = map(int, range_match.groups())
        return datetime(year, m1, d1), datetime(year, m2, d2)
    
    # 単発形式: 8/10
    single_match = re.search(r'(\d{1,2})[./月](\d{1,2})', text)
    if single_match:
        m, d = map(int, single_match.groups())
        dt = datetime(year, m, d)
        return dt, dt
    
    return None, None

# --- データ取得ロジック ---
@st.cache_data(ttl=3600)
def fetch_events(selected_cats, custom_kw):
    search_keywords = []
    for cat in selected_cats: search_keywords.extend(CATEGORIES[cat])
    if custom_kw: search_keywords.append(custom_kw)
    
    all_events = []
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for kw in list(set(search_keywords))[:12]:
        url = f"https://collabo-cafe.com/?s={kw}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            for art in soup.select('article')[:8]:
                title = art.select_one('.entry-title').get_text().strip()
                excerpt = art.select_one('.entry-content').get_text().strip() if art.select_one('.entry-content') else ""
                link = art.find('a')['href']
                
                # エリア判定
                loc_label = "都内"
                if any(x in title for x in ["宇都宮", "ベルモール"]): loc_label = "宇都宮"
                elif any(x in title for x in ["大宮", "さいたま"]): loc_label = "大宮"
                elif any(x in title for x in ["横浜", "幕張", "千葉", "Kアリーナ"]): loc_label = "横浜・千葉"
                elif any(x in title for x in ["大阪", "名古屋", "福岡", "ドーム"]): loc_label = "遠方"

                access_map = {
                    "宇都宮": ("time-30", "30分以内", "JR宇都宮線"),
                    "大宮": ("time-60", "1時間以内", "宇都宮線 快速"),
                    "都内": ("time-90", "1時間半以内", "上野東京ライン"),
                    "横浜・千葉": ("time-150", "2時間半以内", "湘南新宿ライン"),
                    "遠方": ("time-far", "それ以上", "新幹線・特急"),
                }
                css_class, label, way = access_map.get(loc_label)

                # 日付抽出（タイトルと抜粋の両方から探す）
                start_dt, end_dt = extract_dates(title + excerpt)
                has_date = start_dt is not None

                all_events.append({
                    "title": title,
                    "start": start_dt.strftime("%Y-%m-%d") if has_date else None,
                    "end": end_dt.strftime("%Y-%m-%d") if has_date else None,
                    "has_date": has_date,
                    "css": css_class, "label": label, "way": way, "url": link, "kw": kw
                })
        except: pass
    return all_events

# --- メイン画面 ---
st.title("🌸 HoloPoke Access")
st.markdown(f"<p style='color: #64748B;'>小山駅から推しのイベントへ。リンクは新しいタブで開きます。</p>", unsafe_allow_html=True)

with st.sidebar:
    st.subheader("絞り込み")
    selected_cats = [cat for cat in CATEGORIES.keys() if st.checkbox(cat, value=True)]
    selected_times = st.multiselect("所要時間", ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"], default=["30分以内", "1時間以内", "1時間半以内"])
    custom_kw = st.text_input("追加検索")

data = fetch_events(selected_cats, custom_kw)
filtered_data = [e for e in data if e['label'] in selected_times]

tab1, tab2, tab3 = st.tabs(["📅 カレンダー", "📋 直近の週間予定", "🔍 全リスト(日付未定含む)"])

with tab1:
    # 日付があるものだけ表示
    cal_events = []
    for e in [x for x in filtered_data if x['has_date']]:
        color = "#22C55E" if "30分" in e['label'] else "#3B82F6" if "1時間" in e['label'] else "#EAB308" if "1時間半" in e['label'] else "#EF4444"
        cal_events.append({"title": e['title'], "start": e['start'], "end": e['end'], "color": color, "url": e['url']})
    
    if not cal_events:
        st.info("カレンダーに表示できる日付確定イベントがありません。")
    else:
        calendar(events=cal_events, options={"initialView": "dayGridMonth", "locale": "ja"})
        st.caption("※カレンダー内のリンクはシステムの制限で同じタブで開く場合があります。リスト形式の使用をおすすめします。")

with tab2:
    today = datetime.now().date()
    week_events = [e for e in filtered_data if e['has_date'] and today <= datetime.strptime(e['start'], "%Y-%m-%d").date() <= today + timedelta(days=7)]
    if not week_events:
        st.write("今後7日間の予定はありません")
    else:
        for e in sorted(week_events, key=lambda x: x['start']):
            st.markdown(f"""
            <div class="event-card">
                <span class="badge {e['css']}">{e['label']}</span>
                <span class="badge" style="background:#F1F5F9; color:#475569;">{e['kw']}</span>
                <a href="{e['url']}" target="_blank" class="event-title">{e['title']}</a>
                <div class="info-text">📅 {e['start']} | 🚃 {e['way']} (小山駅発)</div>
            </div>
            """, unsafe_allow_html=True)

with tab3:
    for e in sorted(filtered_data, key=lambda x: (not x['has_date'], x['start'] or "")):
        date_display = e['start'] if e['has_date'] else "日付未定（詳細確認）"
        st.markdown(f"""
        <div class="event-card">
            <span class="badge {e['css']}">{e['label']}</span>
            <a href="{e['url']}" target="_blank" class="event-title">{e['title']}</a>
            <div class="info-text">📅 {date_display}</div>
        </div>
        """, unsafe_allow_html=True)
