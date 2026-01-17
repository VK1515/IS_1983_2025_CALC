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
    st.subheader("Direction-wise Base Shear")

    zone = st.selectbox("Earthquake Zone", list(Z_TABLE.keys()), key="bs_zone")
    TR = st.selectbox("Return Period (years)", list(Z_TABLE[zone].keys()), key="bs_TR")
    Z = Z_TABLE[zone][TR]

    I = st.number_input("Importance Factor I", value=1.0, key="bs_I")
    R = st.number_input("Response Reduction Factor R", value=5.0, key="bs_R")
    site = st.selectbox("Site Class", ["A/B","C","D"], key="bs_site")
    W = st.number_input("Total Seismic Weight W (kN)", value=10000.0, key="bs_W")

    H = st.number_input("Total Height H (m)", value=15.0, key="bs_H")
    dx = st.number_input("Plan Dimension dx (m)", value=10.0, key="bs_dx")
    dy = st.number_input("Plan Dimension dy (m)", value=15.0, key="bs_dy")
    TV = st.number_input("Vertical Period TV (s)", value=0.4, key="bs_TV")

    if st.button("Compute Base Shear", key="bs_compute"):
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
            "Tx (s)": round(Tx,3),
            "Ty (s)": round(Ty,3),
            "VBD,H,X (kN)": round(Vx,2),
            "VBD,H,Y (kN)": round(Vy,2),
            "VBD,V (kN)": round(Vv,2)
        }

        st.success("Base shear computed.")

        st.dataframe(
            pd.DataFrame(
                st.session_state.base_shear.items(),
                columns=["Parameter","Value"]
            ),
            use_container_width=True
        )

# ==================================================
# TAB 2 – STOREY DISTRIBUTION
# ==================================================
with tab2:
    st.subheader("Storey-wise Seismic Force Distribution")

    if not st.session_state.base_shear:
        st.warning("Compute base shear in Tab ① first.")
    else:
        Vx = st.session_state.base_shear["VBD,H,X (kN)"]
        Vy = st.session_state.base_shear["VBD,H,Y (kN)"]
        W = st.session_state.base_shear["Total Seismic Weight W (kN)"]

        N = st.number_input("Number of Storeys", min_value=1, value=5, key="st_N")

        rows = []
        for i in range(1, N+1):
            Wi = st.number_input(f"W{i} (kN)", value=W/N, key=f"st_W{i}")
            Hi = st.number_input(f"H{i} (m)", value=3*i, key=f"st_H{i}")
            rows.append([i, Wi, Hi])

        df = pd.DataFrame(rows, columns=["Storey","Wi","Hi"])
        df["WiHi²"] = df["Wi"] * df["Hi"]**2

        df["Qi_X"] = df["WiHi²"]/df["WiHi²"].sum() * Vx
        df["VD_X"] = df["Qi_X"][::-1].cumsum()[::-1]

        df["Qi_Y"] = df["WiHi²"]/df["WiHi²"].sum() * Vy
        df["VD_Y"] = df["Qi_Y"][::-1].cumsum()[::-1]

        st.dataframe(df.round(3), use_container_width=True)

        st.subheader("Combined Storey Shear Diagram (X & Y)")
        fig, ax = plt.subplots()
        ax.plot(df["VD_X"], df["Hi"], marker="o", label="X Direction")
        ax.plot(df["VD_Y"], df["Hi"], marker="s", label="Y Direction")
        ax.set_xlabel("Storey Shear (kN)")
        ax.set_ylabel("Height from Base (m)")
        ax.grid(True)
        ax.legend()
        st.pyplot(fig)
        fig.savefig("storey_shear_XY.png", dpi=300, bbox_inches="tight")

# ==================================================
# TAB 3 – MULTI-ZONE & EXPORT
# ==================================================
with tab3:
    st.subheader("Multi-Zone Base Shear & Export")

    if not st.session_state.base_shear:
        st.warning("Compute base shear first.")
    else:
        zones = st.multiselect(
            "Select Zones",
            list(Z_TABLE.keys()),
            default=["II","III","IV","V"],
            key="mz_zones"
        )

        TR = st.selectbox(
            "Return Period (years)",
            list(Z_TABLE[zones[0]].keys()) if zones else [475],
            key="mz_TR"
        )

        I = st.session_state.base_shear["Importance Factor I"]
        R = st.session_state.base_shear["Response Reduction Factor R"]
        site = st.session_state.base_shear["Site Class"]
        W = st.session_state.base_shear["Total Seismic Weight W (kN)"]
        Tx = st.session_state.base_shear["Tx (s)"]
        Ty = st.session_state.base_shear["Ty (s)"]

        data = []
        for z in zones:
            Z = Z_TABLE[z][TR]
            data.append([z, Z,
                         (Z*I*A_NH(Tx,site)/R)*W,
                         (Z*I*A_NH(Ty,site)/R)*W])

        dfz = pd.DataFrame(data, columns=["Zone","Z","Vx","Vy"])
        st.dataframe(dfz.round(3), use_container_width=True)

        fig2, ax2 = plt.subplots()
        ax2.plot(dfz["Zone"], dfz["Vx"], marker="o", label="X")
        ax2.plot(dfz["Zone"], dfz["Vy"], marker="s", label="Y")
        ax2.set_xlabel("Zone")
        ax2.set_ylabel("Base Shear (kN)")
        ax2.grid(True)
        ax2.legend()
        st.pyplot(fig2)
        fig2.savefig("base_shear_zone.png", dpi=300, bbox_inches="tight")

        base_df = pd.DataFrame(
            st.session_state.base_shear.items(),
            columns=["Parameter","Value"]
        )

        excel_file = "IS1893_2025_Seismic_Output.xlsx"
        with pd.ExcelWriter(excel_file) as writer:
            base_df.to_excel(writer, sheet_name="Base_Shear", index=False)
            dfz.to_excel(writer, sheet_name="Multi_Zone", index=False)

        wb = load_workbook(excel_file)
        ws = wb.create_sheet("Storey_Shear_Plot")
        ws.add_image(XLImage("storey_shear_XY.png"), "A1")
        wb.save(excel_file)

        st.download_button("Download Excel (All Results)", open(excel_file,"rb"), file_name=excel_file)

        pdf_file = "IS1893_2025_Seismic_Output.pdf"
        doc = SimpleDocTemplate(pdf_file)
        styles = getSampleStyleSheet()

        content = [
            Paragraph("IS 1893:2025 – Seismic Analysis Output", styles["Title"]),
            Paragraph("For educational use only<br/>Created by: Vrushali Kamalakar", styles["Normal"]),
            Table([base_df.columns.tolist()] + base_df.values.tolist()),
            Image("storey_shear_XY.png", 400, 300),
            Table([dfz.columns.tolist()] + dfz.round(3).values.tolist()),
            Image("base_shear_zone.png", 400, 300)
        ]

        doc.build(content)

        st.download_button("Download PDF (All Results)", open(pdf_file,"rb"), file_name=pdf_file)

# ==================================================
# FOOTER
# ==================================================
st.markdown("---")
st.info(
    "📘 For educational use only. "
    "Independent verification is mandatory before professional application.\n\n"
    "Created by: Vrushali Kamalakar"
)
