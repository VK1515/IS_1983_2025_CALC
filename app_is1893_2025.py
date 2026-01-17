import streamlit as st
import pandas as pd
import math
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table
from reportlab.lib.styles import getSampleStyleSheet

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="IS 1893:2025 Seismic Force Calculator",
    layout="wide"
)

st.title("IS 1893:2025 – Seismic Force Calculator")
st.caption(
    "Equivalent Static Method | Direction-wise | Multi-Zone Capability\n\n"
    "⚠️ **For educational use only**  \n"
    "**Created by: Vrushali Kamalakar**"
)

# ==================================================
# Z TABLE (IS 1893:2025)
# ==================================================
Z_TABLE = {
    "VI": {75:0.300,175:0.375,275:0.450,475:0.500,975:0.600,1275:0.625,2475:0.750,4975:0.940,9975:1.125},
    "V":  {75:0.200,175:0.250,275:0.300,475:0.333,975:0.400,1275:0.4167,2475:0.500,4975:0.625,9975:0.750},
    "IV": {75:0.140,175:0.175,275:0.210,475:0.233,975:0.280,1275:0.2917,2475:0.350,4975:0.440,9975:0.525},
    "III":{75:0.0625,175:0.085,275:0.100,475:0.125,975:0.167,1275:0.1875,2475:0.250,4975:0.333,9975:0.450},
    "II": {75:0.0375,175:0.050,275:0.060,475:0.075,975:0.100,1275:0.1125,2475:0.150,4975:0.200,9975:0.270}
}

# ==================================================
# SESSION STATE
# ==================================================
if "base_shear" not in st.session_state:
    st.session_state.base_shear = {}

# ==================================================
# SPECTRAL FUNCTIONS (IS 1893:2025)
# ==================================================
def A_NH(T, site):
    if site == "A/B":
        return 2.5 if T <= 0.4 else (1/T if T <= 6 else 6/T**2)
    if site == "C":
        return 2.5 if T <= 0.6 else (1.5/T if T <= 6 else 9/T**2)
    return 2.5 if T <= 0.8 else (2/T if T <= 6 else 12/T**2)

def delta_v(T, site):
    if T > 0.10:
        return 0.67
    return {"A/B":0.80, "C":0.82, "D":0.85}[site]

def gamma_v(T, site):
    return {"A/B":1/T, "C":1.5/T, "D":2.0/T}[site]

# ==================================================
# TABS
# ==================================================
tab1, tab2, tab3 = st.tabs([
    "① Base Shear (X & Y)",
    "② Storey-wise Distribution & Export",
    "③ Multi-Zone Base Shear Study"
])

# ==================================================
# TAB 1 – BASE SHEAR
# ==================================================
with tab1:
    st.subheader("Direction-wise Base Shear Calculation")

    zone = st.selectbox("Earthquake Zone", ["II","III","IV","V","VI"])
    TR = st.selectbox("Return Period TR (years)", [75,175,275,475,975,1275,2475,4975,9975])
    Z = Z_TABLE[zone][TR]
    st.info(f"Zone Factor Z = {Z}")

    I = st.number_input("Importance Factor (I)", value=1.0)
    R = st.number_input("Response Reduction Factor (R)", value=5.0)
    site = st.selectbox("Site Class", ["A/B","C","D"])
    W = st.number_input("Total Seismic Weight W (kN)", value=10000.0)

    st.markdown("### Building Geometry")
    H = st.number_input("Total Height H (m)", value=15.0)
    dx = st.number_input("Plan Dimension dx (m)", value=10.0)
    dy = st.number_input("Plan Dimension dy (m)", value=15.0)

    TV = st.number_input("Vertical Period TV (s)", value=0.4)

    if st.button("Compute Base Shear"):
        Tx = 0.09 * H / math.sqrt(dx)
        Ty = 0.09 * H / math.sqrt(dy)

        Vx = (Z * I * A_NH(Tx, site) / R) * W
        Vy = (Z * I * A_NH(Ty, site) / R) * W
        Vv = Z * I * delta_v(TV, site) * gamma_v(TV, site) * W

        st.session_state.base_shear = {
            "Zone": zone, "TR": TR, "Z": Z,
            "I": I, "R": R, "Site": site,
            "W": W, "Tx": Tx, "Ty": Ty,
            "Vx": Vx, "Vy": Vy, "Vv": Vv
        }

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: st.metric("Tx (s)", f"{Tx:.3f}")
        with c2: st.metric("Ty (s)", f"{Ty:.3f}")
        with c3: st.metric("VBD,H,X (kN)", f"{Vx:.2f}")
        with c4: st.metric("VBD,H,Y (kN)", f"{Vy:.2f}")
        with c5: st.metric("VBD,V (kN)", f"{Vv:.2f}")

