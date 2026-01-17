import streamlit as st
import pandas as pd
import math
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Image
from reportlab.lib.styles import getSampleStyleSheet
from openpyxl import load_workbook
from openpyxl.chart import LineChart, Reference

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
if "storey_df" not in st.session_state:
    st.session_state.storey_df = None
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
    if T > 0.10:
        return 0.67
    return {"A/B":0.80, "C":0.82, "D":0.85}[site]

def gamma_v(T, site):
    return {"A/B":1/T, "C":1.5/T, "D":2.0/T}[site]

def build_base_shear_df():
    bs = st.session_state.base_shear
    return pd.DataFrame([
        ["Earthquake Zone", bs["Zone"]],
        ["Return Period (years)", bs["TR"]],
        ["Zone Factor Z", bs["Z"]],
        ["Importance Factor I", bs["I"]],
        ["Response Reduction Factor R", bs["R"]],
        ["Site Class", bs["Site"]],
        ["Total Height H (m)", bs["H"]],
        ["Plan Dimension dx (m)", bs["dx"]],
        ["Plan Dimension dy (m)", bs["dy"]],
        ["Total Seismic Weight W (kN)", bs["W"]],
        ["Time Period Tx (s)", round(bs["Tx"], 3)],
        ["Time Period Ty (s)", round(bs["Ty"], 3)],
        ["Base Shear Vx (kN)", round(bs["Vx"], 2)],
        ["Base Shear Vy (kN)", round(bs["Vy"], 2)],
        ["Vertical Base Shear Vv (kN)", round(bs["Vv"], 2)],
    ], columns=["Parameter", "Value"])

# ==================================================
# TABS
# ==================================================
tab1, tab2, tab3 = st.tabs([
    "① Base Shear (X & Y)",
    "② Storey-wise Distribution",
    "③ Multi-Zone Study & Export"
])

# ==================================================
# TAB 1 – BASE SHEAR
# ==================================================
with tab1:
    zone = st.selectbox("Earthquake Zone", ["II","III","IV","V","VI"])
    TR = st.selectbox("Return Period TR (years)", [75,175,275,475,975,1275,2475,4975,9975])
    Z = Z_TABLE[zone][TR]

    I = st.number_input("Importance Factor (I)", value=1.0)
    R = st.number_input("Response Reduction Factor (R)", value=5.0)
    site = st.selectbox("Site Class", ["A/B","C","D"])
    W = st.number_input("Total Seismic Weight W (kN)", value=10000.0)

    H  = st.number_input("Total Height H (m)", value=15.0)
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
            "Zone":zone,"TR":TR,"Z":Z,
            "I":I,"R":R,"Site":site,
            "W":W,"H":H,"dx":dx,"dy":dy,
            "Tx":Tx,"Ty":Ty,"Vx":Vx,"Vy":Vy,"Vv":Vv
        }

        st.success("Base shear computed successfully")

# ==================================================
# TAB 2 – STOREY DISTRIBUTION + PLOT
# ==================================================
with tab2:
    if not st.session_state.base_shear:
        st.warning("Compute base shear in Tab ① first.")
    else:
        Vx = st.session_state.base_shear["Vx"]
        Vy = st.session_state.base_shear["Vy"]
        Vv = st.session_state.base_shear["Vv"]

        N = st.number_input("Number of Storeys", min_value=1, value=5)

        rows=[]
        for i in range(1,N+1):
            Wi = st.number_input(f"W{i} (kN)", value=1000.0, key=f"W{i}")
            Hi = st.number_input(f"H{i} (m)", value=3*i, key=f"H{i}")
            rows.append([i,Wi,Hi])

        df = pd.DataFrame(rows, columns=["Storey","Wi","Hi"])
        df["WiHi2"] = df["Wi"] * df["Hi"]**2

        df["QX"] = df["WiHi2"] / df["WiHi2"].sum() * Vx
        df["QY"] = df["WiHi2"] / df["WiHi2"].sum() * Vy

        df["VX"] = df["QX"][::-1].cumsum()[::-1]
        df["VY"] = df["QY"][::-1].cumsum()[::-1]

        st.session_state.storey_df = df

        # ---- STOREY SHEAR PLOT ----
        fig, ax = plt.subplots()
        ax.plot(df["VX"], df["Hi"], marker="o", label="X-direction")
        ax.plot(df["VY"], df["Hi"], marker="s", label="Y-direction")
        ax.set_xlabel("Storey Shear (kN)")
        ax.set_ylabel("Height (m)")
        ax.set_title("Combined Storey Shear Diagram (X & Y)")
        ax.grid(True)
        ax.legend()
        st.pyplot(fig)

        fig.savefig("storey_shear_XY.png", dpi=300)

# ==================================================
# TAB 3 – MULTI-ZONE + EXPORT
# ==================================================
with tab3:
    if st.session_state.storey_df is None:
        st.warning("Complete Tabs ① and ② first.")
    else:
        df_storey = st.session_state.storey_df
        df_base = build_base_shear_df()

        # -------- EXCEL EXPORT --------
        excel_file = "IS1893_2025_Seismic_Output.xlsx"
        with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
            df_base.to_excel(writer, sheet_name="Base_Shear", index=False)
            df_storey.to_excel(writer, sheet_name="Storey_Distribution", index=False)

        st.download_button("Download Excel Output", open(excel_file,"rb"), file_name=excel_file)

        # -------- PDF EXPORT --------
        pdf_file = "IS1893_2025_Seismic_Output.pdf"
        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(pdf_file)

        content = [
            Paragraph("IS 1893:2025 – Seismic Analysis Output", styles["Title"]),
            Paragraph("For educational use only<br/>Created by: Vrushali Kamalakar", styles["Normal"]),
            Paragraph("<b>Base Shear Summary</b>", styles["Heading2"]),
            Table([df_base.columns.tolist()] + df_base.values.tolist()),
            Paragraph("<b>Storey Shear Diagram</b>", styles["Heading2"]),
            Image("storey_shear_XY.png", width=420, height=300),
            Paragraph("<b>Storey-wise Force Distribution</b>", styles["Heading2"]),
            Table([df_storey.columns.tolist()] + df_storey.round(3).values.tolist())
        ]

        doc.build(content)
        st.download_button("Download PDF Output", open(pdf_file,"rb"), file_name=pdf_file)

# ==================================================
# FOOTER
# ==================================================
st.markdown("---")
st.info(
    "📘 For educational use only. Independent verification required for professional use.\n\n"
    "Created by: Vrushali Kamalakar"
)
