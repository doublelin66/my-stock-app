import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import google.generativeai as genai
import twstock
from FinMind.data import DataLoader

# 1. 頁面設定
st.set_page_config(page_title="台股籌碼戰情室", layout="wide")
st.title("📈 台股個股智慧分析 + 籌碼追蹤")

# 2. 設定 Gemini API
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-pro')
        ai_available = True
    else:
        st.warning("尚未設定 GEMINI_API_KEY，AI 分析功能將無法使用。")
        ai_available = False
except Exception as e:
    ai_available = False

# 3. 側邊欄
st.sidebar.header("設定參數")
ticker_input = st.sidebar.text_input("輸入股票代號 (例如 2330)", value="2330")
start_date = st.sidebar.date_input("開始日期", datetime.now() - timedelta(days=180))
end_date = st.sidebar.date_input("結束日期", datetime.now())
st.sidebar.markdown("---")
st.sidebar.info("資料來源：Yahoo Finance / FinMind (證交所 Open Data)")

# 4. 函數區

def get_stock_name(code):
    try:
        if code in twstock.codes:
            return twstock.codes[code].name
        return code
    except:
        return code

# 抓取股價 (Yahoo)
def load_price_data(ticker, start, end):
    clean_ticker = ticker.replace(".TW", "").replace(".TWO", "")
    tickers_to_try = []
    if "." not in ticker:
        tickers_to_try = [f"{clean_ticker}.TW", f"{clean_ticker}.TWO"]
    else:
        tickers_to_try = [ticker]

    for t in tickers_to_try:
        try:
            df = yf.download(t, start=start, end=end)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.loc[:, ~df.columns.duplicated()]
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            
            if not df.empty:
                return df, t, clean_ticker
        except Exception:
            continue
    return None, None, clean_ticker

# 抓取籌碼 (FinMind 通用修復版)
def load_chip_data(stock_id, start, end):
    try:
        # FinMind 需要字串格式的日期 YYYY-MM-DD
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")
        
        dl = DataLoader()
        # --- 修改重點：改用 get_data 通用函數，避免版本錯誤 ---
        df = dl.get_data(
            dataset="TaiwanStockInstitutionalInvestor",
            data_id=stock_id,
            start_date=start_str,
            end_date=end_str
        )
        
        if df is not None and not df.empty:
            # 資料整理：將長表格轉為寬表格 (Pivoting)
            # 原始資料 name 欄位包含：Foreign_Investor(外資), Investment_Trust(投信), Dealer_Self(自營商)...
            
            # 簡化名稱對應
            name_map = {
                'Foreign_Investor': '外資',
                'Investment_Trust': '投信',
                'Dealer_Self': '自營商(自行買賣)',
                'Dealer_Hedging': '自營商(避險)',
                'Dealer': '自營商'
            }
            df['name'] = df['name'].map(name_map).fillna(df['name'])
            
            # 轉換日期格式
            df['date'] = pd.to_datetime(df['date'])
            
            # 取出買賣超股數 (buy - sell) -> 轉成「張數」 (除以 1000)
            df['net_buy'] = (df['buy'] - df['sell']) / 1000
            
            return df
        return None
    except Exception as e:
        st.error(f"籌碼資料抓取失敗: {e}")
        return None
        
