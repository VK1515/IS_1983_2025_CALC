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
def classify_site(Vs):
    if Vs >= 760:
        return "A"
    elif Vs >= 360:
        return "C"
    else:
        return "D"

def time_period(h, c):
    return c * h**0.75

def A_NH(T, site):
    if site in ["A","B"]:
        return 2.5 if T <= 0.4 else 1/T
    elif site == "C":
        return 2.5 if T <= 0.6 else 1.5/T
    else:
        return 2.5 if T <= 0.8 else 2.0/T

def delta_v(Tv):
    return 0.67 if Tv > 0.10 else 0.80

def A_NV(Tv, site):
    dv = delta_v(Tv)
    if site in ["A","B"]:
        Sa = 2.5 if Tv <= 0.4 else 1/Tv
    elif site == "C":
        Sa = 2.5 if Tv <= 0.6 else 1.5/Tv
    else:
        Sa = 2.5 if Tv <= 0.8 else 2.0/Tv
    return dv * Sa

# -------------------------------------------------
# STREAMLIT UI
# -------------------------------------------------
st.set_page_config("IS 1893 Seismic Forces", layout="wide")
st.title("IS 1893:2025 – Seismic Force Calculator")

st.markdown("**Equivalent Static Method with Horizontal & Vertical Effects**")

# ---------------- Inputs ----------------
structure = st.selectbox("Structure Type", STRUCTURE_R_T.keys())
zone = st.selectbox("Seismic Zone", ZONE_FACTOR.keys())

Vs = st.number_input("Shear Wave Velocity Vs (m/s)", 50.0, 400.0)
h_total = st.number_input("Total Building Height h (m)", 3.0, 30.0)
W_total = st.number_input("Total Seismic Weight W (kN)", 0.0, 10000.0)

VBD_V_factor = st.number_input("Vertical seismic weight factor (×W)", value=1.0)

# ---------------- Storey data ----------------
st.subheader("Storey-wise Data")
N = st.number_input("Number of Storeys", 1, 25, 5)

H, W = [], []
for i in range(N):
    H.append(st.number_input(f"Height of Storey {i+1} from base (m)", value=(i+1)*h_total/N))
    W.append(st.number_input(f"Weight of Storey {i+1} (kN)", value=W_total/N))

# -------------------------------------------------
# COMPUTE
# -------------------------------------------------
if st.button("Compute Seismic Forces"):

    Z = ZONE_FACTOR[zone]
    R, c = STRUCTURE_R_T[structure]
    site = classify_site(Vs)

    # ---- Horizontal base shear ----
    T = time_period(h_total, c)
    ANH = A_NH(T, site)
    AHD = (Z * ANH) / R
    VBD_H = AHD * W_total

    # ---- Vertical base shear ----
    Tv = 0.4
    ANV = A_NV(Tv, site)
    VBD_V = Z * ANV * W_total * VBD_V_factor

    # ---- Horizontal storey forces ----
    denom = sum(W[i]*H[i]**2 for i in range(N))
    QH = [(W[i]*H[i]**2/denom)*VBD_H for i in range(N)]

    VH, cum = [], 0.0
    for i in reversed(range(N)):
        cum += QH[i]
        VH.insert(0, cum)

    # ---- Vertical storey forces ----
    QV = [(W[i]/sum(W))*VBD_V for i in range(N)]

    VV, cum = [], 0.0
    for i in reversed(range(N)):
        cum += QV[i]
        VV.insert(0, cum)

    # ---- Interaction ----
    V_comb = [math.sqrt(VH[i]**2 + VV[i]**2) for i in range(N)]

    # ---- Results table ----
    df = pd.DataFrame({
        "Storey": range(1, N+1),
        "Height (m)": H,
        "Weight (kN)": W,
        "Q_Di,H (kN)": QH,
        "V_Di,H (kN)": VH,
        "Q_Di,V (kN)": QV,
        "V_Di,V (kN)": VV,
        "Combined Shear (kN)": V_comb
    })

    st.subheader("Storey-wise Seismic Forces")
    st.dataframe(df, use_container_width=True)

    st.subheader("Base Shear Summary")
    st.success(f"VBD,H = {VBD_H:.2f} kN")
    st.success(f"VBD,V = {VBD_V:.2f} kN")

    # ---- Excel export ----
    excel = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    df.to_excel(excel.name, index=False)
    st.download_button("Download Excel",
                       open(excel.name,"rb"),
                       "storey_seismic_forces.xlsx")

    # ---- PDF export ----
    pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(pdf.name, pagesize=A4,
                            rightMargin=25*mm,leftMargin=25*mm,
                            topMargin=25*mm,bottomMargin=25*mm)
    styles = getSampleStyleSheet()
    elems = [
        Paragraph("IS 1893:2025 – Seismic Force Report", styles["Title"]),
        Spacer(1,12),
        Table([df.columns.tolist()] + df.round(2).values.tolist())
    ]
    doc.build(elems)

    st.download_button("Download PDF Report",
                       open(pdf.name,"rb"),
                       "seismic_force_report.pdf")

# -------------------------------------------------
st.caption(
    "Calculations follow IS 1893 (Part 1):2025 equivalent static method "
    "including vertical seismic effects."
)
