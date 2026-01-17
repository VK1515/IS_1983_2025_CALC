import streamlit as st
import pandas as pd
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
# BASIC INPUTS
# --------------------------------------------------
st.markdown("## Basic Seismic Parameters")

Z = st.selectbox("Seismic Zone Factor (Z)", [0.10, 0.16, 0.24, 0.36])
I = st.number_input("Importance Factor (I)", value=1.0, step=0.1)
R = st.number_input("Response Reduction Factor (R)", value=5.0, step=0.5)
site = st.selectbox("Site Class", ["A/B", "C", "D"])

T_H = st.number_input("Horizontal Natural Period TH (s)", value=1.0)
T_V = st.number_input("Vertical Natural Period TV (s)", value=0.4)

W_total = st.number_input("Total Seismic Weight W (kN)", value=10000.0)

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
    if site == "A/B":
        return 0.80
    if site == "C":
        return 0.82
    return 0.85

def gamma_v(TV, site):
    return {"A/B": 1/TV, "C": 1.5/TV, "D": 2.0/TV}[site]

# --------------------------------------------------
# BASE SHEAR CALCULATION
# --------------------------------------------------
A_HD = (Z * I * A_NH(T_H, site)) / R
V_BD_H = A_HD * W_total

A_NV = delta_v(T_V, site) * gamma_v(T_V, site)
A_VD = Z * I * A_NV
V_BD_V = A_VD * W_total

# --------------------------------------------------
# FLOOR-WISE FORCE DISTRIBUTION
# --------------------------------------------------
df["WiHi²"] = df["Wi (kN)"] * df["Hi (m)"]**2

df["QDi,H (kN)"] = (
    df["WiHi²"] / df["WiHi²"].sum()
) * V_BD_H

df["VDi,H (kN)"] = df["QDi,H (kN)"][::-1].cumsum()[::-1]

df["QDi,V (kN)"] = (
    df["Wi (kN)"] / df["Wi (kN)"].sum()
) * V_BD_V

df["VDi,V (kN)"] = df["QDi,V (kN)"][::-1].cumsum()[::-1]

# --------------------------------------------------
# RESULTS DISPLAY
# --------------------------------------------------
st.markdown("## Results Summary")

col1, col2 = st.columns(2)
with col1:
    st.metric("Horizontal Base Shear VBD,H (kN)", f"{V_BD_H:.2f}")
with col2:
    st.metric("Vertical Base Shear VBD,V (kN)", f"{V_BD_V:.2f}")

st.markdown("## Floor-wise Seismic Force Distribution")
st.dataframe(df.round(3), use_container_width=True)

# --------------------------------------------------
# EXPORT TO EXCEL
# --------------------------------------------------
excel_file = "IS1893_2025_Seismic_Forces.xlsx"
df.to_excel(excel_file, index=False)

st.download_button(
    "Download Excel",
    data=open(excel_file, "rb"),
    file_name=excel_file
)

# --------------------------------------------------
# EXPORT TO PDF
# --------------------------------------------------
pdf_file = "IS1893_2025_Seismic_Forces.pdf"
doc = SimpleDocTemplate(pdf_file)
styles = getSampleStyleSheet()

content = [
    Paragraph("IS 1893:2025 – Seismic Force Distribution", styles["Title"]),
    Paragraph(
        f"Horizontal Base Shear = {V_BD_H:.2f} kN<br/>"
        f"Vertical Base Shear = {V_BD_V:.2f} kN",
        styles["Normal"]
    )
]

table_data = [df.columns.tolist()] + df.round(3).values.tolist()
content.append(Table(table_data))

doc.build(content)

st.download_button(
    "Download PDF",
    data=open(pdf_file, "rb"),
    file_name=pdf_file
)

st.info(
    "Compliance Notes:\n"
    "- Horizontal force uses Response Reduction Factor R\n"
    "- Vertical force does NOT use R (IS 1893:2025)\n"
    "- Horizontal distribution uses Wi·Hi²\n"
    "- Vertical distribution uses Wi only"
)
