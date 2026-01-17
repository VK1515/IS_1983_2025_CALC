import streamlit as st
import pandas as pd
import math

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="IS 1893:2025 Seismic Force Calculator",
    layout="wide"
)

st.title("IS 1893:2025 – Seismic Force Calculator")
st.caption("Equivalent Static Method | Direction-wise (X & Y)")

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
# SESSION STATE INITIALIZATION
# --------------------------------------------------
if "base_shear" not in st.session_state:
    st.session_state.base_shear = {}

# --------------------------------------------------
# SPECTRAL FUNCTIONS (IS 1893:2025)
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
    return {"A/B":0.80, "C":0.82, "D":0.85}[site]

def gamma_v(TV, site):
    return {"A/B":1/TV, "C":1.5/TV, "D":2.0/TV}[site]

# --------------------------------------------------
# TABS
# --------------------------------------------------
tab1, tab2 = st.tabs([
    "① Base Shear Calculation (X & Y)",
    "② Storey-wise Force Distribution"
])

# ==================================================
# TAB 1 – BASE SHEAR
# ==================================================
with tab1:
    st.subheader("Direction-wise Base Shear Calculation")

    zone = st.selectbox("Earthquake Zone", ["II", "III", "IV", "V", "VI"])
    TR = st.selectbox("Return Period TR (years)", [75,175,275,475,975,1275,2475,4975,9975])
    Z = Z_TABLE[zone][TR]
    st.info(f"Design Zone Factor Z = {Z}")

    I = st.number_input("Importance Factor (I)", value=1.0)
    R = st.number_input("Response Reduction Factor (R)", value=5.0)
    site = st.selectbox("Site Class", ["A/B", "C", "D"])
    W = st.number_input("Total Seismic Weight W (kN)", value=10000.0)

    st.markdown("### Building Geometry")
    H = st.number_input("Total Height H (m)", value=15.0)
    dx = st.number_input("Plan Dimension in X direction dx (m)", value=10.0)
    dy = st.number_input("Plan Dimension in Y direction dy (m)", value=15.0)

    TV = st.number_input("Vertical Natural Period TV (s)", value=0.4)

    if st.button("Compute Base Shear"):
        # Approximate periods
        Tx = 0.09 * H / math.sqrt(dx)
        Ty = 0.09 * H / math.sqrt(dy)

        # Horizontal base shear
        Vx = (Z * I * A_NH(Tx, site) / R) * W
        Vy = (Z * I * A_NH(Ty, site) / R) * W

        # Vertical base shear
        Vv = Z * I * delta_v(TV, site) * gamma_v(TV, site) * W

        st.session_state.base_shear = {
            "X": Vx,
            "Y": Vy,
            "V": Vv,
            "W": W,
            "Tx": Tx,
            "Ty": Ty
        }

        st.success("Base shear and fundamental periods computed and locked.")

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("Tx (s)", f"{Tx:.3f}")
        with c2:
            st.metric("Ty (s)", f"{Ty:.3f}")
        with c3:
            st.metric("VBD,H,X (kN)", f"{Vx:.2f}")
        with c4:
            st.metric("VBD,H,Y (kN)", f"{Vy:.2f}")
        with c5:
            st.metric("VBD,V (kN)", f"{Vv:.2f}")

# ==================================================
# TAB 2 – STOREY DISTRIBUTION
# ==================================================
with tab2:
    st.subheader("Storey-wise Seismic Force Distribution")

    if not st.session_state.base_shear:
        st.warning("Please compute base shear in Tab ① first.")
    else:
        direction = st.selectbox("Select Horizontal Direction", ["X", "Y"])

        V_BD_H = st.session_state.base_shear[direction]
        V_BD_V = st.session_state.base_shear["V"]
        W_total = st.session_state.base_shear["W"]

        N = st.number_input("Number of Storeys", min_value=1, value=5)

        storey_data = []
        for i in range(1, N + 1):
            c1, c2 = st.columns(2)
            with c1:
                Wi = st.number_input(
                    f"W{i} – Seismic Weight (kN)",
                    value=W_total / N,
                    key=f"W{i}"
                )
            with c2:
                Hi = st.number_input(
                    f"H{i} – Height from Base (m)",
                    value=3.0 * i,
                    key=f"H{i}"
                )
            storey_data.append([i, Wi, Hi])

        df = pd.DataFrame(storey_data, columns=["Storey", "Wi (kN)", "Hi (m)"])

        # Horizontal distribution
        df["WiHi²"] = df["Wi (kN)"] * df["Hi (m)"]**2
        df["QDi,H (kN)"] = df["WiHi²"] / df["WiHi²"].sum() * V_BD_H
        df["VDi,H (kN)"] = df["QDi,H (kN)"][::-1].cumsum()[::-1]

        # Vertical distribution
        df["QDi,V (kN)"] = df["Wi (kN)"] / df["Wi (kN)"].sum() * V_BD_V
        df["VDi,V (kN)"] = df["QDi,V (kN)"][::-1].cumsum()[::-1]

        st.dataframe(df.round(3), use_container_width=True)

        st.info(
            f"Distribution shown for {direction}-direction horizontal action.\n"
            "Horizontal forces distributed using Wi·Hi².\n"
            "Vertical forces distributed using Wi only."
        )
