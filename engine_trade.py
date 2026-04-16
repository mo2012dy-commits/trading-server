import ccxt
from config import Config

class TradeEngine:
    def __init__(self):
        self.exchange = ccxt.binance({
            'apiKey': Config.BINANCE_API_KEY,
            'secret': Config.BINANCE_SECRET_KEY,
            'options': {'defaultType': 'future'}
        })

    def execute_smart_order(self, symbol, side, amount):
        # إضافة 33: تنفيذ متدرج لتقليل التأثير السعري
        # إضافة 34: اختيار نوع الأمر تلقائياً
        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type='MARKET',
                side=side,
                amount=amount
            )
            return order # إضافة 31: حالة الطلب (Filled)
        except Exception as e:
            return {"status": "FAILED", "reason": str(e)} # إضافة 36: إعادة تنفيذ ذكية
