import pandas as pd
import streamlit as st
from calculator import calculate, make_sphere_fig

st.set_page_config(
    page_title="LED Sphere Spec Calculator",
    page_icon="Yenrich.png",
    layout="wide"
)

# =============================
# Header (Logo + Title)
# =============================
header_col1, header_col2 = st.columns([1, 6])

with header_col1:
    st.image("Yenrich.png", width=160)

with header_col2:
    st.markdown(
        "<h1 style='margin-top:10px;'>LED Sphere Spec Calculator</h1>",
        unsafe_allow_html=True
    )

st.divider()


# =============================
# Sidebar – 核心輸入參數
# =============================
with st.sidebar:
    st.header("Input Parameters")

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
# 固定工程參數（客戶看不到）
# =============================
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
# 計算與顯示結果
# =============================
if run_btn:
    try:
        result = calculate(param)

        # ===== KPI 區 =====
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Pitch (mm)", f'{result["pitch_mm"]:.3f}')
        c2.metric("Module types (Vertical)", f'{result["n_vertical_final"]}')
        c3.metric("Module Qty. (H)", f'{result["n_equator_final"]}')
        c4.metric("Total Power (kW)", f'{result["total_power_W"]:.2f}')


        # ===== LED / IC 表格 =====
        st.divider()
        st.subheader("Product Specification")

        spec_df = pd.DataFrame({
            "Product": [
                "Sphere Diameter (m)",
                "Pixel Pitch (mm)",
                "Resolution (H)",
                "Resolution (V)",
                "Sphere FOV (H)",
                "Sphere FOV (V)",
                "Module Types",
                "Maximum Module Size (mm)",
                "Hub Qty (with PSU/RX)",
                "Brightness (nits)",
                "Total Power (kW)"
            ],
            "Dome Display": [
                round(param["diameter"] / 1000, 2),
                round(result["pitch_mm"], 2),
                int(param["resolution_h"]),
                int(result["resolution_v_px"]),
                round(param["fov_h"], 2),
                round(result["fov_v_deg"], 2),
                int(result["n_vertical_final"]),
                f'{result["width_per_module_mm"]:.2f} x {result["height_per_module_mm"]:.2f}',
                int(result["total_n_hub"]),
                round(param["luminance"], 1),
                round(result["total_power_W"], 2)
            ]
        })

        # ✅ 讓整欄都是 string，避免 pyarrow 嘗試轉成 double
        spec_df["Dome Display"] = spec_df["Dome Display"].astype(str)

        st.table(spec_df.set_index("Product"))

        st.divider()

        # ===== 球面預覽 =====
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
    st.info("Fill in the parameters on the left and click Calculate.")