def get_ai_analysis(ticker_code, stock_name, chip_df=None):
    if not ai_available:
        return "AI 功能未啟用。"
    
    # 計算最近籌碼概況給 AI
    chip_summary = ""
    if chip_df is not None:
        last_date = chip_df['date'].max()
        recent = chip_df[chip_df['date'] == last_date]
        total_buy = recent['net_buy'].sum()
        chip_summary = f"最新籌碼({last_date.date()})：三大法人合計買賣超 {total_buy:.0f} 張。"

    prompt = f"""
    請分析台股 {ticker_code} ({stock_name})。
    {chip_summary}
    請用繁體中文，條列回答：
    1. **產業與題材**：公司簡介與近期熱門話題(如AI, CoWoS等)。
    2. **籌碼面解讀**：根據三大法人近期動向給予簡評。
    3. **操作建議**：簡單的技術面支撐壓力觀察。
    300字以內。
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 分析失敗: {e}"

# 5. 主程式邏輯
if ticker_input:
    # A. 抓股價
    price_df, valid_ticker, clean_code = load_price_data(ticker_input, start_date, end_date)
    
    # B. 抓籌碼
    chip_df = load_chip_data(clean_code, start_date, end_date)

    if price_df is not None and not price_df.empty:
        stock_name = get_stock_name(clean_code)
        display_name = f"{clean_code} {stock_name}"
        st.header(f"📊 {display_name} 戰情室")

        # 分頁設定
        tab1, tab2, tab3 = st.tabs(["📈 技術分析", "🏛️ 三大法人籌碼追蹤", "🔎 券商分點/主力"])

        # === TAB 1: 技術走勢 ===
        with tab1:
            if st.button(f"🤖 AI 分析 {stock_name} (含籌碼解讀)"):
                with st.spinner("AI 正在分析技術與籌碼數據..."):
                    analysis = get_ai_analysis(clean_code, stock_name, chip_df)
                    st.markdown(analysis)
                    st.markdown("---")

            # 畫 K 線圖
            price_df['MA5'] = price_df['Close'].rolling(5).mean()
            price_df['MA20'] = price_df['Close'].rolling(20).mean()
            
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_width=[0.2, 0.7], 
                                subplot_titles=('股價走勢', '成交量'))
            fig.add_trace(go.Candlestick(x=price_df.index, open=price_df['Open'], high=price_df['High'],
                                         low=price_df['Low'], close=price_df['Close'], name="K線"), row=1, col=1)
            fig.add_trace(go.Scatter(x=price_df.index, y=price_df['MA5'], line=dict(color='orange', width=1), name='MA5'), row=1, col=1)
            fig.add_trace(go.Scatter(x=price_df.index, y=price_df['MA20'], line=dict(color='green', width=1), name='MA20'), row=1, col=1)
            fig.add_trace(go.Bar(x=price_df.index, y=price_df['Volume'], name="成交量"), row=2, col=1)
            fig.update_layout(xaxis_rangeslider_visible=False, height=600, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

        # === TAB 2: 三大法人籌碼追蹤 (還原網站功能) ===
        with tab2:
            st.subheader("三大法人累計買賣超趨勢")
            if chip_df is not None:
                # 整理數據：樞紐分析表 (Pivot)
                pivot_df = chip_df.pivot_table(index='date', columns='name', values='net_buy', aggfunc='sum').fillna(0)
                
                # 計算「累計」買賣超 (Cumulative Sum) -> 這才是畫趨勢圖的關鍵
                cum_pivot = pivot_df.cumsum()
                
                # 畫圖
                fig_chip = go.Figure()
                
                # 外資 (紅色)
                if '外資' in cum_pivot.columns:
                    fig_chip.add_trace(go.Scatter(x=cum_pivot.index, y=cum_pivot['外資'], mode='lines', name='外資', line=dict(color='#FF4136')))
                
                # 投信 (黃色/橘色)
                if '投信' in cum_pivot.columns:
                    fig_chip.add_trace(go.Scatter(x=cum_pivot.index, y=cum_pivot['投信'], mode='lines', name='投信', line=dict(color='#FFDC00')))
                    
                # 自營商 (合併所有自營商欄位)
                dealers = [c for c in cum_pivot.columns if '自營商' in c]
                if dealers:
                    cum_pivot['自營商合計'] = cum_pivot[dealers].sum(axis=1)
                    fig_chip.add_trace(go.Scatter(x=cum_pivot.index, y=cum_pivot['自營商合計'], mode='lines', name='自營商', line=dict(color='#2ECC40')))

                fig_chip.update_layout(
                    title=f"{stock_name} 三大法人累計買賣超 (張)",
                    xaxis_title="日期",
                    yaxis_title="累計張數",
                    template="plotly_dark",
                    hovermode="x unified"
                )
                st.plotly_chart(fig_chip, use_container_width=True)
                
                # 顯示原始數據表格
                with st.expander("查看每日買賣超詳細數據"):
                    st.dataframe(pivot_df.sort_index(ascending=False))
            else:
                st.warning("查無籌碼資料 (可能是 ETF 或資料源更新延遲)")

        # === TAB 3: 券商分點/主力 (替代方案) ===
        with tab3:
            st.subheader("券商分點主力進出追蹤")
            st.info("ℹ️ 說明：官方 Open API 僅提供「三大法人」數據，不公開「各別券商分點」(如：凱基台北) 的明細。以下為您整理外部專業網站連結，可直接查詢主力分點。")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"#### 🔗 [Yahoo 股市 - 主力進出](https://tw.stock.yahoo.com/quote/{clean_code}/broker-trading)")
                st.caption("適合查詢當日買賣超前幾名的券商")
            with col2:
                st.markdown(f"#### 🔗 [旺得富 - 分點籌碼](https://wantgoo.com/stock/{clean_code}/major-investors)")
                st.caption("圖表化顯示主力大戶的持股變化")
            
            st.markdown("---")
            st.markdown("### 📊 模擬主力動向 (法人合計)")
            # 畫一個「三大法人合計」的圖來模擬主力
            if chip_df is not None:
                pivot_df = chip_df.pivot_table(index='date', columns='name', values='net_buy', aggfunc='sum').fillna(0)
                pivot_df['合計'] = pivot_df.sum(axis=1)
                pivot_df['累計合計'] = pivot_df['合計'].cumsum()
                
                fig_total = go.Figure()
                fig_total.add_trace(go.Scatter(x=pivot_df.index, y=pivot_df['累計合計'], 
                                             fill='tozeroy', mode='lines', name='法人合計買賣超', line=dict(color='#B10DC9')))
                fig_total.update_layout(title="法人(疑似主力) 累計買賣超動向", template="plotly_dark")
                st.plotly_chart(fig_total, use_container_width=True)

    else:
        st.error(f"找不到代號 {ticker_input}，請確認輸入是否正確。")
