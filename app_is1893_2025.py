import streamlit as st
import pandas as pd
import math
import tempfile
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

# -------------------------------------------------
# CONSTANTS
# -------------------------------------------------
ZONE_FACTOR = {"II":0.10,"III":0.16,"IV":0.24,"V":0.36,"VI":0.48}

STRUCTURE_R_T = {
    "RC OMRF": (3.0, 0.075),
    "RC SMRF": (5.0, 0.075),
    "Steel MRF": (4.0, 0.085),
    "Shear Wall": (4.0, 0.09)
}

# -------------------------------------------------
# FUNCTIONS
# -------------------------------------------------
def classify_soil(Vs):
    if Vs >= 760: return "Hard"
    elif Vs >= 360: return "Medium"
    else: return "Soft"

def time_period(h, c):
    return c * h**0.75

def Sa_static(T, soil):
    if soil in ["Hard","Medium"]:
        return 2.5 if T <= 0.4 else 1/T
    else:
        return 3.0 if T <= 0.6 else 1.8/T

# -------------------------------------------------
# UI
# -------------------------------------------------
st.set_page_config("IS 1893 Seismic Forces", layout="wide")
st.title("IS 1893 – Seismic Force Calculator with Storey Distribution")

structure = st.selectbox("Structure Type", STRUCTURE_R_T.keys())
zone = st.selectbox("Seismic Zone", ZONE_FACTOR.keys())

Vs = st.number_input("Shear Wave Velocity Vs (m/s)", 50.0, 400.0)
h_total = st.number_input("Total Height h (m)", 3.0, 30.0)
W_total = st.number_input("Total Seismic Weight W (kN)", 0.0, 10000.0)

VBD_V = st.number_input("Vertical Base Force VBD,V (kN)", value=0.3*W_total)

# -------------------------------------------------
# STOREY INPUTS
# -------------------------------------------------
N = st.number_input("Number of Storeys", 1, 20, 5)

H, W = [], []
for i in range(N):
    H.append(st.number_input(f"Height of storey {i+1} (m)", value=(i+1)*h_total/N))
    W.append(st.number_input(f"Weight of storey {i+1} (kN)", value=W_total/N))

# -------------------------------------------------
# RESPONSE SPECTRUM INPUT
# -------------------------------------------------
Sa_RS = st.number_input("Sa/g from Response Spectrum Analysis", 0.0, 3.0)

# -------------------------------------------------
# MEMBER DISTRIBUTION INPUT
# -------------------------------------------------
diaphragm = st.selectbox("Diaphragm Type", ["Rigid","Flexible"])
member_props = st.text_input(
    "Member stiffness (Rigid) OR tributary areas (Flexible), comma-separated",
    "30000,20000,10000"
)

# -------------------------------------------------
# COMPUTE
# -------------------------------------------------
if st.button("Compute Seismic Forces"):

    Z = ZONE_FACTOR[zone]
    R, c = STRUCTURE_R_T[structure]
    soil = classify_soil(Vs)
    T = time_period(h_total, c)

    Sa_eq = Sa_static(T, soil)
    Ah_eq = (Z * Sa_eq) / R
    V_static = Ah_eq * W_total

    Ah_rs = (Z * Sa_RS) / R
    V_rs = Ah_rs * W_total

    V_design = max(V_rs, 0.8 * V_static)

    # ---- Horizontal storey forces ----
    denom = sum(W[i]*H[i]**2 for i in range(N))
    QH = [(W[i]*H[i]**2/denom)*V_design for i in range(N)]

    VH, csum = [], 0
    for i in reversed(range(N)):
        csum += QH[i]
        VH.insert(0, csum)

    # ---- Vertical storey forces ----
    QV = [(W[i]/sum(W))*VBD_V for i in range(N)]
    VV, csum = [], 0
    for i in reversed(range(N)):
        csum += QV[i]
        VV.insert(0, csum)

    # ---- Member distribution (example at Storey 1) ----
    props = [float(x) for x in member_props.split(",")]
    if diaphragm == "Rigid":
        member_forces = [(k/sum(props))*VH[0] for k in props]
    else:
        member_forces = [(a/sum(props))*VH[0] for a in props]

    # ---- Results table ----
    df = pd.DataFrame({
        "Storey": range(1,N+1),
        "Height (m)": H,
        "Weight (kN)": W,
        "Q_Di,H (kN)": QH,
        "V_Di,H (kN)": VH,
        "Q_Di,V (kN)": QV,
        "V_Di,V (kN)": VV
    })

    st.subheader("Storey-wise Seismic Forces")
    st.dataframe(df, use_container_width=True)

    st.subheader("Response Spectrum vs Static")
    st.write(f"V_static = {V_static:.2f} kN")
    st.write(f"V_RS = {V_rs:.2f} kN")
    st.success(f"Design Base Shear = {V_design:.2f} kN")

    st.subheader("Member-level Forces at Storey 1")
    st.write(member_forces)

    # ---- Excel export ----
    excel = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    df.to_excel(excel.name, index=False)
    st.download_button("Download Excel Storey Table",
                       open(excel.name,"rb"),
                       "storey_forces.xlsx")

    # ---- PDF ----
    pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(pdf.name, pagesize=A4,
                            rightMargin=25*mm,leftMargin=25*mm,
                            topMargin=25*mm,bottomMargin=25*mm)
    styles = getSampleStyleSheet()
    elems = [
        Paragraph("IS 1893 – Seismic Force Report", styles["Title"]),
        Spacer(1,12),
        Table([df.columns.tolist()] + df.round(2).values.tolist())
    ]
    doc.build(elems)
    st.download_button("Download PDF Report",
                       open(pdf.name,"rb"),
                       "seismic_report.pdf")
