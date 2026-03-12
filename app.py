import math
import pandas as pd
import streamlit as st
from calculator import calculate, make_sphere_fig
from datetime import datetime
from zoneinfo import ZoneInfo
import re

st.set_page_config(
    page_title="LED Sphere Spec Calculator",
    page_icon="yenrich.png",
    layout="wide",
)

# =============================
# Session state init
# =============================
if "document_no" not in st.session_state:
    st.session_state["document_no"] = ""

if "has_result" not in st.session_state:
    st.session_state["has_result"] = False

if "result" not in st.session_state:
    st.session_state["result"] = None

if "param_used" not in st.session_state:
    st.session_state["param_used"] = None

if "fig1" not in st.session_state:
    st.session_state["fig1"] = None

if "fig2" not in st.session_state:
    st.session_state["fig2"] = None

if "fig3" not in st.session_state:
    st.session_state["fig3"] = None

if "fig4" not in st.session_state:
    st.session_state["fig4"] = None

if "quote_parts" not in st.session_state:
    st.session_state["quote_parts"] = {}

# =============================
# Sidebar – Core Inputs
# mode / passcode: immediate UI update
# calculation inputs: submit only on Calculate
# =============================
with st.sidebar:
    st.header("Input Parameters")
    st.caption("(All fields are required.)")

    # -----------------------------
    # Immediate widgets (outside form)
    # -----------------------------
    mode = st.radio(
        "Mode",
        options=["Visitor", "Yenrich"],
        index=0,
        horizontal=True
    )

    passcode = ""
    if mode == "Yenrich":
        passcode = st.text_input(
            "Yenrich Passcode",
            value="",
            type="password",
            placeholder="Enter passcode"
        )

    # -----------------------------
    # Submit-only widgets (inside form)
    # -----------------------------
    with st.form("input_form", clear_on_submit=False, enter_to_submit=False):
        project_name = st.text_input("Project Name", value="")

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

        bottom_edge_height = st.number_input(
            "Bottom Edge Height Above Floor (mm)",
            value=500.0,
            step=1.0,
            format="%.1f"
        )

        run_btn = st.form_submit_button("Calculate", type="primary")

show_bom = (mode == "Yenrich" and passcode == "25087030")

# =============================
# Internal Engineering Defaults
# =============================
safe_project_name = re.sub(r"[^A-Za-z0-9_-]", "_", project_name)

param = {
    "diameter": diameter,
    "fov_h": fov_h,
    "fov_v_n": fov_v_n,
    "fov_v_s": fov_v_s,
    "resolution_h": resolution_h,
    "luminance": luminance,
    "frame_rate": frame_rate,
    "bottom_edge_height": bottom_edge_height,

    # Internal Engineering Defaults
    "module_angle_limit": 6,
    "module_size_limit": 250,
    "dclk_limit": 10,
    "waveform_duty": 0.7,
    "scan_ratio_limit": 45,
    "channel_threshold_for_double_scan": 64,
    "calibration_ratio": 0.1,
}

# =============================
# Header (Logo + Title + Document No.)
# =============================
st.image("yenrich.png", width=130)

