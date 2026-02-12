import math
import pandas as pd
import streamlit as st
from calculator import calculate, make_sphere_fig
from datetime import datetime
from datetime import datetime
from zoneinfo import ZoneInfo


st.set_page_config(
    page_title="LED Sphere Spec Calculator",
    page_icon="yenrich.png",
    layout="wide",
)

# =============================
# Sidebar – Core Inputs
# =============================
with st.sidebar:
    st.header("Input Parameters")
    st.caption("(All fields are required.)")

    project_name = st.text_input(
        "Project Name",
        value=""
    )

    diameter = st.number_input(
        "Diameter (mm)",
        value=3000.0,
        step=1.0,
        format="%.1f"
    )

    fov_h = st.number_input(
        "FOV Horizontal (deg)",
        value=180.00,
        step=0.01,
        format="%.2f"
    )

    fov_v_n = st.number_input(
        "FOV North (deg)",
        value=67.50,
        step=0.01,
        format="%.2f"
    )

    fov_v_s = st.number_input(
        "FOV South (deg)",
        value=33.75,
        step=0.01,
        format="%.2f"
    )

    resolution_h = st.number_input(
        "Resolution Horizontal (px)",
        value=3840,
        step=1
    )

    luminance = st.number_input(
        "Luminance (nits)",
        value=800.0,
        step=1.0,
        format="%.1f"
    )

    frame_rate = st.selectbox(
        "Frame Rate",
        options=[60, 120],
        index=0
    )

    run_btn = st.button("Calculate", type="primary")


# =============================
# Internal Engineering Defaults (hidden from customers)
# =============================
# ✅ 這裡保留你的命名與邏輯：safe_project_name / date_code / document_no
safe_project_name = project_name.replace(" ", "_")

# ✅ 用 session_state 固定 document_no：只有按 Calculate 才更新
if "document_no" not in st.session_state:
    st.session_state["document_no"] = ""

if run_btn:
    now_tpe = datetime.now(ZoneInfo("Asia/Taipei"))
    date_code = now_tpe.strftime("%Y%m%d%H%M%S")
    st.session_state["document_no"] = f"{safe_project_name}_{date_code}"

document_no = st.session_state["document_no"]

param = {
    "diameter": diameter,
    "fov_h": fov_h,
    "fov_v_n": fov_v_n,
    "fov_v_s": fov_v_s,
    "resolution_h": resolution_h,
    "luminance": luminance,
    "frame_rate": frame_rate,

    # 🔒 Internal Engineering Defaults
    "module_angle_limit": 6,
    "module_size_limit": 250,
    "dclk_limit": 10,
    "waveform_duty": 0.7,
    "scan_ratio_limit": 45,
    "channel_threshold_for_double_scan": 64,
    "calibration_ratio": 0.1,
}


# =============================
# Header (Logo + Title + Document No.)  ✅ 你要的優化在這裡
# =============================

# Logo
st.image("yenrich.png", width=130)

# 先組 DocNo HTML（避免巢狀三引號）
doc_html = ""
if document_no:
    doc_html = (
        "<div style='text-align:right; line-height:1.2;'>"
        "<div style='font-size:0.9rem; color:#bdbdbd;'>Document No.</div>"
        f"<div style='font-weight:600;'>{document_no}</div>"
        "</div>"
    )

# Title + DocNo 同一行（單行拼接，沒有縮排）
st.markdown(
    "<div style='display:flex; justify-content:space-between; align-items:flex-start;'>"
    "<h1 style='margin:0; font-size:34px;'>LED Sphere Spec Calculator</h1>"
    f"{doc_html}"
    "</div>",
    unsafe_allow_html=True
)

st.divider()


