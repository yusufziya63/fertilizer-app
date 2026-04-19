import streamlit as st
import pandas as pd
import numpy as np
import os
import io
import json
import csv
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpStatus
from sklearn.linear_model import LinearRegression
from datetime import datetime

st.set_page_config(page_title="Fertilizer Pro AI", layout="wide")
st.title("🌱 Gübre Optimizasyon & AI Sistem")

# ---------------- AYARLAR ----------------
SAVE_FILE = "saved_plans.json"
YIELD_FILE = "yield_data.csv"

# load saved plans into session_state once
if os.path.exists(SAVE_FILE) and "saved_plans" not in st.session_state:
    with open(SAVE_FILE, "r", encoding="utf-8") as f:
        try:
            st.session_state["saved_plans"] = json.load(f)
        except:
            st.session_state["saved_plans"] = []
else:
    st.session_state.setdefault("saved_plans", [])

# ensure yield file exists
if not os.path.exists(YIELD_FILE):
    pd.DataFrame(columns=["N","P","K","Ca","Mg","Yield"]).to_csv(YIELD_FILE, index=False)

# ---------------- SOL MENÜ: MOD SEÇİMİ ----------------
mode = st.sidebar.radio("Mod Seçimi",
                        ("Dönemsel Hesaplama", "Toprağa Göre Hesaplama", "Hedef Verime Göre Hesaplama"))

# period data
period_data = {
    "14 Gün": {"N":130,"P":50,"K":180,"Ca":80,"Mg":30,"S":50},
    "28 Gün": {"N":110,"P":40,"K":200,"Ca":100,"Mg":35,"S":55},
    "56 Gün": {"N":90,"P":30,"K":230,"Ca":130,"Mg":40,"S":60},
    "98 Gün": {"N":70,"P":20,"K":250,"Ca":160,"Mg":45,"S":65}
}

# helper: kullanıcı elle değiştirdiğinde işaretle
def mark_user(k):
    st.session_state[f"user_{k}"] = True

# initialize user flags if missing
for d in ["N","P","K","Ca","Mg","S"]:
    st.session_state.setdefault(f"user_{d}", False)

# ---------------- ORTA: GİRİŞLER VE GÜBRE SEÇİMİ ----------------
st.header("Girişler ve Gübre Seçimi")
left, right = st.columns([2,1])

# Shared fert_db
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

