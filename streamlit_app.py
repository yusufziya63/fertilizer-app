import streamlit as st
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, PULP_CBC_CMD

# ============ DÖNEM VERİSİ ============
periods = {
    "14 Gün": [130, 50, 180, 80, 30, 50],
    "28 Gün": [110, 40, 200, 100, 35, 55],
    "56 Gün": [90, 30, 230, 130, 40, 60],
    "98 Gün": [70, 20, 250, 160, 45, 65]
}

# ============ GÜBRE BİLESİMİ ============
ferts = {
    "Urea": {"N": 0.46, "P": 0, "K": 0, "Ca": 0, "Mg": 0, "S": 0},
    "MAP": {"N": 0.11, "P": 0.52, "K": 0, "Ca": 0, "Mg": 0, "S": 0},
    "MKP": {"N": 0, "P": 0.52, "K": 0.34, "Ca": 0, "Mg": 0, "S": 0},
    "KNO3": {"N": 0.13, "P": 0, "K": 0.46, "Ca": 0, "Mg": 0, "S": 0},
    "CaNO3": {"N": 0.15, "P": 0, "K": 0, "Ca": 0.19, "Mg": 0, "S": 0},
    "MgSO4": {"N": 0, "P": 0, "K": 0, "Ca": 0, "Mg": 0.098, "S": 0.13},
    "K2SO4": {"N": 0, "P": 0, "K": 0.50, "Ca": 0, "Mg": 0, "S": 0.18}
}

st.set_page_config(page_title="🌾 Gübre Optimizasyonu", layout="wide")
st.title("🌾 Gübre Karışımı Optimizasyonu")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📋 Hedef Seçimi")
    selected_period = st.radio("Dönem Seç:", list(periods.keys()), horizontal=True)
    target_values = periods[selected_period]
    st.info(f"✅ Seçili Dönem: **{selected_period}**")

with col2:
    st.subheader("💰 Gübre Fiyatları")
    prices = {}
    for fert_name in ferts.keys():
        prices[fert_name] = st.number_input(f"{fert_name} Fiyatı (₺/kg):", value=5.0, min_value=0.0, step=0.1, key=f"price_{fert_name}")

st.markdown("---")

if st.button("🚀 OPTİMİZE ET", use_container_width=True, type="primary"):
    try:
        N, P, K, Ca, Mg, S = target_values
        
        model = LpProblem("Gubre_Optimizasyonu", LpMinimize)
        x = {f: LpVariable(f, 0) for f in ferts}
        
        model += lpSum(prices[f] * x[f] for f in ferts)
        model += lpSum(ferts[f]["N"] * x[f] for f in ferts) == N
        model += lpSum(ferts[f]["P"] * x[f] for f in ferts) == P
        model += lpSum(ferts[f]["K"] * x[f] for f in ferts) == K
        model += lpSum(ferts[f]["Ca"] * x[f] for f in ferts) == Ca
        model += lpSum(ferts[f]["Mg"] * x[f] for f in ferts) == Mg
        model += lpSum(ferts[f]["S"] * x[f] for f in ferts) == S
        
        model.solve(PULP_CBC_CMD(msg=0))
        
        st.subheader("✅ SONUÇLAR")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📦 Gübre Miktarları")
            total_amount = 0
            for f in ferts:
                amount = x[f].varValue or 0
                if amount > 0.01:
                    st.success(f"**{f}**: {round(amount, 3)} kg/m²")
                    total_amount += amount
        
        with col2:
            st.markdown("### 💡 Hesaplanan Değerler")
            ec = total_amount / 1000 * 1.2
            st.metric("EC (dS/m)", round(ec, 2))
            
            acid = sum((x[f].varValue or 0) * (1 if f in ["Urea", "MAP", "MKP"] else -1) for f in ferts)
            ph_status = "🔴 Asidik" if acid > 50 else ("🔵 Bazik" if acid < -50 else "🟢 Dengeli")
            st.metric("pH Durumu", ph_status)
            
            st.metric("Toplam Gübre (kg/m²)", round(total_amount, 3))
            total_cost = sum((x[f].varValue or 0) * prices[f] for f in ferts)
            st.metric("Toplam Maliyet (₺)", f"₺{round(total_cost, 2)}")
    
    except Exception as e:
        st.error(f"❌ Hata: {str(e)}")
