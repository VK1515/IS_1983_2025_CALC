import streamlit as st
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


def calculate(zone, structure, Vs, h, W, I=1.0):
    Z = ZONE_FACTOR[zone]
    R, coeff = STRUCTURE_R_T[structure]

    soil = classify_soil(Vs)
    T = time_period(h, coeff)
    ANH = spectral_acceleration(T, soil)

    AHD = (Z * I * ANH) / R
    VBD = AHD * W

    return soil, Z, R, T, ANH, AHD, VBD


# -------------------------------------------------
# STREAMLIT UI
# -------------------------------------------------

st.set_page_config(page_title="IS 1893:2025 Base Shear", layout="centered")

st.title("IS 1893 (Part 1):2025 – Base Shear Calculator")

st.markdown("**Equivalent Static Method with Automatic Period & Spectrum**")

structure = st.selectbox("Type of Structure", STRUCTURE_R_T.keys())
zone = st.selectbox("Seismic Zone", ZONE_FACTOR.keys())

Vs = st.number_input("Shear Wave Velocity Vs (m/s)", min_value=50.0, value=400.0, step=10.0)
h = st.number_input("Building Height h (m)", min_value=3.0, value=30.0, step=1.0)
W = st.number_input("Seismic Weight W (kN)", min_value=0.0, value=10000.0, step=500.0)

# -------------------------------------------------
# COMPUTE
# -------------------------------------------------

if st.button("Compute Base Shear"):

    soil, Z, R, T, ANH, AHD, VBD = calculate(zone, structure, Vs, h, W)

    st.subheader("Derived Parameters")
    st.write(f"Soil Classification: **{soil}**")
    st.write(f"Fundamental Time Period T = **{T:.3f} s**")
    st.write(f"Spectral Acceleration AₙH(T) = **{ANH:.3f}**")

    st.subheader("Design Results")
    st.success(f"Design Acceleration Coefficient AHD = {AHD:.4f}")
    st.success(f"Design Base Shear VBD,H = {VBD:.2f} kN")

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

        elems.append(Paragraph("<b>IS 1893 (Part 1):2025 – Base Shear Report</b>", styles["Title"]))
        elems.append(Spacer(1, 12))

        data = [
            ["Parameter", "Value"],
            ["Structure Type", structure],
            ["Seismic Zone", zone],
            ["Zone Factor Z", Z],
            ["Soil Type", soil],
            ["Shear Wave Velocity Vs (m/s)", Vs],
            ["Building Height h (m)", h],
            ["Time Period T (s)", round(T, 3)],
            ["Response Reduction Factor R", R],
            ["Spectral Acceleration AₙH(T)", round(ANH, 3)],
            ["Seismic Weight W (kN)", W],
            ["Design Base Shear VBD,H (kN)", round(VBD, 2)]
        ]

        elems.append(Table(data, colWidths=[70*mm, 80*mm]))
        elems.append(Spacer(1, 15))

        elems.append(Paragraph("Base shear calculated using equivalent static method "
                               "as per IS 1893 (Part 1):2025.", styles["Italic"]))

        doc.build(elems)
        return tmp.name

    pdf_path = generate_pdf()

    with open(pdf_path, "rb") as f:
        st.download_button(
            "Download PDF Report",
            f,
            file_name="IS1893_2025_Base_Shear_Report.pdf",
            mime="application/pdf"
        )

# -------------------------------------------------
# FOOTNOTE
# -------------------------------------------------
st.caption(
    "Note: Applicable for regular buildings using equivalent static method. "
    "Dynamic analysis is mandatory for irregular or tall structures."
)
