import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time
import re
import urllib.parse
import imageio.v3 as iio
import shutil
import sys
from collections import deque
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- CONFIGURATION ---
OUTPUT_FILE = "leads_database.csv"
VIDEO_FILE = "mission_recording.mp4"
TEMP_IMG_FOLDER = "temp_frames"

# --- PAGE SETUP ---
st.set_page_config(page_title="NotNahid Intel", page_icon="🕵️", layout="wide")

# --- CUSTOM CSS (THE "PRO" LOOK) ---
st.markdown("""
<style>
    /* Main Background */
    .stApp { background-color: #0E1117; }
    
    /* Metrics Styling */
    [data-testid="stMetricValue"] {
        font-size: 36px;
        color: #00FF99;
        font-family: 'Courier New', monospace;
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] {
        color: #aaaaaa;
        font-size: 14px;
    }
    
    /* Button Styling */
    div.stButton > button {
        background: linear-gradient(45deg, #00FF99, #00CC7A);
        color: black;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 1px;
        width: 100%;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 0 15px rgba(0, 255, 153, 0.4);
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    
    /* Progress Bar */
    .stProgress > div > div > div > div {
        background-color: #00FF99;
    }
</style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS (Same logic, cleaner code) ---
def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled") 
    options.add_argument("--window-size=1280,720") 
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def make_video():
    images = []
    if not os.path.exists(TEMP_IMG_FOLDER): return False
    files = sorted(os.listdir(TEMP_IMG_FOLDER), key=lambda x: int(x.split('_')[1].split('.')[0]))
    for filename in files:
        if filename.endswith(".png"):
            images.append(iio.imread(os.path.join(TEMP_IMG_FOLDER, filename)))
    if images:
        iio.imwrite(VIDEO_FILE, images, fps=2, codec="libx264")
        return True
    return False

def run_spider_gui(keyword, max_leads_limit, record_screen):
    # UI Layout for Live Feed
    col1, col2 = st.columns([1, 2])
    with col1:
        status_text = st.empty()
        progress_bar = st.progress(0)
        log_box = st.empty()
    with col2:
        cctv_display = st.empty()

    if record_screen:
        if os.path.exists(TEMP_IMG_FOLDER): shutil.rmtree(TEMP_IMG_FOLDER)
        os.makedirs(TEMP_IMG_FOLDER)
    
    driver = setup_driver()
    leads_data = []
    visit_queue = deque()
    visited_urls = set()
    frame_count = 0
    
    # HARVEST PHASE
    status_text.markdown("### 📡 Phase 1: Scanning Network...")
    driver.get(f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(keyword)}")
    
    results = driver.find_elements(By.CLASS_NAME, "result__a")
    for res in results:
        try:
            link = res.get_attribute("href")
            if "duckduckgo.com/l/" in link:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
                link = qs.get('uddg', [link])[0]
            if link and link not in visited_urls:
                visit_queue.append((link, 1, res.text))
                visited_urls.add(link)
        except: pass
    
    # DEEP SCAN PHASE
    status_text.markdown(f"### 🕷️ Phase 2: Infiltrating {len(visit_queue)} Targets...")
    total_targets = len(visit_queue)
    processed = 0
    
    while visit_queue and len(leads_data) < max_leads_limit:
        url, depth, title = visit_queue.popleft()
        processed += 1
        
        # Update UI
        progress_val = min(int((processed / (total_targets + 10)) * 100), 90)
        progress_bar.progress(progress_val)
        log_box.code(f"VISITING: {url[:50]}...", language="bash")
        
        try:
            driver.set_page_load_timeout(10)
            driver.get(url)
            time.sleep(1)
            
            if record_screen:
                path = f"{TEMP_IMG_FOLDER}/frame_{frame_count}.png"
                driver.save_screenshot(path)
                cctv_display.image(path, caption=f"LIVE FEED: {title[:30]}", use_container_width=True)
                frame_count += 1
            
            # Extraction Logic (Simplified for brevity)
            text = driver.find_element(By.TAG_NAME, "body").text
            page_source = driver.page_source
            
            emails = list(set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)))
            emails = [e for e in emails if not any(x in e for x in ['.png', '.jpg', 'wix', 'example'])]
            phones = list(set(re.findall(r'(?:\+88|88)?(01[3-9]\d{8})', text.replace('-', '').replace(' ', ''))))
            whatsapps = list(set(re.findall(r'wa\.me/(\d+)', page_source)))
            
            if emails or phones or whatsapps:
                leads_data.append({
                    "Company": title, "Website": url,
                    "Emails": ", ".join(emails), "Phones": ", ".join(phones),
                    "WhatsApp": ", ".join(whatsapps), "Status": "Verified"
                })
                st.toast(f"🎯 Hit: {title[:20]}", icon="✅")
                
        except: pass

    driver.quit()
    progress_bar.progress(100)
    
    if record_screen and frame_count > 0:
        status_text.markdown("### 💾 Saving Mission Data...")
        make_video()
        
    return pd.DataFrame(leads_data)

# --- SIDEBAR ---
with st.sidebar:
    st.title("🕵️‍♂️ NotNahid Intel")
    st.markdown("---")
    keyword = st.text_input("🎯 Target Keyword", "Software Companies in Dhaka")
    limit = st.slider("📊 Max Leads", 5, 200, 50)
    cctv = st.toggle("🎥 CCTV Mode", value=True)
    st.markdown("---")
    
    if st.button("🚀 INITIATE SCAN"):
        if not keyword:
            st.error("KEYWORD REQUIRED")
        else:
            with st.spinner("Initializing Cyber-Spider..."):
                df = run_spider_gui(keyword, limit, cctv)
                if not df.empty:
                    df.to_csv(OUTPUT_FILE, index=False)
                    st.success("SCAN COMPLETE")
                    time.sleep(1)
                    st.rerun()

# --- MAIN DASHBOARD ---
if os.path.exists(OUTPUT_FILE):
    df = pd.read_csv(OUTPUT_FILE)
else:
    df = pd.DataFrame()

# Header
col1, col2 = st.columns([3, 1])
with col1:
    st.title("COMMAND CENTER")
    st.caption("Real-Time Lead Intelligence System")
with col2:
    if not df.empty:
        st.metric("Total Intel", f"{len(df)} Leads", delta=f"+{len(df)} Today")

# Tabs
tab1, tab2, tab3 = st.tabs(["📊 DATABASE", "📈 ANALYTICS", "🎥 REPLAY"])

with tab1:
    if not df.empty:
        st.dataframe(
            df, 
            column_config={
                "Website": st.column_config.LinkColumn("Website"),
                "Emails": st.column_config.TextColumn("Emails", width="medium"),
                "Status": st.column_config.Column("Verified", width="small")
            },
            use_container_width=True,
            height=600
        )
        # CSV Download
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ DOWNLOAD FULL REPORT", csv, "intel_report.csv", "text/csv")
    else:
        st.info("Awaiting Mission Data. Launch a scan from the sidebar.")

with tab2:
    if not df.empty:
        c1, c2 = st.columns(2)
        with c1:
            # Clean data for charts
            has_email = df['Emails'].notna().sum()
            has_wa = df['WhatsApp'].notna().sum()
            has_phone = df['Phones'].notna().sum()
            
            fig = px.pie(
                names=["Emails", "WhatsApp", "Phone"],
                values=[has_email, has_wa, has_phone],
                title="Contact Method Distribution",
                hole=0.5,
                template="plotly_dark",
                color_discrete_sequence=["#00FF99", "#00CC7A", "#008855"]
            )
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown("### 💡 Strategic Insights")
            st.success(f"**{int((has_wa/len(df))*100)}%** of targets have WhatsApp.")
            st.info(f"**{int((has_email/len(df))*100)}%** of targets have Email.")

with tab3:
    if os.path.exists(VIDEO_FILE):
        st.video(VIDEO_FILE)
    else:
        st.warning("No mission footage available.")
