import streamlit as st
import pandas as pd
import numpy as np
import os
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpStatus
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="Fertilizer Pro AI", layout="wide")
st.title("🌱 Gübre Optimizasyon & AI Sistem")

# ---------------- DÖNEM ----------------
period_data = {
    "14 Gün": {"N":130,"P":50,"K":180,"Ca":80,"Mg":30,"S":50},
    "28 Gün": {"N":110,"P":40,"K":200,"Ca":100,"Mg":35,"S":55},
    "56 Gün": {"N":90,"P":30,"K":230,"Ca":130,"Mg":40,"S":60},
    "98 Gün": {"N":70,"P":20,"K":250,"Ca":160,"Mg":45,"S":65}
}

# period seçimi ve auto ayar (yerleştirin st.selectbox sonrası)
period = st.selectbox("Dönem seç", list(period_data.keys()), key="period_select")
auto = period_data[period]

# period değişince otomatik güncelleme (sadece kullanıcı değiştirmediyse)
if st.session_state.get("last_period") != period:
    for k in ["N","P","K","Ca","Mg","S"]:
        if not st.session_state.get(f"user_{k}", False):
            st.session_state[k] = auto[k]
    st.session_state["last_period"] = period

# helper: kullanıcı elle değiştirdiğinde işaretle
def mark_user(k):
    st.session_state[f"user_{k}"] = True

# ---------------- INIT SESSION STATE DEFAULTS ----------------
# Ensure flags and defaults exist
for d in ["N","P","K","Ca","Mg","S"]:
    if d not in st.session_state:
        st.session_state[d] = auto[d]
    if f"user_{d}" not in st.session_state:
        st.session_state[f"user_{d}"] = False

# ---------------- HEDEF (widget'lar with on_change) ----------------
col1, col2 = st.columns(2)
with col1:
    N = st.number_input("N", key="N_input", value=st.session_state.get("N", auto["N"]),
                        on_change=mark_user, args=("N",))
    P = st.number_input("P", key="P_input", value=st.session_state.get("P", auto["P"]),
                        on_change=mark_user, args=("P",))
    K = st.number_input("K", key="K_input", value=st.session_state.get("K", auto["K"]),
                        on_change=mark_user, args=("K",))
    Ca = st.number_input("Ca", key="Ca_input", value=st.session_state.get("Ca", auto["Ca"]),
                         on_change=mark_user, args=("Ca",))
    Mg = st.number_input("Mg", key="Mg_input", value=st.session_state.get("Mg", auto["Mg"]),
                         on_change=mark_user, args=("Mg",))
    S  = st.number_input("S", key="S_input", value=st.session_state.get("S", auto["S"]),
                         on_change=mark_user, args=("S",))

with col2:
    Fe = st.number_input("Fe", value=2.5, key="Fe_input")
    Zn = st.number_input("Zn", value=0.5, key="Zn_input")
    Mn = st.number_input("Mn", value=0.6, key="Mn_input")
    Cu = st.number_input("Cu", value=0.1, key="Cu_input")
    B  = st.number_input("B", value=0.3, key="B_input")
    Mo = st.number_input("Mo", value=0.05, key="Mo_input")

# ---------------- HEDEF VERİM -> NUTRIENTS FONKSİYONLARI ----------------
def calculate_nutrients(target_yield_kg_per_da):
    per_kg = {
        "N": 0.012,
        "P": 0.036,
        "K": 0.02,
        "Ca": 0.008,
        "Mg": 0.003,
        "S": 0.004
    }
    nutrients = {k: round(v * target_yield_kg_per_da, 3) for k, v in per_kg.items()}
    nutrients["P2O5_eq_kg_per_da"] = round(nutrients["P"] * 2.29, 3)
    nutrients["K2O_eq_kg_per_da"] = round(nutrients["K"] * 1.2, 3)
    return nutrients