with left:
    st.subheader(f"{mode}")

    if mode == "Dönemsel Hesaplama":
        period = st.selectbox("Dönem seç", list(period_data.keys()), key="period_select")
        auto = period_data[period]

        # period değişince session_state değerlerini güncelle
        if st.session_state.get("last_period") != period:
            st.session_state["last_period"] = period
            for k in ["N","P","K","Ca","Mg","S"]:
                if not st.session_state.get(f"user_{k}", False):
                    st.session_state[k] = auto[k]
                    st.session_state[f"{k}_period"] = auto[k]

        area = st.number_input("Ekim Alanı (da)", value=st.session_state.get("area", 1.0), key="area")
        growth_stage = st.selectbox("Büyüme Dönemi", ["Başlangıç","Vejetatif","Gelişme","Hasat"], key="growth_stage")

        N = st.number_input("N", key="N_period", value=st.session_state.get("N_period", st.session_state.get("N", auto["N"])), on_change=mark_user, args=("N",))
        P = st.number_input("P", key="P_period", value=st.session_state.get("P_period", st.session_state.get("P", auto["P"])), on_change=mark_user, args=("P",))
        K = st.number_input("K", key="K_period", value=st.session_state.get("K_period", st.session_state.get("K", auto["K"])), on_change=mark_user, args=("K",))
        Ca = st.number_input("Ca", key="Ca_period", value=st.session_state.get("Ca_period", st.session_state.get("Ca", auto["Ca"])), on_change=mark_user, args=("Ca",))
        Mg = st.number_input("Mg", key="Mg_period", value=st.session_state.get("Mg_period", st.session_state.get("Mg", auto["Mg"])), on_change=mark_user, args=("Mg",))
        S  = st.number_input("S", key="S_period", value=st.session_state.get("S_period", st.session_state.get("S", auto["S"])), on_change=mark_user, args=("S",))

    elif mode == "Toprağa Göre Hesaplama":
        st.markdown("Toprak Analizi (girdi değerleri)")
        soil_N = st.number_input("Toprak N", 40.0, key="soil_N_input_main")
        soil_P = st.number_input("Toprak P", 5.0, key="soil_P_input_main")
        soil_K = st.number_input("Toprak K", 50.0, key="soil_K_input_main")
        soil_Ca = st.number_input("Toprak Ca", 500.0, key="soil_Ca_input_main")
        soil_Mg = st.number_input("Toprak Mg", 50.0, key="soil_Mg_input_main")

        N = st.number_input("Hedef N", value=st.session_state.get("N", 100.0), key="N_soil_target")
        P = st.number_input("Hedef P", value=st.session_state.get("P", 30.0), key="P_soil_target")
        K = st.number_input("Hedef K", value=st.session_state.get("K", 80.0), key="K_soil_target")
        Ca = st.number_input("Hedef Ca", value=st.session_state.get("Ca", 100.0), key="Ca_soil_target")
        Mg = st.number_input("Hedef Mg", value=st.session_state.get("Mg", 30.0), key="Mg_soil_target")
        S  = st.number_input("Hedef S", value=st.session_state.get("S", 50.0), key="S_soil_target")

    else:
        hedef_verim = st.number_input("Hedef verim (kg/da)", value=5000.0, step=100.0, key="hedef_verim_main")
        efficiency_pct = st.slider("Uygulama verimliliği (%)", min_value=30, max_value=100, value=60, key="eff_pct_main")
        efficiency = efficiency_pct/100.0

        def calculate_nutrients_local(target_yield_kg_per_da):
            per_kg = {"N":0.020,"P":0.036,"K":0.040,"Ca":0.014,"Mg":0.005,"S":0.002}
            return {k: round(v*target_yield_kg_per_da,3) for k,v in per_kg.items()}

        if st.button("Hesapla hedeften", key="calc_target_main"):
            nuts = calculate_nutrients_local(hedef_verim)
            st.session_state["N_target_calc"] = nuts["N"]
            st.session_state["P_target_calc"] = nuts["P"]
            st.session_state["K_target_calc"] = nuts["K"]
            st.session_state["Ca_target_calc"] = nuts["Ca"]
            st.session_state["Mg_target_calc"] = nuts["Mg"]
            st.session_state["S_target_calc"] = nuts["S"]
            st.success("Hedef nutrientler hesaplandı.")

        N = st.number_input("N", value=st.session_state.get("N_target_calc", st.session_state.get("N",100.0)), key="N_target_ui")
        P = st.number_input("P", value=st.session_state.get("P_target_calc", st.session_state.get("P",30.0)), key="P_target_ui")
        K = st.number_input("K", value=st.session_state.get("K_target_calc", st.session_state.get("K",80.0)), key="K_target_ui")
        Ca = st.number_input("Ca", value=st.session_state.get("Ca_target_calc", st.session_state.get("Ca",100.0)), key="Ca_target_ui")
        Mg = st.number_input("Mg", value=st.session_state.get("Mg_target_calc", st.session_state.get("Mg",30.0)), key="Mg_target_ui")
        S = st.number_input("S", value=st.session_state.get("S_target_calc", st.session_state.get("S",50.0)), key="S_target_ui")

with right:
    st.subheader("🧪 Gübre seç + fiyat")
    selected = {}
    costs = {}
    for f in fert_db:
        c1, c2 = st.columns([2,1])
        with c1:
            use = st.checkbox(f, True, key=f+"_use_main")
        with c2:
            price = st.number_input(f"{f} fiyat (birim/kg)", 5.0, key=f+"_price_main")
        if use:
            selected[f] = fert_db[f]
            costs[f] = price

# ---------------- ALT: BUTONLAR ----------------
st.markdown("---")
btn_col1, btn_col2, btn_col3 = st.columns([1,1,1])
with btn_col1:
    al_optimize = st.button("AL OPTIMIZE", key="al_opt_main")
with btn_col2:
    optimize = st.button("OPTIMIZE ET", key="opt_main")
with btn_col3:
    save_plan = st.button("KAYDET", key="save_plan_main")

