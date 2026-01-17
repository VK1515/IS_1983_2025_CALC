import streamlit as st
import pandas as pd
import math
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Image
from reportlab.lib.styles import getSampleStyleSheet
from openpyxl import load_workbook
from openpyxl.chart import LineChart, Reference
import os

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
    "⚠️ For educational use only\n"
    "Created by: Vrushali Kamalakar"
)

# ==================================================
# Z TABLE (IS 1893:2025 – COMPLETE)
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
if "multi_zone_df" not in st.session_state:
    st.session_state.multi_zone_df = None

# ==================================================
# FUNCTIONS
# ==================================================
def A_NH(T, site):
    if site == "A/B":
        return 2.5 if T <= 0.4 else (1/T if T <= 6 else 6/T**2)
    if site == "C":
        return 2.5 if T <= 0.6 else (1.5/T if T <= 6 else 9/T**2)
    return 2.5 if T <= 0.8 else (2/T if T <= 6 else 12/T**2)

def delta_v(T, site):
    return 0.67 if T > 0.10 else {"A/B":0.80, "C":0.82, "D":0.85}[site]

def gamma_v(T, site):
    return {"A/B":1/T, "C":1.5/T, "D":2.0/T}[site]

def safe_image(path, w=400, h=250):
    return Image(path, w, h) if os.path.exists(path) else None

# ==================================================
# TABS
# ==================================================
tab1, tab2, tab3 = st.tabs([
    "① Base Shear",
    "② Storey-wise Distribution",
    "③ Multi-Zone Study & Export"
])

# ==================================================
# TAB 1 – BASE SHEAR
# ==================================================
with tab1:
    zone = st.selectbox("Earthquake Zone", list(Z_TABLE.keys()))
    TR = st.selectbox("Return Period TR (years)", list(Z_TABLE[zone].keys()))
    Z = Z_TABLE[zone][TR]

    I = st.number_input("Importance Factor I", value=1.0)
    R = st.number_input("Response Reduction Factor R", value=5.0)
    site = st.selectbox("Site Class", ["A/B","C","D"])
    W = st.number_input("Total Seismic Weight W (kN)", value=10000.0)

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
            "Zone": zone,
            "Return Period (years)": TR,
            "Z": Z,
            "Importance Factor I": I,
            "Response Reduction Factor R": R,
            "Site Class": site,
            "Total Seismic Weight W (kN)": W,
            "Tx (s)": Tx,
            "Ty (s)": Ty,
            "VBD,H,X (kN)": Vx,
            "VBD,H,Y (kN)": Vy,
            "VBD,V (kN)": Vv
        }

        st.success("Base shear computed.")

# ==================================================
# TAB 2 – STOREY DISTRIBUTION
# ==================================================
with tab2:
    if not st.session_state.base_shear:
        st.warning("Compute base shear in Tab ① first.")
    else:
        direction = st.selectbox("Horizontal Direction", ["X","Y"])
        Vh = st.session_state.base_shear["VBD,H,X (kN)"] if direction=="X" else st.session_state.base_shear["VBD,H,Y (kN)"]
        Vv = st.session_state.base_shear["VBD,V (kN)"]
        W = st.session_state.base_shear["Total Seismic Weight W (kN)"]

        N = st.number_input("Number of Storeys", min_value=1, value=5)

        rows=[]
        for i in range(1, N+1):
            Wi = st.number_input(f"W{i} (kN)", value=W/N, key=f"W_{i}")
            Hi = st.number_input(f"H{i} (m)", value=3*i, key=f"H_{i}")
            rows.append([i, Wi, Hi])

        df = pd.DataFrame(rows, columns=["Storey","Wi (kN)","Hi (m)"])
        df["WiHi²"] = df["Wi (kN)"] * df["Hi (m)"]**2
        df["QDi,H"] = df["WiHi²"] / df["WiHi²"].sum() * Vh
        df["VDi,H"] = df["QDi,H"][::-1].cumsum()[::-1]
        df["QDi,V"] = df["Wi (kN)"] / df["Wi (kN)"].sum() * Vv
        df["VDi,V"] = df["QDi,V"][::-1].cumsum()[::-1]

        st.dataframe(df.round(3), use_container_width=True)

# ==================================================
# TAB 3 – MULTI-ZONE STUDY & EXPORT
# ==================================================
with tab3:
    if not st.session_state.base_shear:
        st.warning("Compute base shear in Tab ① first.")
    else:
        base_df = pd.DataFrame(
            list(st.session_state.base_shear.items()),
            columns=["Parameter","Value"]
        )

        st.subheader("Base Shear – Summary Output")
        st.dataframe(base_df, use_container_width=True)

        # ---------------- EXPORT ----------------
        excel_file = "IS1893_2025_Full_Output.xlsx"
        with pd.ExcelWriter(excel_file) as writer:
            base_df.to_excel(writer, "Base_Shear", index=False)

        st.download_button(
            "Download Excel (with Base Shear)",
            open(excel_file,"rb"),
            file_name=excel_file
        )

        pdf_file = "IS1893_2025_Full_Output.pdf"
        doc = SimpleDocTemplate(pdf_file)
        styles = getSampleStyleSheet()
        content = [
            Paragraph("IS 1893:2025 – Seismic Analysis Output", styles["Title"]),
            Paragraph("For educational use only<br/>Created by: Vrushali Kamalakar", styles["Normal"]),
            Table([base_df.columns.tolist()] + base_df.values.tolist())
        ]
        doc.build(content)

        st.download_button(
            "Download PDF (with Base Shear)",
            open(pdf_file,"rb"),
            file_name=pdf_file
        )

# ==================================================
# FOOTER
# ==================================================
st.markdown("---")
st.info(
    "📘 For educational use only. Independent verification is mandatory before "
    "professional or statutory application."
)