def convert_to_fertilizer(nutrients_kg_per_da, fert_db, efficiency=0.6):
    required = {}
    best_for = {}
    for elem in ["N","P","K","Ca","Mg","S"]:
        best = None
        best_frac = 0
        for f, comp in fert_db.items():
            frac = comp.get(elem, 0) or 0
            if frac > best_frac:
                best_frac = frac
                best = f
        if best:
            best_for[elem] = (best, best_frac)
    for elem, (f, frac) in best_for.items():
        need_elem = nutrients_kg_per_da.get(elem, 0)
        if need_elem <= 0 or frac <= 0:
            continue
        fert_needed_kg = need_elem / frac / max(efficiency, 1e-6)
        required.setdefault(f, 0)
        required[f] += fert_needed_kg
    required = {f: round(q, 3) for f, q in required.items()}
    return required

st.subheader("🎯 Hedef verimden otomatik hesapla")
coly1, coly2 = st.columns([2,1])

# Hedef verim kısmı
hedef_verim = st.number_input("Hedef verim (kg/da)", value=5000.0, step=100.0, key="hedef_verim_input")
efficiency_pct = st.slider("Uygulama verimliliği (%)", min_value=30, max_value=100, value=60, key="eff_pct_slider")
efficiency = efficiency_pct / 100.0

# Hesapla butonu: hesaplayıp ara anahtarları yazar
if st.button("Hesapla ve hedef nutrientleri doldur", key="calc_fill_btn"):
    nutrients = calculate_nutrients(st.session_state["hedef_verim_input"])
    for k in ["N","P","K","Ca","Mg","S"]:
        st.session_state[f"{k}_calc"] = nutrients[k]
    st.session_state["last_calc_efficiency"] = efficiency
    st.success("Hedef nutrientler hesaplandı ve ara değişkenlere yazıldı.")

# Widget'lar: value olarak önce ara anahtarı, yoksa eski session_state/auto al
with coly1:
    N = st.number_input(
        "N",
        key="N_input_after",
        value=st.session_state.get("N_calc", st.session_state.get("N", auto["N"]))
    )
    P = st.number_input(
        "P",
        key="P_input_after",
        value=st.session_state.get("P_calc", st.session_state.get("P", auto["P"]))
    )
    K = st.number_input(
        "K",
        key="K_input_after",
        value=st.session_state.get("K_calc", st.session_state.get("K", auto["K"]))
    )
    Ca = st.number_input(
        "Ca",
        key="Ca_input_after",
        value=st.session_state.get("Ca_calc", st.session_state.get("Ca", auto["Ca"]))
    )
    Mg = st.number_input(
        "Mg",
        key="Mg_input_after",
        value=st.session_state.get("Mg_calc", st.session_state.get("Mg", auto["Mg"]))
    )
    S = st.number_input(
        "S",
        key="S_input_after",
        value=st.session_state.get("S_calc", st.session_state.get("S", auto["S"]))
    )

# opsiyonel gösterim
st.write("Mevcut hedef nutrientler (kg/da):",
         {"N": st.session_state.get("N_calc", st.session_state.get("N")),
          "P": st.session_state.get("P_calc", st.session_state.get("P")),
          "K": st.session_state.get("K_calc", st.session_state.get("K")),
          "Ca": st.session_state.get("Ca_calc", st.session_state.get("Ca")),
          "Mg": st.session_state.get("Mg_calc", st.session_state.get("Mg")),
          "S": st.session_state.get("S_calc", st.session_state.get("S"))})

# ---------------- TOPRAK ----------------
st.subheader("🌍 Toprak Analizi")
soil_N = st.number_input("Toprak N", 40.0, key="soil_N_input")
soil_P = st.number_input("Toprak P", 10.0, key="soil_P_input")
soil_K = st.number_input("Toprak K", 120.0, key="soil_K_input")
soil_Ca = st.number_input("Toprak Ca", 1500.0, key="soil_Ca_input")
soil_Mg = st.number_input("Toprak Mg", 120.0, key="soil_Mg_input")

