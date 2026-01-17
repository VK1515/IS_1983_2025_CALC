
import streamlit as st
import pandas as pd
import math
import tempfile
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

# ---------------- Constants ----------------
ZONE_FACTOR = {"II":0.10,"III":0.16,"IV":0.24,"V":0.36,"VI":0.48}

STRUCTURE_R_T = {
    "RC OMRF": (3.0, 0.075),
    "RC SMRF": (5.0, 0.075),
    "Steel MRF": (4.0, 0.085),
    "Shear Wall": (4.0, 0.09)
}

# ---------------- Functions ----------------
def classify_soil(Vs):
    if Vs >= 760: return "Hard"
    elif Vs >= 360: return "Medium"
    else: return "Soft"

def time_period(h, c):
    return c * h**0.75

def Sa_T(T, soil):
    if soil in ["Hard","Medium"]:
        return 2.5 if T <= 0.4 else 1/T
    else:
        return 3.0 if T <= 0.6 else 1.8/T

# ---------------- Streamlit UI ----------------
st.set_page_config("IS 1893:2025 – Static vs RS", layout="wide")
st.title("IS 1893:2025 – Static vs Response Spectrum Comparison")

structure = st.selectbox("Structure Type", STRUCTURE_R_T.keys())
zone = st.selectbox("Seismic Zone", ZONE_FACTOR.keys())

Vs = st.number_input("Shear Wave Velocity Vs (m/s)", 50.0, 400.0)
h = st.number_input("Building Height h (m)", 3.0, 30.0)
W = st.number_input("Seismic Weight W (kN)", 0.0, 10000.0)

st.subheader("Response Spectrum Inputs")
Sa_RS = st.number_input("Design spectral acceleration from RS analysis (Sa/g)", 0.0, 2.5)

# ---------------- Computation ----------------
if st.button("Compute Comparison"):

    Z = ZONE_FACTOR[zone]
    R, c = STRUCTURE_R_T[structure]
    soil = classify_soil(Vs)
    T = time_period(h, c)

    # Equivalent Static
    Sa_static = Sa_T(T, soil)
    Ah_static = (Z * Sa_static) / R
    V_static = Ah_static * W

    # Response Spectrum
    Ah_rs = (Z * Sa_RS) / R
    V_rs = Ah_rs * W

    # Minimum check
    V_design = max(V_rs, 0.8 * V_static)

    df = pd.DataFrame({
        "Method": ["Equivalent Static", "Response Spectrum", "Design Governing"],
        "Sa/g": [Sa_static, Sa_RS, "-"],
        "Base Shear (kN)": [V_static, V_rs, V_design]
    })

    st.dataframe(df, use_container_width=True)

    # Excel
    excel = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    df.to_excel(excel.name, index=False)
    st.download_button("Download Excel", open(excel.name,"rb"), "static_vs_rs.xlsx")

    # PDF
    pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(pdf.name, pagesize=A4,
                            rightMargin=25*mm,leftMargin=25*mm,
                            topMargin=25*mm,bottomMargin=25*mm)
    styles = getSampleStyleSheet()
    elems = [
        Paragraph("IS 1893:2025 – Static vs Response Spectrum Comparison", styles["Title"]),
        Spacer(1,12),
        Table([df.columns.tolist()] + df.values.tolist())
    ]
    doc.build(elems)
    st.download_button("Download PDF", open(pdf.name,"rb"), "static_vs_rs.pdf")
