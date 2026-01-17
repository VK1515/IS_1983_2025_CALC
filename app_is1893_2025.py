import streamlit as st
import pandas as pd
import math
import matplotlib.pyplot as plt
import os

from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Image
from reportlab.lib.styles import getSampleStyleSheet

from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage

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
# Z TABLE
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

# ==================================================
# TABS
# ==================================================
tab1, tab2, tab3 = st.tabs([
    "① Base Shear",
    "② Storey-wise Distribution",
    "③ Multi-Zone & Export"
])

# ==================================================
# TAB 1 – BASE SHEAR
# ==================================================
with tab1:
    st.subheader("Base Shear Calculation")

    zone = st.selectbox("Earthquake Zone", list(Z_TABLE.keys()))
    TR = st.selectbox("Return Period (years)", list(Z_TABLE[zone].keys()))
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
            "Zone":zone,"TR":TR,"Z":Z,"I":I,"R":R,"Site":site,
            "W (kN)":W,"Tx (s)":round(Tx,3),"Ty (s)":round(Ty,3),
            "Vx (kN)":round(Vx,2),"Vy (kN)":round(Vy,2),"Vv (kN)":round(Vv,2)
        }

        st.success("Base shear computed.")
        st.dataframe(pd.DataFrame(st.session_state.base_shear.items(),
                     columns=["Parameter","Value"]),
                     use_container_width=True)

# ==================================================
# TAB 2 – STOREY DISTRIBUTION + PLOT
# ==================================================
with tab2:
    st.subheader("Storey-wise Seismic Forces")

    if not st.session_state.base_shear:
        st.warning("Compute base shear first.")
    else:
        Vx = st.session_state.base_shear["Vx (kN)"]
        Vy = st.session_state.base_shear["Vy (kN)"]
        W = st.session_state.base_shear["W (kN)"]

        N = st.number_input("Number of Storeys", min_value=1, value=5)

        rows=[]
        for i in range(1, N+1):
            Wi = st.number_input(f"W{i} (kN)", value=W/N, key=f"Wi_{i}")
            Hi = st.number_input(f"H{i} (m)", value=3*i, key=f"Hi_{i}")
            rows.append([i,Wi,Hi])

        df = pd.DataFrame(rows, columns=["Storey","Wi","Hi"])
        df["WiHi²"] = df["Wi"] * df["Hi"]**2

        df["Qi_X"] = df["WiHi²"]/df["WiHi²"].sum()*Vx
        df["VD_X"] = df["Qi_X"][::-1].cumsum()[::-1]

        df["Qi_Y"] = df["WiHi²"]/df["WiHi²"].sum()*Vy
        df["VD_Y"] = df["Qi_Y"][::-1].cumsum()[::-1]

        st.session_state.storey_df = df
        st.dataframe(df.round(3), use_container_width=True)

        fig, ax = plt.subplots()
        ax.plot(df["VD_X"], df["Hi"], marker="o", label="X direction")
        ax.plot(df["VD_Y"], df["Hi"], marker="s", label="Y direction")
        ax.set_xlabel("Storey Shear (kN)")
        ax.set_ylabel("Height from Base (m)")
        ax.set_title("Combined Storey Shear Diagram")
        ax.grid(True)
        ax.legend()
        st.pyplot(fig)

        fig.savefig("storey_shear_XY.png", dpi=300, bbox_inches="tight")

# ==================================================
# TAB 3 – EXPORT
# ==================================================
with tab3:
    st.subheader("Export Results")

    if not st.session_state.storey_df:
        st.warning("Complete Tabs ① and ② first.")
    else:
        base_df = pd.DataFrame(
            st.session_state.base_shear.items(),
            columns=["Parameter","Value"]
        )
        storey_df = st.session_state.storey_df

        excel_file = "IS1893_2025_Seismic_Output.xlsx"
        with pd.ExcelWriter(excel_file) as writer:
            base_df.to_excel(writer, sheet_name="Base_Shear", index=False)
            storey_df.to_excel(writer, sheet_name="Storey_Distribution", index=False)

        wb = load_workbook(excel_file)
        ws = wb.create_sheet("Storey_Shear_Plot")
        ws.add_image(XLImage("storey_shear_XY.png"), "A1")
        wb.save(excel_file)

        st.download_button("Download Excel", open(excel_file,"rb"), file_name=excel_file)

        pdf_file = "IS1893_2025_Seismic_Output.pdf"
        doc = SimpleDocTemplate(pdf_file)
        styles = getSampleStyleSheet()

        content = [
            Paragraph("IS 1893:2025 – Seismic Analysis Output", styles["Title"]),
            Paragraph("For educational use only<br/>Created by: Vrushali Kamalakar", styles["Normal"]),
            Table([base_df.columns.tolist()] + base_df.values.tolist()),
            Image("storey_shear_XY.png", 400, 300),
            Table([storey_df.columns.tolist()] + storey_df.round(3).values.tolist())
        ]

        doc.build(content)
        st.download_button("Download PDF", open(pdf_file,"rb"), file_name=pdf_file)

# ==================================================
# FOOTER
# ==================================================
st.markdown("---")
st.info("For educational use only. Created by: Vrushali Kamalakar")