def classify(v,l,o,h):
    if v < l: return "low"
    elif v < o: return "medium"
    elif v < h: return "good"
    else: return "high"

def mult(s):
    return {"low":1.3,"medium":1.1,"good":0.9,"high":0.5}[s]

if st.checkbox("🤖 Toprağa göre ayarla", key="soil_adjust_chk"):
    st.session_state["N"] = float(st.session_state.get("N", N)) * mult(classify(soil_N,30,60,100))
    st.session_state["P"] = float(st.session_state.get("P", P)) * mult(classify(soil_P,8,20,40))
    st.session_state["K"] = float(st.session_state.get("K", K)) * mult(classify(soil_K,80,150,250))
    st.session_state["Ca"] = float(st.session_state.get("Ca", Ca)) * mult(classify(soil_Ca,1000,2000,4000))
    st.session_state["Mg"] = float(st.session_state.get("Mg", Mg)) * mult(classify(soil_Mg,80,150,300))
    st.success("Toprağa göre güncellendi")

# ---------------- GÜBRE DB ----------------
fert_db = {
    "Urea":{"N":0.46,"P":0,"K":0,"Ca":0,"Mg":0,"S":0,"acid":1},
    "MAP":{"N":0.11,"P":0.52,"K":0,"Ca":0,"Mg":0,"S":0,"acid":2},
    "MKP":{"N":0,"P":0.52,"K":0.34,"Ca":0,"Mg":0,"S":0,"acid":1},
    "KNO3":{"N":0.13,"P":0,"K":0.46,"Ca":0,"Mg":0,"S":0,"acid":-1},
    "CaNO3":{"N":0.15,"P":0,"K":0,"Ca":0.19,"Mg":0,"S":0,"acid":-2},
    "MgSO4":{"N":0,"P":0,"K":0,"Ca":0,"Mg":0.098,"S":0.13,"acid":0},
    "K2SO4":{"N":0,"P":0,"K":0.50,"Ca":0,"Mg":0,"S":0.18,"acid":0},
    "10-30-10":{"N":0.10,"P":0.30,"K":0.10,"Ca":0,"Mg":0,"S":0,"acid":0},
    "10-5-40":{"N":0.10,"P":0.05,"K":0.40,"Ca":0,"Mg":0,"S":0,"acid":0},
    "25-5-0(30SO3)":{"N":0.25,"P":0.05,"K":0,"Ca":0,"Mg":0,"S":0.30,"acid":0},
    "CALSIMAGSİ":{"N":0.13,"P":0,"K":0,"Ca":0.16,"Mg":0.60,"S":0,"acid":0},
    "BESTCALNİ":{"N":0.155,"P":0,"K":0,"Ca":0.27,"Mg":0,"S":0,"acid":0}
}

st.subheader("🧪 Gübre seç + fiyat")
selected={}
costs={}

for f in fert_db:
    c1,c2=st.columns([2,1])
    with c1:
        use=st.checkbox(f, True, key=f+"_use")
    with c2:
        price=st.number_input(f"{f} fiyat (birim/kg)",5.0,key=f+"_price")
    if use:
        selected[f]=fert_db[f]
        costs[f]=price

# ---------------- AI DATA ----------------
file="yield_data.csv"
if not os.path.exists(file):
    pd.DataFrame(columns=["N","P","K","Ca","Mg","Yield"]).to_csv(file,index=False)

def train():
    df=pd.read_csv(file)
    if len(df)<5: return None
    X=df[["N","P","K","Ca","Mg"]]
    y=df["Yield"]
    m=LinearRegression()
    m.fit(X,y)
    return m

