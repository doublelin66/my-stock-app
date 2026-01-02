# 抓取籌碼 (診斷模式：會顯示 API 錯誤原因)
def load_chip_data(stock_id, start, end):
    try:
        url = "https://api.finmindtrade.com/api/v4/data"
        parameter = {
            "dataset": "TaiwanStockInstitutionalInvestor",
            "data_id": stock_id,
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d")
        }
        
        r = requests.get(url, params=parameter)
        data = r.json()
        
        # --- 診斷區：印出 API 回傳狀態 ---
        if data.get("msg") != "success":
            st.error(f"FinMind API 回傳錯誤: {data.get('msg')}")
            return None
            
        if not data.get("data"):
            st.warning(f"FinMind 回傳成功但沒有資料 (stock_id: {stock_id})")
            return None
        # -----------------------------

        df = pd.DataFrame(data["data"])
        
        name_map = {
            'Foreign_Investor': '外資',
            'Investment_Trust': '投信',
            'Dealer_Self': '自營商(自行買賣)',
            'Dealer_Hedging': '自營商(避險)',
            'Dealer': '自營商'
        }
        df['name'] = df['name'].map(name_map).fillna(df['name'])
        df['date'] = pd.to_datetime(df['date'])
        df['net_buy'] = (df['buy'] - df['sell']) / 1000
        
        return df

    except Exception as e:
        st.error(f"連線發生異常: {e}")
        return None