result_box = st.container()

# ---------------- YARDIMCI ----------------
def train(file=YIELD_FILE):
    df = pd.read_csv(file)
    if len(df) < 5: return None
    X = df[["N","P","K","Ca","Mg"]]
    y = df["Yield"]
    m = LinearRegression(); m.fit(X,y)
    return m

def simple_optimizer(requirements, fertilizers, chosen, costs, budget=0.0):
    if not chosen:
        return {"error":"Hiç gübre seçilmedi"}
    model = LpProblem("fert", LpMinimize)
    x = {f: LpVariable(f, 0) for f in chosen}
    model += lpSum(costs[f] * x[f] for f in chosen)
    for elem in ["N","P","K","Ca","Mg","S"]:
        need = requirements.get(elem, 0)
        model += lpSum(fertilizers[f].get(elem, 0) * x[f] for f in chosen) == need
    model.solve()
    if LpStatus[model.status] != "Optimal":
        return {"error":"Çözüm yok"}
    plan = {f: round(x[f].varValue,3) for f in chosen if x[f].varValue and x[f].varValue>0}
    return {"plan": plan, "cost": sum(plan[f]*costs[f] for f in plan)}

# hazır requirements dict
requirements = {
    "N": float(st.session_state.get("N_period", st.session_state.get("N", 0))),
    "P": float(st.session_state.get("P_period", st.session_state.get("P", 0))),
    "K": float(st.session_state.get("K_period", st.session_state.get("K", 0))),
    "Ca": float(st.session_state.get("Ca_period", st.session_state.get("Ca", 0))),
    "Mg": float(st.session_state.get("Mg_period", st.session_state.get("Mg", 0))),
    "S": float(st.session_state.get("S_period", st.session_state.get("S", 0)))
}

# AL optimize
if al_optimize:
    res = simple_optimizer(requirements, fert_db, list(selected.keys()), costs)
    if "error" in res:
        result_box.error(res["error"])
    else:
        result_box.success("AL OPTIMIZE sonucu:")
        result_box.json(res)
        # kaydetme için sakla
        st.session_state["plan_result"] = res

# AI optimize
if optimize:
    model = train()
    if model:
        ...
    res = simple_optimizer(requirements, fert_db, list(selected.keys()), costs)
    if "error" in res:
        result_box.error(res["error"])
    else:
        result_box.success("OPTIMIZE ET sonucu:")
        result_box.json(res)
        # kaydetme için sakla
        st.session_state["plan_result"] = res


# ---------------- KAYDETME ----------------
if save_plan:
    saved = st.session_state.get("saved_plans", [])
    plan_to_save = st.session_state.get("plan_result", {})  # güvenli alınış

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "mode": mode,
        "requirements": requirements,
        "selected": list(selected.keys()),
        "plan": plan_to_save
    }
    saved.append(entry)
    st.session_state["saved_plans"] = saved
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(saved, f, ensure_ascii=False, indent=2)
    st.success("Plan kaydedildi.")
    st.write(entry)


# ---------- KAYDEDİLMİŞ PLANLAR GÖSTERİMİ VE İNDİRME/YÜKLEME ----------
st.markdown("### Kaydedilmiş Planlar")
if st.session_state.get("saved_plans"):
    for i, p in enumerate(st.session_state["saved_plans"]):
        selected_names = ', '.join(p.get('selected', []))
        with st.expander(f"{i+1}. {p['timestamp']} — {p['mode']} — Seçilen: {selected_names}"):
            st.write("**Requirements:**")
            st.json(p.get("requirements", {}))
            st.write("**Plan (hesaplanan gübre ve miktarları):**")
            st.json(p.get("plan", {}))

            # Tek planı CSV olarak indirme
            headers = ["timestamp","mode","req_N","req_P","req_K","req_Ca","req_Mg","req_S","selected","plan_json","cost"]
            csv_buf = io.StringIO()
            writer = csv.writer(csv_buf)
            writer.writerow(headers)
            req = p.get("requirements", {})
            plan_obj = p.get("plan", {})
            cost = plan_obj.get("cost") if isinstance(plan_obj, dict) else ""
            plan_json = json.dumps(plan_obj, ensure_ascii=False)
            selected_str = ",".join(p.get("selected", []))
            writer.writerow([
                p.get("timestamp",""),
                p.get("mode",""),
                req.get("N",""),
                req.get("P",""),
                req.get("K",""),
                req.get("Ca",""),
                req.get("Mg",""),
                req.get("S",""),
                selected_str,
                plan_json,
                cost
            ])
            st.download_button(
                label="Planı indir (CSV)",
                data=csv_buf.getvalue(),
                file_name=f"plan_{p['timestamp'].replace(':','-')}.csv",
                mime="text/csv"
            )