# ---------------- AI ----------------
if st.checkbox("🧠 AI optimize", key="ai_opt_chk"):
    model=train()
    if model:
        base=np.array([[st.session_state.get("N", N),
                        st.session_state.get("P", P),
                        st.session_state.get("K", K),
                        st.session_state.get("Ca", Ca),
                        st.session_state.get("Mg", Mg)]])
        best=base.copy()
        best_y=float(model.predict(base)[0])

        for i in range(50):
            test=base*np.random.uniform(0.8,1.2,base.shape)
            y_pred=float(model.predict(test)[0])
            if y_pred>best_y:
                best_y=y_pred
                best=test.copy()

        st.session_state["N"] = float(best[0][0])
        st.session_state["P"] = float(best[0][1])
        st.session_state["K"] = float(best[0][2])
        st.session_state["Ca"] = float(best[0][3])
        st.session_state["Mg"] = float(best[0][4])
        st.success(f"AI optimize etti (verim: {round(best_y,1)})")
    else:
        st.warning("Veri az")

# ---------------- SOLVER ----------------
if st.button("🚀 OPTİMİZE", key="optimize_btn"):

    if not selected:
        st.error("Önce en az bir gübre seçin.")
    else:
        model=LpProblem("fert",LpMinimize)
        x={f:LpVariable(f,0) for f in selected}

        model+=lpSum(costs[f]*x[f] for f in selected)

        model+=lpSum(selected[f]["N"]*x[f] for f in selected)==st.session_state.get("N", N)
        model+=lpSum(selected[f]["P"]*x[f] for f in selected)==st.session_state.get("P", P)
        model+=lpSum(selected[f]["K"]*x[f] for f in selected)==st.session_state.get("K", K)
        model+=lpSum(selected[f]["Ca"]*x[f] for f in selected)==st.session_state.get("Ca", Ca)
        model+=lpSum(selected[f]["Mg"]*x[f] for f in selected)==st.session_state.get("Mg", Mg)
        # S may not exist in some fert_db entries; ensure default 0
        model+=lpSum(selected[f].get("S",0)*x[f] for f in selected)==st.session_state.get("S", S)

        model.solve()

        if LpStatus[model.status]=="Optimal":

            st.subheader("📊 Sonuç")
            result=[]
            for f in selected:
                val = x[f].varValue
                if val and val>0:
                    result.append([f,round(val,2)])

            df=pd.DataFrame(result,columns=["Gübre","Kg"])
            st.dataframe(df)

            # A-B
            st.subheader("🧪 A-B Tank")
            A=[f for f,_ in result if f=="CaNO3"]
            B=[f for f,_ in result if f!="CaNO3"]
            st.write("A:",A)
            st.write("B:",B)

            # EC
            st.subheader("⚡ EC")
            total=sum(x[f].varValue or 0 for f in selected)
            st.write("EC ≈",round(total/1000*1.2,2))

            # pH
            st.subheader("🧪 pH")
            acid=sum(selected[f].get("acid",0)*(x[f].varValue or 0) for f in selected)
            if acid>50: st.write("Asidik")
            elif acid<-50: st.write("Bazik")
            else: st.write("Dengeli")

        else:
            st.error("Çözüm yok")

# ---------------- VERİ KAYDET ----------------
st.subheader("📊 Verim Kaydet")

y=st.number_input("Verim kg/da",0.0, key="yield_input")

if st.button("💾 Kaydet", key="save_btn"):
    df = pd.read_csv(file)

    # Kaydederken "N_calc" öncelikli, yoksa session_state N (ve benzerleri)
    row = {
        "N": float(st.session_state.get("N_calc", st.session_state.get("N", auto["N"]))),
        "P": float(st.session_state.get("P_calc", st.session_state.get("P", auto["P"]))),
        "K": float(st.session_state.get("K_calc", st.session_state.get("K", auto["K"]))),
        "Ca": float(st.session_state.get("Ca_calc", st.session_state.get("Ca", auto["Ca"]))),
        "Mg": float(st.session_state.get("Mg_calc", st.session_state.get("Mg", auto["Mg"]))),
        "Yield": float(st.session_state.get("yield_input", 0.0))
    }

    new = pd.DataFrame([row], columns=df.columns)
    pd.concat([df, new], ignore_index=True).to_csv(file, index=False)
    st.success("Kaydedildi")
