import sqlite3
from datetime import datetime

class FactoryDatabase:
    def __init__(self):
        self.db_path = "factory_memory.db"
        self._create_tables()

    def _create_tables(self):
        with sqlite3.connect(self.db_path) as conn:
            # جدول ذاكرة القرارات (لماذا دخلنا؟ وماذا حدث؟)
            conn.execute('''CREATE TABLE IF NOT EXISTS ai_memory 
                            (id INTEGER PRIMARY KEY, timestamp TEXT, reason TEXT, 
                             outcome TEXT, confidence REAL)''')
            # جدول سجل الصفقات التاريخي
            conn.execute('''CREATE TABLE IF NOT EXISTS trade_history 
                            (id INTEGER PRIMARY KEY, symbol TEXT, side TEXT, 
                             pnl REAL, timestamp TEXT)''')

    def save_decision(self, reason, confidence):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO ai_memory (timestamp, reason, confidence) VALUES (?, ?, ?)",
                         (datetime.now().isoformat(), reason, confidence))
