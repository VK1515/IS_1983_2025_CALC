import streamlit as st
import pandas as pd
import math
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table
from reportlab.lib.styles import getSampleStyleSheet

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="IS 1893:2025 Seismic Calculator",
    layout="wide"
)

st.title("IS 1893:2025 – Seismic Force Calculator")
st.caption("Equivalent Static Method | Base Shear → Storey-wise Distribution")

# --------------------------------------------------
# Z TABLE (IS 1893:2025)
# --------------------------------------------------
Z_TABLE = {
    "VI": {75:0.300,175:0.375,275:0.450,475:0.500,975:0.600,1275:0.625,2475:0.750,4975:0.940,9975:1.125},
    "V":  {75:0.200,175:0.250,275:0.300,475:0.333,975:0.400,1275:0.4167,2475:0.500,4975:0.625,9975:0.750},
    "IV": {75:0.140,175:0.175,275:0.210,475:0.233,975:0.280,1275:0.2917,2475:0.350,4975:0.440,9975:0.525},
    "III":{75:0.0625,175:0.085,275:0.100,475:0.125,975:0.167,1275:0.1875,2475:0.250,4975:0.333,9975:0.450},
    "II": {75:0.0375,175:0.050,275:0.060,475:0.075,975:0.100,1275:0.1125,2475:0.150,4975:0.200,9975:0.270}
}

# --------------------------------------------------
# SESSION STATE INIT
# --------------------------------------------------
if "V_BD_H" not in st.session_state:
    st.session_state.V_BD_H = None
    st.session_state.V_BD_V = None
    st.session_state.W_total = None

# --------------------------------------------------
# SPECTRAL FUNCTIONS
# --------------------------------------------------
def A_NH(TH, site):
    if site == "A/B":
        return 2.5 if TH <= 0.4 else (1/TH if TH <= 6 else 6/TH**2)
    if site == "C":
        return 2.5 if TH <= 0.6 else (1.5/TH if TH <= 6 else 9/TH**2)
    return 2.5 if TH <= 0.8 else (2/TH if TH <= 6 else 12/TH**2)

def delta_v(TV, site):
    if TV > 0.10:
        return 0.67
    return {"A/B":0.80,"C":0.82,"D":0.85}[site]

def gamma_v(TV, site):
    return {"A/B":1/TV,"C":1.5/TV,"D":2/TV}[site]

# --------------------------------------------------
# TABS
# --------------------------------------------------
tab1, tab2 = st.tabs(["① Base Shear Calculation", "② Storey-wise Force Distribution"])

# ==================================================
# TAB 1 – BASE SHEAR
# ==================================================
with tab1:
    st.subheader("Base Shear Calculation")

    zone = st.selectbox("Earthquake Zone", ["II","III","IV","V","VI"])
    TR = st.selectbox("Return Period TR (years)", [75,175,275,475,975,1275,2475,4975,9975])
    Z = Z_TABLE[zone][TR]

    st.info(f"Design Zone Factor Z = {Z}")

    I = st.number_input("Importance Factor (I)", value=1.0)
    R = st.number_input("Response Reduction Factor (R)", value=5.0)
    site = st.selectbox("Site Class", ["A/B","C","D"])

    W_total = st.number_input("Total Seismic Weight W (kN)", value=10000.0)

    st.markdown("#### Approximate Fundamental Period (Horizontal)")
    use_Ta = st.checkbox("Use Ta = 0.09H / √d", value=True)

    H = st.number_input("Total Height H (m)", value=15.0)
    d = st.number_input("Base Dimension d (m)", value=10.0)
    TH_manual = st.number_input("Manual TH (s)", value=1.0)

    TV = st.number_input("Vertical Period TV (s)", value=0.4)

    TH = 0.09*H/math.sqrt(d) if use_Ta else TH_manual

    if st.button("Compute Base Shear"):
        A_HD = (Z * I * A_NH(TH, site)) / R
        V_BD_H = A_HD * W_total

        A_NV = delta_v(TV, site) * gamma_v(TV, site)
        V_BD_V = Z * I * A_NV * W_total

        st.session_state.V_BD_H = V_BD_H
        st.session_state.V_BD_V = V_BD_V
        st.session_state.W_total = W_total

        st.success("Base shear computed and locked.")

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Horizontal Base Shear (kN)", f"{V_BD_H:.2f}")
        with c2:
            st.metric("Vertical Base Shear (kN)", f"{V_BD_V:.2f}")

# ==================================================
# TAB 2 – STOREY DISTRIBUTION
# ==================================================
with tab2:
    st.subheader("Storey-wise Seismic Force Distribution")

    if st.session_state.V_BD_H is None:
        st.warning("Please compute base shear in Tab ① first.")
    else:
        V_BD_H = st.session_state.V_BD_H
        V_BD_V = st.session_state.V_BD_V

        N = st.number_input("Number of Storeys", min_value=1, value=5)

        storey_data = []
        for i in range(1, N+1):
            c1, c2 = st.columns(2)
            with c1:
                Wi = st.number_input(f"W{i} (kN)", value=st.session_state.W_total/N, key=f"Wi{i}")
            with c2:
                Hi = st.number_input(f"H{i} (m)", value=3*i, key=f"Hi{i}")
            storey_data.append([i, Wi, Hi])

        df = pd.DataFrame(storey_data, columns=["Storey","Wi (kN)","Hi (m)"])
        df["WiHi²"] = df["Wi (kN)"] * df["Hi (m)"]**2

        df["QDi,H (kN)"] = df["WiHi²"] / df["WiHi²"].sum() * V_BD_H
        df["VDi,H (kN)"] = df["QDi,H (kN)"][::-1].cumsum()[::-1]

        df["QDi,V (kN)"] = df["Wi (kN)"] / df["Wi (kN)"].sum() * V_BD_V
        df["VDi,V (kN)"] = df["QDi,V (kN)"][::-1].cumsum()[::-1]

        st.dataframe(df.round(3), use_container_width=True)