# ==================================================
# TAB 2 – STOREY DISTRIBUTION & EXPORT
# ==================================================
with tab2:
    st.subheader("Storey-wise Seismic Force Distribution")

    if not st.session_state.base_shear:
        st.warning("Compute base shear in Tab ① first.")
    else:
        direction = st.selectbox("Horizontal Direction", ["X","Y"])
        Vh = st.session_state.base_shear["Vx"] if direction == "X" else st.session_state.base_shear["Vy"]
        Vv = st.session_state.base_shear["Vv"]
        W = st.session_state.base_shear["W"]

        N = st.number_input("Number of Storeys", min_value=1, value=5)

        data = []
        for i in range(1, N+1):
            Wi = st.number_input(f"W{i} (kN)", value=W/N, key=f"W{i}")
            Hi = st.number_input(f"H{i} (m)", value=3*i, key=f"H{i}")
            data.append([i, Wi, Hi])

        df = pd.DataFrame(data, columns=["Storey","Wi (kN)","Hi (m)"])
        df["WiHi²"] = df["Wi (kN)"] * df["Hi (m)"]**2
        df["QDi,H"] = df["WiHi²"] / df["WiHi²"].sum() * Vh
        df["VDi,H"] = df["QDi,H"][::-1].cumsum()[::-1]
        df["QDi,V"] = df["Wi (kN)"] / df["Wi (kN)"].sum() * Vv
        df["VDi,V"] = df["QDi,V"][::-1].cumsum()[::-1]

        st.dataframe(df.round(3), use_container_width=True)

# ==================================================
# TAB 3 – MULTI-ZONE STUDY
# ==================================================
with tab3:
    st.subheader("Multi-Zone Base Shear Comparison")

    zones = st.multiselect("Select Zones", ["II","III","IV","V","VI"], default=["II","III","IV","V"])
    TR = st.selectbox("Return Period (years)", [75,175,275,475,975,1275,2475,4975,9975], key="mz_tr")
    I = st.number_input("Importance Factor", value=1.0, key="mz_I")
    R = st.number_input("Response Reduction Factor", value=5.0, key="mz_R")
    site = st.selectbox("Site Class", ["A/B","C","D"], key="mz_site")
    W = st.number_input("Total Weight W (kN)", value=10000.0, key="mz_W")
    H = st.number_input("Height H (m)", value=15.0, key="mz_H")
    dx = st.number_input("dx (m)", value=10.0, key="mz_dx")
    dy = st.number_input("dy (m)", value=15.0, key="mz_dy")

    if st.button("Compute Multi-Zone Base Shear"):
        Tx = 0.09 * H / math.sqrt(dx)
        Ty = 0.09 * H / math.sqrt(dy)

        rows = []
        for z in zones:
            Z = Z_TABLE[z][TR]
            rows.append([z, Z,
                         (Z*I*A_NH(Tx,site)/R)*W,
                         (Z*I*A_NH(Ty,site)/R)*W])

        dfz = pd.DataFrame(rows, columns=["Zone","Z","Vx (kN)","Vy (kN)"])
        st.dataframe(dfz.round(3), use_container_width=True)

        fig, ax = plt.subplots()
        ax.plot(dfz["Zone"], dfz["Vx (kN)"], marker="o", label="X direction")
        ax.plot(dfz["Zone"], dfz["Vy (kN)"], marker="s", label="Y direction")
        ax.set_xlabel("Zone")
        ax.set_ylabel("Base Shear (kN)")
        ax.set_title("Base Shear Variation with Seismic Zone")
        ax.grid(True)
        ax.legend()
        st.pyplot(fig)

# ==================================================
# FOOTER / DISCLAIMER
# ==================================================
st.markdown("---")
st.info(
    "📘 **For Educational Use Only**\n\n"
    "This application is intended for learning, teaching, and academic demonstration of "
    "IS 1893:2025 concepts. It must not be used directly for professional design or statutory "
    "submission without independent verification.\n\n"
    "**Created by: Vrushali Kamalakar**"
)