doc_html = ""
if st.session_state["document_no"]:
    doc_html = (
        "<div style='text-align:right; line-height:1.2;'>"
        "<div style='font-size:0.9rem; color:#bdbdbd;'>Document No.</div>"
        f"<div style='font-weight:600;'>{st.session_state['document_no']}</div>"
        "</div>"
    )

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
    missing_fields = []

    if not project_name.strip():
        missing_fields.append("Project Name")

    if diameter <= 0:
        missing_fields.append("Diameter must be greater than 0")

    if fov_h <= 0:
        missing_fields.append("FOV Horizontal must be greater than 0")

    if fov_v_n < 0:
        missing_fields.append("FOV North cannot be negative")

    if fov_v_s < 0:
        missing_fields.append("FOV South cannot be negative")

    if resolution_h <= 0:
        missing_fields.append("Resolution Horizontal must be greater than 0")

    if luminance <= 0:
        missing_fields.append("Luminance must be greater than 0")

    if bottom_edge_height < 0:
        missing_fields.append("Bottom Edge Height cannot be negative")

    if missing_fields:
        st.error(
            "⚠️ Please correct the following:\n\n"
            + "\n".join([f"- {field}" for field in missing_fields])
        )
        st.stop()

    try:
        result = calculate(param)
        need_superstructure_eval = param["diameter"] >= 10000

        fig1 = make_sphere_fig(
            diameter=param["diameter"],
            fov_h=param["fov_h"],
            fov_v_n_final=result["fov_v_n_final"],
            fov_v_s_final=result["fov_v_s_final"],
            n_equator_final=result["n_equator_final"],
            n_vertical_final=result["n_vertical_final"],
            bottom_edge_height=param.get("bottom_edge_height", 0.0),
            show_room_box=False,
            elev=0,
            azim=180,
            title="View 1 (Front)"
        )

        fig2 = make_sphere_fig(
            diameter=param["diameter"],
            fov_h=param["fov_h"],
            fov_v_n_final=result["fov_v_n_final"],
            fov_v_s_final=result["fov_v_s_final"],
            n_equator_final=result["n_equator_final"],
            n_vertical_final=result["n_vertical_final"],
            bottom_edge_height=param.get("bottom_edge_height", 0.0),
            show_room_box=False,
            elev=25,
            azim=-145,
            title="View 2 (Iso)"
        )

        fig3 = None
        fig4 = None

        if not need_superstructure_eval:
            fig3 = make_sphere_fig(
                diameter=param["diameter"],
                fov_h=param["fov_h"],
                fov_v_n_final=result["fov_v_n_final"],
                fov_v_s_final=result["fov_v_s_final"],
                n_equator_final=result["n_equator_final"],
                n_vertical_final=result["n_vertical_final"],
                bottom_edge_height=param.get("bottom_edge_height", 0.0),
                show_room_box=False,
                show_height_dims=True,
                elev=0,
                azim=180,
                title="Front View (Heights)"
            )

            fig4 = make_sphere_fig(
                diameter=param["diameter"],
                fov_h=param["fov_h"],
                fov_v_n_final=result["fov_v_n_final"],
                fov_v_s_final=result["fov_v_s_final"],
                n_equator_final=result["n_equator_final"],
                n_vertical_final=result["n_vertical_final"],
                room_w=result["room_size_w"],
                room_l=result["room_size_l"],
                room_h=result["room_size_h"],
                bottom_edge_height=param.get("bottom_edge_height", 0.0),
                show_room_box=True,
                show_room_dims=True,
                flip_xy=False,
                elev=25,
                azim=-145,
                title="Recommended Room Dimensions"
            )

        now_tpe = datetime.now(ZoneInfo("Asia/Taipei"))
        date_code = now_tpe.strftime("%Y%m%d%H%M%S")
        st.session_state["document_no"] = f"{safe_project_name}_{date_code}"

        st.session_state["result"] = result
        st.session_state["param_used"] = param.copy()
        st.session_state["fig1"] = fig1
        st.session_state["fig2"] = fig2
        st.session_state["fig3"] = fig3
        st.session_state["fig4"] = fig4
        st.session_state["has_result"] = True

        st.toast("Result updated!", icon="✅")

    except Exception as e:
        st.error(f"Calculation failed: {e}")
        st.stop()

# =============================
# BOM Fragment
# Only BOM reruns when BOM widgets change
# =============================

def get_led_options_by_pitch(pitch_mm: float) -> dict:
    if pitch_mm <= 1.2:
        return {
            "MIP-C0606TM": 2.11,
            "LSSF0606CC2": 3.2,
            "LSSF0606CC3": 2.78,
        }
    elif pitch_mm <= 1.7:
        return {
            "MIP-C1010TM": 2.78,
            "MIP-C0606TM": 2.11,
            "LSSF0606CC2": 3.2,
            "LSSF0606CC3": 2.78,
        }
    elif pitch_mm <= 2.2:
        return {
            "NH1515": 1.35,
            "RS1515": 5.04,
            "MIP-C1010TM": 2.78,
        }
    else:
        return {
            "NH2020": 2.14,
            "FM2020": 4.71,
            "RS2020": 7.43,
            "NH1515": 1.35,
            "RS1515": 5.04,
        }


def get_part_catalog(pitch_mm: float) -> dict:
    return {
        "LED": get_led_options_by_pitch(pitch_mm),
        "PWM IC": {"ICND-2069": 0.09},
        "SCAN IC": {"ICND-2019": 0.07},
        "Module (PCB)": {"4 layer": 200},
        "Hub": {"2 layer": 58.29},
        "RX": {"AUO-R3E": 35, "Mooncell-A10X": 21.2},
        "Controller": {"AUO-D4000": 2000, "Mooncell-B2000ES": 1686},
        "PSU": {"UHP-200": 28.01},
        "Mechanical": {"mechanical": 600},
    }