# =============================
# Calculate (ONLY when button clicked)
# =============================
if run_btn:
    # 🔴 先檢查 Project Name
    # 🔴 檢查所有欄位
    missing_fields = []

    # 文字一定要填
    if not project_name.strip():
        missing_fields.append("Project Name")

    # 直徑必須 > 0
    if diameter <= 0:
        missing_fields.append("Diameter must be greater than 0")

    # 水平 FOV 必須 > 0
    if fov_h <= 0:
        missing_fields.append("FOV Horizontal must be greater than 0")

    # 垂直 FOV 可以是 0（北半球 0 是合理）
    if fov_v_n < 0:
        missing_fields.append("FOV North cannot be negative")

    if fov_v_s < 0:
        missing_fields.append("FOV South cannot be negative")

    # 解析度不能 <= 0
    if resolution_h <= 0:
        missing_fields.append("Resolution Horizontal must be greater than 0")

    if luminance <= 0:
        missing_fields.append("Luminance must be greater than 0")

    if missing_fields:
        st.error(
            "⚠️ Please correct the following:\n\n"
            + "\n".join([f"- {field}" for field in missing_fields])
        )
        st.stop()

    try:
        result = calculate(param)

        # Simple user feedback
        st.toast("Result is ready! Collapse the input panel to view it.", icon="✅")

        # =============================
        # KPI Section
        # =============================
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Pitch (mm)", f'{result["pitch_mm"]:.3f}')
        c2.metric("Module Types (Vertical)", f'{result["n_vertical_final"]}')
        c3.metric("Module Qty. (H)", f'{result["n_equator_final"]}')
        c4.metric("Total Power (kW)", f'{result["total_power_W"]:.2f}')

        # =============================
        # Product Specification
        # =============================
        st.divider()
        st.subheader("Product Specification")

        # 10m threshold (diameter in mm)
        need_superstructure_eval = param["diameter"] >= 10000

        superstructure_msg = "Need external superstructure evaluation"

        if need_superstructure_eval:
            weight_display = superstructure_msg
            room_w_display = superstructure_msg
            room_l_display = superstructure_msg
            room_h_display = superstructure_msg
        else:
            weight_display = math.ceil(result["weight"])
            room_w_display = math.ceil(result["room_size_w"])
            room_l_display = math.ceil(result["room_size_l"])
            room_h_display = f'{math.ceil(result["room_size_h"])} + Bottom Edge Height Above Floor'

        spec_df = pd.DataFrame({
            "Product": [
                "Sphere Diameter (m)",
                "Display area (m2)",
                "Pixel Pitch (mm)",
                "Resolution (H)",
                "Resolution (V)",
                "Sphere FOV (H)",
                "Sphere FOV (V)",
                "Module Types",
                "Maximum Module Size (mm)",
                "Module Qty",
                "Hub Qty (with PSU/RX)",
                "4K controller Qty",
                "Brightness (nits)",
                "Total Power (kW)",
                "Weight (kg)",
                "Room size_W (mm)",
                "Room size_L (mm)",
                "Room size_H (mm)",

            ],
            "Dome Display": [
                round(param["diameter"] / 1000, 2),
                round(result["display_area"], 2),
                round(result["pitch_mm"], 2),
                int(param["resolution_h"]),
                int(result["resolution_v_final"]),
                round(param["fov_h"], 2),
                round(result["fov_v_deg"], 2),
                int(result["n_vertical_final"]),
                f'{result["width_per_module_mm"]:.2f} x {result["height_per_module_mm"]:.2f}',
                int(result["total_n_module"]),
                int(result["total_n_hub"]),
                int(result["total_n_controller"]),
                round(param["luminance"], 1),
                round(result["total_power_W"], 2),
                weight_display,
                room_w_display,
                room_l_display,
                room_h_display,
            ]
        })

        spec_df["Dome Display"] = spec_df["Dome Display"].astype(str)
        st.table(spec_df.set_index("Product"))

        # =============================
        # Sphere Preview
        # =============================
        st.divider()
        st.subheader("Sphere Layout Preview")

        colA, colB = st.columns(2)

        with colA:
            figA = make_sphere_fig(
                diameter=param["diameter"],
                fov_h=param["fov_h"],
                fov_v_n_final=result["fov_v_n_final"],
                fov_v_s_final=result["fov_v_s_final"],
                n_equator_final=result["n_equator_final"],
                n_vertical_final=result["n_vertical_final"],
                elev=0,
                azim=180,
                title="View A"
            )
            st.pyplot(figA, clear_figure=True)

        with colB:
            figB = make_sphere_fig(
                diameter=param["diameter"],
                fov_h=param["fov_h"],
                fov_v_n_final=result["fov_v_n_final"],
                fov_v_s_final=result["fov_v_s_final"],
                n_equator_final=result["n_equator_final"],
                n_vertical_final=result["n_vertical_final"],
                elev=15,
                azim=230,
                title="View B"
            )
            st.pyplot(figB, clear_figure=True)

    except Exception as e:
        st.error(f"Calculation failed: {e}")

else:
    st.info("Click the >> button in the top-left corner, fill in the parameters and click Calculate.")
