import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, ScrollView, SafeAreaView, ActivityIndicator, Alert, StatusBar } from 'react-native';

export default function App() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState({
    real_equity: '0.00',
    market_price: 0,
    market_rsi: 0,
    paper_trades_count: 0,
    total_paper_pnl: 0
  });

  // رابط سيرفرك في Railway (تأكد إنه نفس الرابط حقك)
  const API_URL = 'https://trading-server-production-bb80.up.railway.app';

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/`);
      const json = await response.json();
      if (json.status === 'online') {
        setData(json);
      }
    } catch (error) {
      console.error("خطأ في جلب البيانات:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleTrade = async (side: 'buy' | 'sell') => {
    try {
      const response = await fetch(`${API_URL}/trade`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ side: side, symbol: 'BTC/USDT', amount: 0.001 })
      });
      const res = await response.json();
      if (res.status === 'success') {
        Alert.alert("نجاح", `تم فتح صفقة وهمية (${side === 'buy' ? 'Long' : 'Short'})`);
        fetchData();
      }
    } catch (error) {
      Alert.alert("خطأ", "فشل في إرسال الأمر");
    }
  };

  const handleKillSwitch = async () => {
    try {
      const response = await fetch(`${API_URL}/kill`, { method: 'POST' });
      const res = await response.json();
      if (res.status === 'success') {
        Alert.alert("Kill Switch", `تم إغلاق ${res.closed_paper_trades} صفقة وهمية`);
        fetchData();
      }
    } catch (error) {
      Alert.alert("خطأ", "فشل في تنفيذ أمر الإغلاق");
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // تحديث تلقائي كل 30 ثانية
    return () => clearInterval(interval);
  }, []);

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />
      <ScrollView contentContainerStyle={styles.scrollContent}>
        
        <Text style={styles.headerTitle}>مصنع $ - غرفة العمليات</Text>
        
        {/* حالة السوق المباشرة */}
        <View style={styles.marketBar}>
          <Text style={styles.marketText}>BTC/USDT: ${data.market_price}</Text>
          <Text style={[styles.rsiText, { color: data.market_rsi > 70 ? '#ff4444' : data.market_rsi < 30 ? '#00ff00' : '#f0b90b' }]}>
            RSI: {data.market_rsi}
          </Text>
        </View>

        {/* كرت الرصيد الحقيقي (للمراقبة) */}
        <View style={styles.walletCard}>
          <Text style={styles.label}>الرصيد الحقيقي (بينانس)</Text>
          <Text style={styles.equityValue}>${parseFloat(data.real_equity).toFixed(2)}</Text>
        </View>

        {/* ملخص التداول الوهمي */}
        <View style={styles.paperCard}>
          <Text style={styles.label}>نتائج التداول الوهمي (Paper Trading)</Text>
          <View style={styles.row}>
            <View>
              <Text style={styles.subLabel}>الصفقات النشطة</Text>
              <Text style={styles.subValue}>{data.paper_trades_count}</Text>
            </View>
            <View>
              <Text style={styles.subLabel}>PNL الوهمي</Text>
              <Text style={[styles.subValue, { color: data.total_paper_pnl >= 0 ? '#00ff00' : '#ff4444' }]}>
                ${data.total_paper_pnl}
              </Text>
            </View>
          </View>
        </View>

        {/* أزرار التحكم السريع */}
        <View style={styles.row}>
          <TouchableOpacity style={[styles.tradeBtn, { backgroundColor: '#00ff00' }]} onPress={() => handleTrade('buy')}>
            <Text style={styles.btnText}>شراء (Long)</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.tradeBtn, { backgroundColor: '#ff4444' }]} onPress={() => handleTrade('sell')}>
            <Text style={styles.btnText}>بيع (Short)</Text>
          </TouchableOpacity>
        </View>

        <TouchableOpacity style={styles.refreshButton} onPress={fetchData}>
          {loading ? <ActivityIndicator color="#000" /> : <Text style={styles.btnTextDark}>تحديث البيانات</Text>}
        </TouchableOpacity>

        <TouchableOpacity style={styles.killSwitch} onPress={handleKillSwitch}>
          <Text style={styles.btnText}>Kill Switch (إغلاق الكل)</Text>
        </TouchableOpacity>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0b0e11' },
  scrollContent: { padding: 20 },
  headerTitle: { fontSize: 22, fontWeight: 'bold', color: '#fff', textAlign: 'center', marginBottom: 20 },
  marketBar: { flexDirection: 'row', justifyContent: 'space-between', backgroundColor: '#1e2329', padding: 15, borderRadius: 12, marginBottom: 15 },
  marketText: { color: '#fff', fontWeight: 'bold' },
  rsiText: { fontWeight: 'bold' },
  walletCard: { backgroundColor: '#1e2329', padding: 20, borderRadius: 15, marginBottom: 15, borderLeftWidth: 5, borderLeftColor: '#f0b90b' },
  paperCard: { backgroundColor: '#1e2329', padding: 20, borderRadius: 15, marginBottom: 20, borderLeftWidth: 5, borderLeftColor: '#00ff00' },
  label: { color: '#848e9c', fontSize: 12, marginBottom: 5 },
  equityValue: { color: '#fff', fontSize: 28, fontWeight: 'bold' },
  row: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 15 },
  subLabel: { color: '#848e9c', fontSize: 11 },
  subValue: { color: '#fff', fontSize: 18, fontWeight: 'bold' },
  tradeBtn: { flex: 0.48, padding: 18, borderRadius: 12, alignItems: 'center' },
  btnText: { color: '#fff', fontWeight: 'bold' },
  btnTextDark: { color: '#000', fontWeight: 'bold' },
  refreshButton: { backgroundColor: '#f0b90b', padding: 18, borderRadius: 12, alignItems: 'center', marginBottom: 12 },
  killSwitch: { backgroundColor: '#ff4444', padding: 18, borderRadius: 12, alignItems: 'center' },
});
