import os
from decimal import getcontext

# إعدادات الدقة المالية (إضافة 2)
getcontext().prec = 10

class Config:
    # جلب المفاتيح من Railway Variables
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
    BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
    
    # إعدادات السيرفر
    PORT = int(os.getenv('PORT', 5000))
    DEBUG = False
    
    # إعدادات الوضع (إضافة 14)
    DEFAULT_MODE = "DEMO" 
    
    # إعدادات الأمان (إضافة 55)
    DAILY_STOP_LOSS = 0.05  # 5%
    MAX_DRAWDOWN = 0.20     # 20% (إضافة 16)