else:
    st.info("Henüz kaydedilmiş plan yok.")

# Toplu CSV indirme
if st.session_state.get("saved_plans"):
    buf = io.StringIO()
    headers = ["timestamp","mode","req_N","req_P","req_K","req_Ca","req_Mg","req_S","selected","plan_json","cost"]
    writer = csv.writer(buf)
    writer.writerow(headers)
    for p in st.session_state["saved_plans"]:
        req = p.get("requirements", {})
        plan_obj = p.get("plan", {})
        cost = plan_obj.get("cost") if isinstance(plan_obj, dict) else ""
        plan_json = json.dumps(plan_obj, ensure_ascii=False)
        selected_str = ",".join(p.get("selected", []))
        writer.writerow([
            p.get("timestamp",""),
            p.get("mode",""),
            req.get("N",""),
            req.get("P",""),
            req.get("K",""),
            req.get("Ca",""),
            req.get("Mg",""),
            req.get("S",""),
            selected_str,
            plan_json,
            cost
        ])
    st.download_button(
        "Tüm planları indir (CSV)",
        data=buf.getvalue(),
        file_name="all_saved_plans.csv",
        mime="text/csv"
    )

# CSV import: kullanıcı cihazından yükleyip saved_plans'a ekleme
uploaded = st.file_uploader("CSV ile plan yükle", type=["csv"])
if uploaded is not None:
    s = uploaded.getvalue().decode("utf-8")
    reader = csv.DictReader(io.StringIO(s))
    loaded = []
    for row in reader:
        try:
            plan_obj = json.loads(row.get("plan_json","{}"))
        except Exception:
            plan_obj = {}
        entry = {
            "timestamp": row.get("timestamp","") or datetime.utcnow().isoformat(),
            "mode": row.get("mode","") or "Imported",
            "requirements": {
                "N": float(row.get("req_N") or 0),
                "P": float(row.get("req_P") or 0),
                "K": float(row.get("req_K") or 0),
                "Ca": float(row.get("req_Ca") or 0),
                "Mg": float(row.get("req_Mg") or 0),
                "S": float(row.get("req_S") or 0)
            },
            "selected": [s for s in (row.get("selected") or "").split(",") if s],
            "plan": plan_obj
        }
        loaded.append(entry)
    if loaded:
        saved = st.session_state.get("saved_plans", [])
        saved.extend(loaded)
        st.session_state["saved_plans"] = saved
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(saved, f, ensure_ascii=False, indent=2)
        st.success(f"{len(loaded)} plan yüklendi ve kaydedildi.")

# ---------- YIELD verisi kaydetme (sizin mevcut kodunuzdan kopya) ----------
y = st.number_input("Verim kg/da (AI için kayıt)", 0.0, key="yield_input_main")
if st.button("💾 Veriyi Kaydet", key="save_yield_main"):
    try:
        df = pd.read_csv(YIELD_FILE)
    except Exception:
        # eğer dosya yoksa sütunları oluştur
        df = pd.DataFrame(columns=["N","P","K","Ca","Mg","Yield"])
    row = {
        "N": float(requirements.get("N",0)),
        "P": float(requirements.get("P",0)),
        "K": float(requirements.get("K",0)),
        "Ca": float(requirements.get("Ca",0)),
        "Mg": float(requirements.get("Mg",0)),
        "Yield": float(st.session_state.get("yield_input_main", 0.0))
    }
    new = pd.DataFrame([row], columns=df.columns)
    pd.concat([df, new], ignore_index=True).to_csv(YIELD_FILE, index=False)
    st.success("Veri kaydedildi.")