@st.fragment
def render_bom(show_bom: bool, result: dict):
    if not show_bom:
        return

    st.divider()
    st.subheader("BOM List (Quotation)")

    PART_CATALOG = get_part_catalog(result["pitch_mm"])

    qty_map = {
        "LED": int(result["total_n_led_kpcs"]),
        "PWM IC": int(result["total_n_pwm"]),
        "SCAN IC": int(result["total_n_scan"]),
        "Module (PCB)": round(result["display_area"],1),
        "Hub": int(result["total_n_hub"]),
        "RX": int(result["total_n_hub"]),
        "Controller": int(result["total_n_controller"]),
        "PSU": int(result["total_n_hub"]),
        "Mechanical": round(result["display_area"], 1),
    }

    if not st.session_state["quote_parts"]:
        st.session_state["quote_parts"] = {
            item: list(PART_CATALOG[item].keys())[0]
            for item in PART_CATALOG.keys()
        }

    # 新結果進來時，如果舊選項不存在就補回預設
    for item in PART_CATALOG.keys():
        if item not in st.session_state["quote_parts"]:
            st.session_state["quote_parts"][item] = list(PART_CATALOG[item].keys())[0]
        elif st.session_state["quote_parts"][item] not in PART_CATALOG[item]:
            st.session_state["quote_parts"][item] = list(PART_CATALOG[item].keys())[0]

    h1, h2, h3, h4, h5 = st.columns([2.2, 3.2, 1.2, 1.4, 1.6])

    with h1:
        st.caption("Item")
    with h2:
        st.caption("Part No.")
    with h3:
        st.caption("Qty")
    with h4:
        st.caption("Unit price (USD)")
    with h5:
        st.caption("Total price (USD)")

    st.markdown("---")
    grand_total = 0.0

    for item in PART_CATALOG.keys():
        c1, c2, c3, c4, c5 = st.columns([2.2, 3.2, 1.2, 1.4, 1.6])

        qty = qty_map[item]
        options = list(PART_CATALOG[item].keys())
        current = st.session_state["quote_parts"].get(item, options[0])

        if current not in options:
            current = options[0]

        with c1:
            st.write(f"**{item}**")

        with c2:
            selected = st.selectbox(
                label=f"{item}_part",
                options=options,
                index=options.index(current),
                label_visibility="collapsed",
                key=f"quote_parts_{item}"
            )

        st.session_state["quote_parts"][item] = selected
        unit_price = float(PART_CATALOG[item][selected])
        total_price = unit_price * qty
        grand_total += total_price

        # Qty unit rule
        if item == "LED":
            unit = "kpcs"
        elif item == "Module (PCB)":
            unit = "m²"
        elif item == "Mechanical":
            unit = "m²"
        else:
            unit = "pcs"

        with c3:
            st.write(f"{qty:,} {unit}")

        with c4:
            st.write(f"{unit_price:,.2f}")

        with c5:
            st.write(f"{total_price:,.2f}")

    st.markdown("---")
    st.metric("Grand Total (USD)", f"{grand_total:,.2f}")

# =============================
# Display Area
# =============================
if st.session_state["has_result"]:
    result = st.session_state["result"]
    param_used = st.session_state["param_used"]

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

    need_superstructure_eval = param_used["diameter"] >= 10000
    superstructure_msg = "Need external superstructure evaluation"

    if need_superstructure_eval:
        weight_display = superstructure_msg
        room_size = superstructure_msg
    else:
        weight_display = math.ceil(result["weight"])
        room_w_display = math.ceil(result["room_size_w"])
        room_l_display = math.ceil(result["room_size_l"])
        room_h_display = math.ceil(result["room_size_h"])
        room_size = f"{room_w_display} × {room_l_display} × {room_h_display}"

    deg = "\u00B0"

    spec_df = pd.DataFrame({
        "Product": [
            "Sphere Diameter (m)",
            "Display area (m2)",
            "Pixel Pitch (mm)",
            "Resolution (H*V)",
            "Sphere FOV (H*V)",
            "Module Types",
            "Maximum Module Size (mm)",
            "Module Qty",
            "Hub Qty (with PSU/RX)",
            "4K controller Qty",
            "Brightness (nits)",
            "Total Power (kW)",
            "Weight (kg)",
            "Room size_W * L * H (mm)",
        ],
        "Dome Display": [
            round(param_used["diameter"] / 1000, 2),
            round(result["display_area"], 2),
            round(result["pitch_mm"], 3),
            f'{int(param_used["resolution_h"])} × {int(result["resolution_v_final"])}',
            f'{round(param_used["fov_h"], 2)}{deg} × {round(result["fov_v_n_final"], 2) + round(result["fov_v_s_final"], 2)}{deg}',
            int(result["n_vertical_final"]),
            f'{result["width_per_module_mm"]:.2f} x {result["height_per_module_mm"]:.2f}',
            int(result["total_n_module"]),
            int(result["total_n_hub"]),
            int(result["total_n_controller"]),
            round(param_used["luminance"], 1),
            round(result["total_power_W"], 2),
            weight_display,
            room_size,
        ]
    })

    spec_df["Dome Display"] = spec_df["Dome Display"].astype(str)
    st.table(spec_df.set_index("Product"))

    # =============================
    # Sphere Preview
    # =============================
    st.divider()
    st.subheader("Sphere Layout Preview")

    r1c1, r1c2 = st.columns(2)

    with r1c1:
        if st.session_state["fig1"] is not None:
            st.pyplot(st.session_state["fig1"], clear_figure=False)

    with r1c2:
        if st.session_state["fig2"] is not None:
            st.pyplot(st.session_state["fig2"], clear_figure=False)

    if not need_superstructure_eval:
        r2c1, r2c2 = st.columns(2)

        with r2c1:
            if st.session_state["fig3"] is not None:
                st.pyplot(
                    st.session_state["fig3"],
                    use_container_width=True,
                    clear_figure=False
                )

        with r2c2:
            if st.session_state["fig4"] is not None:
                st.pyplot(
                    st.session_state["fig4"],
                    use_container_width=True,
                    clear_figure=False
                )

    # =============================
    # BOM List (Quotation)
    # =============================
    render_bom(show_bom, result)

else:
    st.info("Click the >> button in the top-left corner, fill in the parameters and click Calculate.")