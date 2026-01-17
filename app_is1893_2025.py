import streamlit as st
import pandas as pd
import math
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Image
from reportlab.lib.styles import getSampleStyleSheet
from openpyxl import load_workbook
from openpyxl.chart import LineChart, Reference
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
    "For educational use only\n"
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
    return {"A/B":0.80,"C":0.82,"D":0.85}[site]

def gamma_v(T, site):
    return {"A/B":1/T,"C":1.5/T,"D":2/T}[site]

# ==================================================
# TABS
# ==================================================
tab1, tab2, tab3 = st.tabs([
    "① Base Shear",
    "② Storey-wise Distribution",
    "③ Multi-Zone Study"
])

# ==================================================
# TAB 1 – BASE SHEAR
# ==================================================
with tab1:
    zone = st.selectbox("Zone", ["II","III","IV","V","VI"])
    TR = st.selectbox("Return Period (years)", [75,175,275,475,975,1275,2475,4975,9975])
    Z = Z_TABLE[zone][TR]

    I = st.number_input("Importance Factor", value=1.0)
    R = st.number_input("Response Reduction Factor", value=5.0)
    site = st.selectbox("Site Class", ["A/B","C","D"])
    W = st.number_input("Total Seismic Weight W (kN)", value=10000.0)

    H = st.number_input("Height H (m)", value=15.0)
    dx = st.number_input("dx (m)", value=10.0)
    dy = st.number_input("dy (m)", value=15.0)
    TV = st.number_input("Vertical Period TV (s)", value=0.4)

    if st.button("Compute Base Shear"):
        Tx = 0.09 * H / math.sqrt(dx)
        Ty = 0.09 * H / math.sqrt(dy)

        Vx = (Z*I*A_NH(Tx,site)/R)*W
        Vy = (Z*I*A_NH(Ty,site)/R)*W
        Vv = Z*I*delta_v(TV,site)*gamma_v(TV,site)*W

        st.session_state.base_shear = {
            "Zone":zone,"TR":TR,"Z":Z,"I":I,"R":R,"Site":site,
            "W":W,"Tx":Tx,"Ty":Ty,"Vx":Vx,"Vy":Vy,"Vv":Vv
        }

        st.success("Base shear computed and locked.")
        st.metric("Tx (s)", f"{Tx:.3f}")
        st.metric("Ty (s)", f"{Ty:.3f}")

# ==================================================
# TAB 3 – MULTI-ZONE STUDY + GRAPH
# ==================================================
with tab3:
    zones = st.multiselect("Zones", ["II","III","IV","V","VI"], default=["II","III","IV","V"])
    TR = st.selectbox("Return Period", [75,175,275,475,975,1275,2475,4975,9975], key="mztr")
    I = st.number_input("I", value=1.0, key="mzi")
    R = st.number_input("R", value=5.0, key="mzr")
    site = st.selectbox("Site", ["A/B","C","D"], key="mzsite")
    W = st.number_input("W (kN)", value=10000.0, key="mzw")
    H = st.number_input("H (m)", value=15.0, key="mzh")
    dx = st.number_input("dx (m)", value=10.0, key="mzdx")
    dy = st.number_input("dy (m)", value=15.0, key="mzdy")

    if st.button("Compute Multi-Zone"):
        Tx = 0.09 * H / math.sqrt(dx)
        Ty = 0.09 * H / math.sqrt(dy)

        rows = []
        for z in zones:
            Z = Z_TABLE[z][TR]
            rows.append([z,Z,(Z*I*A_NH(Tx,site)/R)*W,(Z*I*A_NH(Ty,site)/R)*W])

        dfz = pd.DataFrame(rows, columns=["Zone","Z","Vx","Vy"])
        st.session_state.multi_zone_df = dfz
        st.dataframe(dfz.round(3), use_container_width=True)

        fig, ax = plt.subplots()
        ax.plot(dfz["Zone"], dfz["Vx"], marker="o", label="X")
        ax.plot(dfz["Zone"], dfz["Vy"], marker="s", label="Y")
        ax.set_xlabel("Zone")
        ax.set_ylabel("Base Shear (kN)")
        ax.set_title("Base Shear vs Seismic Zone")
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)

        fig.savefig("base_shear_zone_plot.png", dpi=300)

# ==================================================
# EXPORT SECTION
# ==================================================
if st.session_state.multi_zone_df is not None:

    # -------- EXCEL EXPORT --------
    excel_file = "IS1893_2025_Seismic_Forces_With_Graph.xlsx"
    with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
        st.session_state.multi_zone_df.to_excel(writer, sheet_name="Multi_Zone", index=False)

    wb = load_workbook(excel_file)
    ws = wb["Multi_Zone"]

    chart = LineChart()
    chart.title = "Base Shear vs Seismic Zone"
    chart.y_axis.title = "Base Shear (kN)"
    chart.x_axis.title = "Zone"

    data = Reference(ws, min_col=3, min_row=1, max_col=4, max_row=ws.max_row)
    cats = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    ws.add_chart(chart, "G2")

    wb.save(excel_file)

    st.download_button("Download Excel (with graph)", open(excel_file,"rb"), file_name=excel_file)

    # -------- PDF EXPORT --------
    pdf_file = "IS1893_2025_Seismic_Forces_With_Graph.pdf"
    doc = SimpleDocTemplate(pdf_file)
    styles = getSampleStyleSheet()

    content = [
        Paragraph("IS 1893:2025 – Seismic Force Study", styles["Title"]),
        Paragraph("For educational use only<br/>Created by Vrushali Kamalakar", styles["Normal"]),
        Table([st.session_state.multi_zone_df.columns.tolist()] +
              st.session_state.multi_zone_df.round(3).values.tolist()),
        Image("base_shear_zone_plot.png", width=400, height=250)
    ]

    doc.build(content)

    st.download_button("Download PDF (with graph)", open(pdf_file,"rb"), file_name=pdf_file)
