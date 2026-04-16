from config import Config

class RiskEngine:
    def __init__(self):
        self.current_drawdown = 0.0
        self.survival_mode = False # إضافة 27: وضع النجاة

    def validate_trade(self, signal_confidence, market_regime):
        # إضافة 24: مخاطرة ديناميكية حسب حالة السوق
        if market_regime == "CRASH":
            self.survival_mode = True
            return False
            
        if signal_confidence < 0.75: # إضافة 41: فلترة الإشارات ضعيفة الثقة
            return False
            
        return True

    def update_drawdown(self, equity, balance):
        # إضافة 16: حساب التراجع اللحظي
        self.current_drawdown = (balance - equity) / balance
        if self.current_drawdown > Config.MAX_DRAWDOWN:
            return "KILL_SWITCH" # إضافة 17: مفتاح القطع الفوري
        return "SAFE"
