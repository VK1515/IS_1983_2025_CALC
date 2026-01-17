import streamlit as st
import pandas as pd
import math
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Image
from reportlab.lib.styles import getSampleStyleSheet
from openpyxl import load_workbook
from openpyxl.chart import LineChart, Reference

# ==================================================
# RESET BUTTON (FIXES ALL STUCK INPUT ERRORS)
# ==================================================
if st.button("🔄 Reset all inputs"):
    st.session_state.clear()
    st.experimental_rerun()

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(page_title="IS 1893:2025 Seismic Calculator", layout="wide")

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
    "VI": {75:0.300,175:0.375,275:0.450,475:0.500},
    "V":  {75:0.200,175:0.250,275:0.300,475:0.333},
    "IV": {75:0.140,175:0.175,275:0.210,475:0.233},
    "III":{75:0.0625,175:0.085,275:0.100,475:0.125},
    "II": {75:0.0375,175:0.050,275:0.060,475:0.075}
}

# ==================================================
# SESSION STATE
# ==================================================
for k in ["base","storey","multi"]:
    if k not in st.session_state:
        st.session_state[k] = None

# ==================================================
# FUNCTIONS
# ==================================================
def A_NH(T):
    return 2.5 if T <= 0.4 else 1/T

def plot_storey(df, col, title, fname):
    fig, ax = plt.subplots()
    ax.plot(df[col], df["Storey"], marker="o")
    ax.set_xlabel("Shear (kN)")
    ax.set_ylabel("Storey")
    ax.set_title(title)
    ax.grid(True)
    fig.savefig(fname, dpi=300)
    st.pyplot(fig)

# ==================================================
# TABS
# ==================================================
tab1, tab2, tab3 = st.tabs([
    "① Base Shear",
    "② Storey Forces & Diagrams",
    "③ Multi-Zone Study & Export"
])

# ==================================================
# TAB 1 – BASE SHEAR
# ==================================================
with tab1:
    zone = st.selectbox("Zone", list(Z_TABLE.keys()))
    TR = st.selectbox("Return Period (years)", list(Z_TABLE[zone].keys()))
    Z = Z_TABLE[zone][TR]

    I = st.number_input("Importance Factor I", 1.0)
    R = st.number_input("Response Reduction Factor R", 5.0)
    W = st.number_input("Total Seismic Weight W (kN)", 10000.0)

    H = st.number_input("Total Height H (m)", min_value=0.1, value=15.0, key="H")
    dx = st.number_input("Plan Dimension dx (m)", min_value=0.1, value=10.0, key="dx")
    dy = st.number_input("Plan Dimension dy (m)", min_value=0.1, value=8.6, key="dy")

    if st.button("Compute Base Shear"):
        Tx = 0.09 * H / math.sqrt(dx)
        Ty = 0.09 * H / math.sqrt(dy)

        Vx = Z * I * A_NH(Tx) / R * W
        Vy = Z * I * A_NH(Ty) / R * W

        st.session_state.base = {
            "Zone":zone,"TR":TR,"Z":Z,
            "Tx":Tx,"Ty":Ty,
            "Vx":Vx,"Vy":Vy
        }

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Tx (s)", f"{Tx:.3f}")
        c2.metric("Ty (s)", f"{Ty:.3f}")
        c3.metric("Vx (kN)", f"{Vx:.2f}")
        c4.metric("Vy (kN)", f"{Vy:.2f}")

# ==================================================
# TAB 2 – STOREY FORCES + DIAGRAMS
# ==================================================
with tab2:
    if st.session_state.base is None:
        st.warning("Compute base shear first.")
    else:
        direction = st.selectbox("Direction", ["X","Y"])
        V = st.session_state.base["Vx"] if direction=="X" else st.session_state.base["Vy"]

        N = st.number_input("Number of Storeys", min_value=1, value=5)

        rows=[]
        for i in range(1, N+1):
            Wi = st.number_input(
                f"W{i} (kN)", 2000.0, key=f"W_{direction}_{i}"
            )
            Hi = st.number_input(
                f"H{i} (m)", min_value=0.1, value=3*i, key=f"H_{direction}_{i}"
            )
            rows.append([i,Wi,Hi])

        df = pd.DataFrame(rows, columns=["Storey","Wi","Hi"])
        df["WiHi²"] = df["Wi"]*df["Hi"]**2
        df["Qi"] = df["WiHi²"]/df["WiHi²"].sum()*V
        df["Storey Shear"] = df["Qi"][::-1].cumsum()[::-1]

        st.session_state.storey = df
        st.dataframe(df.round(3), use_container_width=True)

        plot_storey(df,"Storey Shear",
            f"Storey Shear Diagram ({direction})",
            f"storey_{direction}.png"
        )

# ==================================================
# TAB 3 – MULTI-ZONE STUDY + EXPORT
# ==================================================
with tab3:
    zones = st.multiselect("Zones", list(Z_TABLE.keys()), default=["II","III","IV"])
    TR = st.selectbox("Return Period", [75,175,275,475], key="mzTR")

    rows=[]
    for z in zones:
        Z = Z_TABLE[z][TR]
        rows.append([z,Z,Z*10000])

    dfz = pd.DataFrame(rows, columns=["Zone","Z","Base Shear (kN)"])
    st.session_state.multi = dfz

    st.dataframe(dfz.round(3), use_container_width=True)

    fig, ax = plt.subplots()
    ax.plot(dfz["Zone"], dfz["Base Shear (kN)"], marker="o")
    ax.set_title("Base Shear vs Zone")
    ax.grid(True)
    fig.savefig("multi_zone.png", dpi=300)
    st.pyplot(fig)

# ==================================================
# EXPORT ALL OUTPUTS
# ==================================================
st.header("📤 Export ALL Outputs (All Tabs)")

if st.session_state.storey is not None:

    excel="IS1893_2025_FULL_OUTPUT.xlsx"
    with pd.ExcelWriter(excel, engine="openpyxl") as w:
        pd.DataFrame.from_dict(st.session_state.base,orient="index").to_excel(w,"Base_Shear")
        st.session_state.storey.to_excel(w,"Storey_Forces",index=False)
        st.session_state.multi.to_excel(w,"Multi_Zone",index=False)

    st.download_button("Download Excel (ALL OUTPUTS)", open(excel,"rb"), excel)

    pdf="IS1893_2025_FULL_OUTPUT.pdf"
    doc=SimpleDocTemplate(pdf)
    styles=getSampleStyleSheet()

    content=[
        Paragraph("IS 1893:2025 – Seismic Analysis Output", styles["Title"]),
        Paragraph("For Educational Use Only<br/>Created by: Vrushali Kamalakar", styles["Normal"]),
        Image("storey_X.png",400,250),
        Image("storey_Y.png",400,250),
        Image("multi_zone.png",400,250)
    ]

    doc.build(content)

    st.download_button("Download PDF (ALL OUTPUTS)", open(pdf,"rb"), pdf)
