import streamlit as st
import pandas as pd
import math
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table
from reportlab.lib.styles import getSampleStyleSheet

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="IS 1893:2025 Seismic Force Calculator",
    layout="wide"
)

st.title("IS 1893:2025 – Horizontal & Vertical Seismic Forces")
st.subheader("Equivalent Static Method (Clauses 6, 8 & 8.2.4)")

# --------------------------------------------------
# ZONE FACTOR TABLE (IS 1893:2025)
# --------------------------------------------------
Z_TABLE = {
    "VI": {
        75: 0.300, 175: 0.375, 275: 0.450, 475: 0.500,
        975: 0.600, 1275: 0.625, 2475: 0.750, 4975: 0.940, 9975: 1.125
    },
    "V": {
        75: 0.200, 175: 0.250, 275: 0.300, 475: 0.333,
        975: 0.400, 1275: 0.4167, 2475: 0.500, 4975: 0.625, 9975: 0.750
    },
    "IV": {
        75: 0.140, 175: 0.175, 275: 0.210, 475: 0.233,
        975: 0.280, 1275: 0.2917, 2475: 0.350, 4975: 0.440, 9975: 0.525
    },
    "III": {
        75: 0.0625, 175: 0.085, 275: 0.100, 475: 0.125,
        975: 0.167, 1275: 0.1875, 2475: 0.250, 4975: 0.333, 9975: 0.450
    },
    "II": {
        75: 0.0375, 175: 0.050, 275: 0.060, 475: 0.075,
        975: 0.100, 1275: 0.1125, 2475: 0.150, 4975: 0.200, 9975: 0.270
    }
}

# --------------------------------------------------
# BASIC SEISMIC INPUTS
# --------------------------------------------------
st.markdown("## Design Earthquake Parameters")

zone = st.selectbox(
    "Earthquake Zone",
    ["II", "III", "IV", "V", "VI"]
)

return_period = st.selectbox(
    "Return Period TR (years)",
    [75, 175, 275, 475, 975, 1275, 2475, 4975, 9975]
)

Z = Z_TABLE[zone][return_period]

st.info(f"Selected Design Zone Factor Z = {Z}")

I = st.number_input("Importance Factor (I)", value=1.0, step=0.1)
R = st.number_input("Response Reduction Factor (R)", value=5.0, step=0.5)
site = st.selectbox("Site Class", ["A/B", "C", "D"])

W_total = st.number_input("Total Seismic Weight W (kN)", value=10000.0)

# --------------------------------------------------
# APPROXIMATE FUNDAMENTAL PERIOD
# --------------------------------------------------
st.markdown("## Approximate Fundamental Period for Horizontal Action")

use_Ta = st.checkbox(
    "Use Ta = 0.09 H / √d (IS 1893:2025)",
    value=True
)

H_total = st.number_input("Total Building Height H (m)", value=15.0)
d_base = st.number_input("Base Dimension d (m)", value=10.0)

T_H_manual = st.number_input(
    "Manual Horizontal Period TH (s)",
    value=1.0
)

T_V = st.number_input("Vertical Natural Period TV (s)", value=0.4)

T_H_used = 0.09 * H_total / math.sqrt(d_base) if use_Ta else T_H_manual

# --------------------------------------------------
# STOREY DATA
# --------------------------------------------------
st.markdown("## Storey Data")

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

# --------------------------------------------------
# SPECTRAL FUNCTIONS
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
    return {"A/B": 0.80, "C": 0.82, "D": 0.85}[site]

def gamma_v(TV, site):
    return {"A/B": 1/TV, "C": 1.5/TV, "D": 2.0/TV}[site]

# --------------------------------------------------
# BASE SHEAR
# --------------------------------------------------
A_HD = (Z * I * A_NH(T_H_used, site)) / R
V_BD_H = A_HD * W_total

A_NV = delta_v(T_V, site) * gamma_v(T_V, site)
V_BD_V = Z * I * A_NV * W_total

# --------------------------------------------------
# FLOOR-WISE DISTRIBUTION
# --------------------------------------------------
df["WiHi²"] = df["Wi (kN)"] * df["Hi (m)"]**2

df["QDi,H (kN)"] = df["WiHi²"] / df["WiHi²"].sum() * V_BD_H
df["VDi,H (kN)"] = df["QDi,H (kN)"][::-1].cumsum()[::-1]

df["QDi,V (kN)"] = df["Wi (kN)"] / df["Wi (kN)"].sum() * V_BD_V
df["VDi,V (kN)"] = df["QDi,V (kN)"][::-1].cumsum()[::-1]

# --------------------------------------------------
# RESULTS
# --------------------------------------------------
st.markdown("## Results Summary")

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Z (from Zone & TR)", Z)
with c2:
    st.metric("Horizontal Base Shear (kN)", f"{V_BD_H:.2f}")
with c3:
    st.metric("Vertical Base Shear (kN)", f"{V_BD_V:.2f}")

st.markdown("## Floor-wise Seismic Force Distribution")
st.dataframe(df.round(3), use_container_width=True)

# --------------------------------------------------
# EXPORT
# --------------------------------------------------
excel_file = "IS1893_2025_Seismic_Forces.xlsx"
df.to_excel(excel_file, index=False)

st.download_button(
    "Download Excel",
    data=open(excel_file, "rb"),
    file_name=excel_file
)

pdf_file = "IS1893_2025_Seismic_Forces.pdf"
doc = SimpleDocTemplate(pdf_file)
styles = getSampleStyleSheet()

content = [
    Paragraph("IS 1893:2025 – Seismic Force Distribution", styles["Title"]),
    Paragraph(
        f"Zone = {zone}<br/>"
        f"Return Period TR = {return_period} years<br/>"
        f"Zone Factor Z = {Z}<br/>"
        f"Horizontal Base Shear = {V_BD_H:.2f} kN<br/>"
        f"Vertical Base Shear = {V_BD_V:.2f} kN",
        styles["Normal"]
    ),
    Table([df.columns.tolist()] + df.round(3).values.tolist())
]

doc.build(content)

st.download_button(
    "Download PDF",
    data=open(pdf_file, "rb"),
    file_name=pdf_file
)

st.info(
    "IS 1893:2025 Compliance:\n"
    "- Z selected using Zone + Return Period table\n"
    "- Horizontal action uses R\n"
    "- Vertical action independent of R\n"
    "- Horizontal distribution: Wi·Hi²\n"
    "- Vertical distribution: Wi"
)
