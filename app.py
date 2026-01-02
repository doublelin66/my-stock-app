import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta

# 1. 網頁基本設定
st.set_page_config(page_title="台股即時分析儀表板", layout="wide")

st.title("📈 台股個股技術分析 (Yahoo Finance)")

# 2. 側邊欄設定 (Sidebar)
st.sidebar.header("設定參數")

# 輸入股票代號 (預設台積電)
ticker_input = st.sidebar.text_input("輸入股票代號 (請加 .TW 或 .TWO)", value="2330.TW")

# 選擇時間範圍
start_date = st.sidebar.date_input("開始日期", datetime.now() - timedelta(days=180))
end_date = st.sidebar.date_input("結束日期", datetime.now())

st.sidebar.markdown("---")
st.sidebar.info("資料來源：Yahoo Finance (延遲報價)")

# 3. 抓取資料函數
def load_data(ticker, start, end):
    try:
        df = yf.download(ticker, start=start, end=end)
        return df
    except Exception as e:
        return None

# 執行按鈕
if st.button("開始分析") or ticker_input:
    # 下載資料
    data = load_data(ticker_input, start_date, end_date)

    if data is not None and not data.empty:
        # 資料預處理 (處理 MultiIndex 問題)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        # 計算移動平均線 (MA)
        data['MA5'] = data
