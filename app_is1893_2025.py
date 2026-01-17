import streamlit as st
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import tempfile
import math

# -------------------------------------------------
# CONSTANTS (IS 1893:2025 aligned)
# -------------------------------------------------

ZONE_FACTOR = {
    "II": 0.10,
    "III": 0.16,
    "IV": 0.24,
    "V": 0.36,
    "VI": 0.48
}

STRUCTURE_R_T = {
    "RC Ordinary Moment Frame (OMRF)": (3.0, 0.075),
    "RC Special Moment Resisting Frame (SMRF)": (5.0, 0.075),
    "Steel Moment Resisting Frame": (4.0, 0.085),
    "Shear Wall System": (4.0, 0.09)
}

# -------------------------------------------------
# FUNCTIONS
# -------------------------------------------------

def classify_soil(Vs):
    if Vs >= 760:
        return "Hard Soil"
    elif Vs >= 360:
        return "Medium Soil"
    else:
        return "Soft Soil"


def time_period(h, coeff):
    return coeff * (h ** 0.75)


def spectral_acceleration(T, soil):
    if soil in ["Hard Soil", "Medium Soil"]:
        return 2.5 if T <= 0.4 else 1.0 / T
    else:
        return 3.0 if T <= 0.6 else 1.8 / T


# -------------------------------------------------
# STREAMLIT UI
# -------------------------------------------------

st.set_page_config(page_title="IS 1893:2025 Seismic Forces", layout="wide")
st.title("IS 1893 (Part 1):2025 – Seismic Force Calculator")

st.markdown("**Equivalent Static Method with Storey-wise Distribution**")

structure = st.selectbox("Type of Structure", STRUCTURE_R_T.keys())
zone = st.selectbox("Seismic Zone", ZONE_FACTOR.keys())

Vs = st.number_input("Shear Wave Velocity Vs (m/s)", min_value=50.0, value=400.0, step=10.0)
h_total = st.number_input("Total Building Height h (m)", min_value=3.0, value=30.0, step=1.0)
W_total = st.number_input("Total Seismic Weight W (kN)", min_value=0.0, value=10000.0, step=500.0)

VBD_V = st.number_input("Design Vertical Base Force VBD,V (kN)", value=0.30 * W_total)

# -------------------------------------------------
# STOREY INPUTS
# -------------------------------------------------

st.subheader("Storey-wise Input Data")

N = st.number_input("Number of Storeys", min_value=1, value=5, step=1)

storey_heights = []
storey_weights = []

for i in range(int(N)):
    c1, c2 = st.columns(2)
    with c1:
        Hi = st.number_input(f"Height of Storey {i+1} from base (m)", value=(i+1)*(h_total/N))
    with c2:
        Wi = st.number_input(f"Seismic Weight at Storey {i+1} (kN)", value=W_total/N)
    storey_heights.append(Hi)
    storey_weights.append(Wi)

# -------------------------------------------------
# COMPUTE
# -------------------------------------------------

if st.button("Compute Seismic Forces"):

    # ---- Base shear calculation (unchanged) ----
    Z = ZONE_FACTOR[zone]
    R, coeff = STRUCTURE_R_T[structure]
    soil = classify_soil(Vs)
    T = time_period(h_total, coeff)
    ANH = spectral_acceleration(T, soil)

    AHD = (Z * 1.0 * ANH) / R
    VBD_H = AHD * W_total

    # ---- Horizontal force distribution ----
    denom = sum(storey_weights[i] * storey_heights[i]**2 for i in range(N))
    QD_H = [(storey_weights[i]*storey_heights[i]**2/denom)*VBD_H for i in range(N)]

    VD_H = []
    cum = 0.0
    for i in reversed(range(N)):
        cum += QD_H[i]
        VD_H.insert(0, cum)

    # ---- Vertical force distribution ----
    total_W = sum(storey_weights)
    QD_V = [(storey_weights[i]/total_W)*VBD_V for i in range(N)]

    VD_V = []
    cum_v = 0.0
    for i in reversed(range(N)):
        cum_v += QD_V[i]
        VD_V.insert(0, cum_v)

    # ---- Interaction (SRSS) ----
    V_combined = [
        math.sqrt(VD_H[i]**2 + VD_V[i]**2)
        for i in range(N)
    ]

    # -------------------------------------------------
    # RESULTS TABLE
    # -------------------------------------------------

    df = pd.DataFrame({
        "Storey": range(1, N+1),
        "Height H (m)": storey_heights,
        "Weight W (kN)": storey_weights,
        "Q_Di,H (kN)": QD_H,
        "V_Di,H (kN)": VD_H,
        "Q_Di,V (kN)": QD_V,
        "V_Di,V (kN)": VD_V,
        "Combined Shear (kN)": V_combined
    })

    st.subheader("Storey-wise Seismic Forces")
    st.dataframe(df, use_container_width=True)

    # -------------------------------------------------
    # EXCEL EXPORT
    # -------------------------------------------------

    excel_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    df.to_excel(excel_file.name, index=False)

    with open(excel_file.name, "rb") as f:
        st.download_button(
            "Download Excel Results",
            f,
            file_name="IS1893_2025_Storey_Forces.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # -------------------------------------------------
    # PDF REPORT
    # -------------------------------------------------

    def generate_pdf():
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        doc = SimpleDocTemplate(tmp.name, pagesize=A4,
                                rightMargin=25*mm, leftMargin=25*mm,
                                topMargin=25*mm, bottomMargin=25*mm)
        styles = getSampleStyleSheet()
        elems = []

        elems.append(Paragraph("<b>IS 1893 (Part 1):2025 – Seismic Force Report</b>", styles["Title"]))
        elems.append(Spacer(1, 12))

        table_data = [df.columns.tolist()] + df.round(2).values.tolist()
        elems.append(Table(table_data, repeatRows=1))

        elems.append(Spacer(1, 12))
        elems.append(Paragraph(
            "Horizontal and vertical seismic forces distributed as per IS 1893. "
            "Combined storey shear computed using SRSS interaction.",
            styles["Italic"]
        ))

        doc.build(elems)
        return tmp.name

    pdf_path = generate_pdf()

    with open(pdf_path, "rb") as f:
        st.download_button(
            "Download PDF Report",
            f,
            file_name="IS1893_2025_Seismic_Report.pdf",
            mime="application/pdf"
        )

# -------------------------------------------------
# FOOTNOTE
# -------------------------------------------------
st.caption(
    "Equivalent static method as per IS 1893 (Part 1):2025. "
    "Dynamic analysis required for irregular or tall structures."
)
