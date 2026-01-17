import streamlit as st
import pandas as pd
import math
import matplotlib.pyplot as plt
import os

from reportlab.platypus import SimpleDocTemplate, Paragraph, Image
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
    "⚠️ For Educational Use Only  \n"
    "Created by: Vrushali Kamalakar"
)

# ==================================================
# SAFE RESET
# ==================================================
if st.button("🔄 Reset all inputs"):
    st.session_state.clear()
    st.rerun()

# ==================================================
# FULL Z TABLE (IS 1893:2025)
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
if "base" not in st.session_state:
    st.session_state.base = None

# ==================================================
# FUNCTIONS
# ==================================================
def A_NH(T):
    return 2.5 if T <= 0.4 else 1.0 / T

def plot_storey(df, fname, title):
    fig, ax = plt.subplots()
    ax.plot(df["Storey Shear"], df["Storey"], marker="o")
    ax.set_xlabel("Storey Shear (kN)")
    ax.set_ylabel("Storey")
    ax.set_title(title)
    ax.grid(True)
    fig.savefig(fname, dpi=300)
    st.pyplot(fig)

def safe_image(path, w=400, h=250):
    if os.path.exists(path):
        return Image(path, w, h)
    return None

# ==================================================
# TABS
# ==================================================
tab1, tab2, tab3 = st.tabs([
    "① Base Shear (Geometry Locked)",
    "② Storey-wise Forces (Editable)",
    "③ Multi-Zone Study"
])

# ==================================================
# TAB 1 – BASE SHEAR (GEOMETRY LOCKED)
# ==================================================
with tab1:
    zone = st.selectbox("Earthquake Zone", list(Z_TABLE.keys()))
    TR = st.selectbox(
        "Return Period TR (years)",
        [75,175,275,475,975,1275,2475,4975,9975]
    )
    Z = Z_TABLE[zone][TR]
    st.info(f"Zone Factor Z = {Z}")

    I = st.number_input("Importance Factor I", value=1.0)
    R = st.number_input("Response Reduction Factor R", value=5.0)
    W = st.number_input("Total Seismic Weight W (kN)", value=10000.0)

    st.markdown("### Global Building Geometry")
    H = st.number_input("Total Height H (m)", min_value=0.1, value=15.0)
    dx = st.number_input("Plan Dimension dx (m)", min_value=0.1, value=10.0)
    dy = st.number_input("Plan Dimension dy (m)", min_value=0.1, value=8.6)

    if st.button("Compute Base Shear"):
        Tx = 0.09 * H / math.sqrt(dx)
        Ty = 0.09 * H / math.sqrt(dy)

        Vx = Z * I * A_NH(Tx) / R * W
        Vy = Z * I * A_NH(Ty) / R * W

        st.session_state.base = {
            "Zone": zone, "TR": TR, "Z": Z,
            "H": H, "dx": dx, "dy": dy,
            "Tx": Tx, "Ty": Ty,
            "Vx": Vx, "Vy": Vy,
            "W": W
        }

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tx (s)", f"{Tx:.3f}")
        c2.metric("Ty (s)", f"{Ty:.3f}")
        c3.metric("VBD,H,X (kN)", f"{Vx:.2f}")
        c4.metric("VBD,H,Y (kN)", f"{Vy:.2f}")

# ==================================================
# TAB 2 – STOREY-WISE FORCES (FULLY EDITABLE)
# ==================================================
with tab2:
    if st.session_state.base is None:
        st.warning("Compute base shear in Tab ① first.")
    else:
        st.info(
            "Storey heights and weights are editable here to study force distribution. "
            "Base shear remains unchanged."
        )

        direction = st.selectbox("Horizontal Direction", ["X","Y"])
        V = st.session_state.base["Vx"] if direction=="X" else st.session_state.base["Vy"]

        N = st.number_input("Number of Storeys", min_value=1, value=5)

        rows = []
        for i in range(1, N+1):
            Wi = st.number_input(
                f"W{i} (kN)",
                min_value=0.0,
                value=float(st.session_state.base["W"]/N),
                key=f"W_{direction}_{i}"
            )
            Hi = st.number_input(
                f"H{i} (m)",
                min_value=0.1,
                value=float(3*i),
                key=f"H_{direction}_{i}"
            )
            rows.append([i, Wi, Hi])

        df = pd.DataFrame(rows, columns=["Storey","Wi","Hi"])
        df["WiHi²"] = df["Wi"] * df["Hi"]**2
        df["Qi"] = df["WiHi²"] / df["WiHi²"].sum() * V
        df["Storey Shear"] = df["Qi"][::-1].cumsum()[::-1]

        st.dataframe(df.round(3), use_container_width=True)

        plot_storey(
            df,
            f"storey_{direction}.png",
            f"Storey Shear Diagram ({direction})"
        )

# ==================================================
# TAB 3 – MULTI-ZONE STUDY
# ==================================================
with tab3:
    zones = st.multiselect(
        "Select Zones",
        list(Z_TABLE.keys()),
        default=["II","III","IV"]
    )

    TR_mz = st.selectbox(
        "Return Period (years)",
        [75,175,275,475,975,1275,2475,4975,9975]
    )

    rows = []
    for z in zones:
        Z = Z_TABLE[z][TR_mz]
        rows.append([z, Z, Z * st.session_state.base["W"] if st.session_state.base else 0])

    dfz = pd.DataFrame(rows, columns=["Zone","Z","Base Shear (kN)"])
    st.dataframe(dfz.round(3), use_container_width=True)

    fig, ax = plt.subplots()
    ax.plot(dfz["Zone"], dfz["Base Shear (kN)"], marker="o")
    ax.set_xlabel("Zone")
    ax.set_ylabel("Base Shear (kN)")
    ax.set_title("Base Shear vs Zone")
    ax.grid(True)
    fig.savefig("multi_zone.png", dpi=300)
    st.pyplot(fig)

# ==================================================
# EXPORT SECTION
# ==================================================
st.markdown("---")
st.header("📤 Export Outputs")

if st.session_state.base is not None:

    excel_file = "IS1893_2025_Output.xlsx"
    with pd.ExcelWriter(excel_file) as writer:
        pd.DataFrame.from_dict(st.session_state.base, orient="index").to_excel(writer, "Base_Shear")

    st.download_button("Download Excel", open(excel_file, "rb"), excel_file)

    pdf_file = "IS1893_2025_Output.pdf"
    doc = SimpleDocTemplate(pdf_file)
    styles = getSampleStyleSheet()

    content = [
        Paragraph("IS 1893:2025 – Seismic Analysis Output", styles["Title"]),
        Paragraph("For Educational Use Only<br/>Created by: Vrushali Kamalakar", styles["Normal"])
    ]

    for img in ["storey_X.png", "storey_Y.png", "multi_zone.png"]:
        pic = safe_image(img)
        if pic:
            content.append(pic)

    doc.build(content)

    st.download_button("Download PDF", open(pdf_file, "rb"), pdf_file)

st.info(
    "📘 This application is intended strictly for educational and academic use. "
    "Independent verification is mandatory for professional design."
)
