import pandas as pd
import pandas_ta as ta
from loguru import logger

class DataEngine:
    def __init__(self):
        self.tick_history = [] # إضافة 11: تسجيل كل حركة سعر

    def process_order_book(self, depth):
        # إضافة 9: تحليل أماكن السيولة وجدران الأوامر
        bids = depth['bids']
        asks = depth['asks']
        liquidity_gap = float(asks[0][0]) - float(bids[0][0])
        return liquidity_gap

    def generate_features(self, df):
        # إضافة 26: استخراج الخصائص الفنية
        df['RSI'] = ta.rsi(df['close'], length=14)
        df['EMA_20'] = ta.ema(df['close'], length=20)
        return df.dropna()

    def check_data_quality(self, df):
        # إضافة 12: اكتشاف البيانات الناقصة أو المشبوهة
        if df.isnull().values.any():
            logger.warning("Data Leakage or Missing Values Detected!")
            return False
        return True
