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
# Sidebar – Core Inputs
# =============================
with st.sidebar:
    st.header("Input Parameters")
    st.caption("(All fields are required.)")

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

    project_name = st.text_input("Project Name", value="")

    diameter = st.number_input(
        "Diameter (mm)", value=3000.0, step=1.0, format="%.1f"
    )

    fov_h = st.number_input(
        "FOV Horizontal (deg)", value=180.00, step=0.01, format="%.2f"
    )

    fov_v_n = st.number_input(
        "FOV North (deg)", value=67.50, step=0.01, format="%.2f"
    )

    fov_v_s = st.number_input(
        "FOV South (deg)", value=33.75, step=0.01, format="%.2f"
    )

    resolution_h = st.number_input(
        "Resolution Horizontal (px)", value=3840, step=1
    )

    luminance = st.number_input(
        "Luminance (nits)", value=800.0, step=1.0, format="%.1f"
    )

    frame_rate = st.selectbox("Frame Rate", options=[60, 120], index=0)

    bottom_edge_height = st.number_input(
        "Bottom Edge Height Above Floor (mm)", value=500.0, step=1.0, format="%.1f"
    )

    run_btn = st.button("Calculate", type="primary")

show_bom = (mode == "Yenrich" and passcode == "25087030")

# =============================
# Internal Engineering Defaults (hidden from customers)
# =============================
safe_project_name = re.sub(r'[^A-Za-z0-9_-]', '_', project_name)

# ✅ document_no：只有按 Calculate 才更新
if "document_no" not in st.session_state:
    st.session_state["document_no"] = ""

if run_btn:
    now_tpe = datetime.now(ZoneInfo("Asia/Taipei"))
    date_code = now_tpe.strftime("%Y%m%d%H%M%S")
    st.session_state["document_no"] = f"{safe_project_name}_{date_code}"

document_no = st.session_state["document_no"]

# =============================
# Param (current inputs)
# =============================
param = {
    "diameter": diameter,
    "fov_h": fov_h,
    "fov_v_n": fov_v_n,
    "fov_v_s": fov_v_s,
    "resolution_h": resolution_h,
    "luminance": luminance,
    "frame_rate": frame_rate,
    "bottom_edge_height": bottom_edge_height,

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
# Session state for "manual compute mode"
# =============================
if "has_result" not in st.session_state:
    st.session_state["has_result"] = False
if "result" not in st.session_state:
    st.session_state["result"] = None
if "param_used" not in st.session_state:
    st.session_state["param_used"] = None
if "dirty" not in st.session_state:
    st.session_state["dirty"] = False

# 只要目前 param 跟上次計算用的 param 不同，就 dirty（但不重算）
if st.session_state["param_used"] is not None and param != st.session_state["param_used"]:
    st.session_state["dirty"] = True


# =============================
# Header (Logo + Title + Document No.)
# =============================
st.image("yenrich.png", width=130)

doc_html = ""
if document_no:
    doc_html = (
        "<div style='text-align:right; line-height:1.2;'>"
        "<div style='font-size:0.9rem; color:#bdbdbd;'>Document No.</div>"
        f"<div style='font-weight:600;'>{document_no}</div>"
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

        # ✅ 存起來：之後改任何值都不會跳回初始畫面
        st.session_state["result"] = result
        st.session_state["param_used"] = param.copy()
        st.session_state["has_result"] = True
        st.session_state["dirty"] = False

        st.toast("Result updated! (No auto-calc. Click Calculate to refresh.)", icon="✅")

    except Exception as e:
        st.error(f"Calculation failed: {e}")
        st.stop()


# =============================
# Display Area (use cached result)
# =============================
if st.session_state["has_result"]:
    result = st.session_state["result"]
    param_used = st.session_state["param_used"]

    # 如果輸入變了但還沒按 Calculate：只提醒，不重算、不跳頁
    if st.session_state.get("dirty", False):
        st.warning("Inputs changed — click **Calculate** to update.")

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
        room_size = f'{room_w_display} × {room_l_display} × {room_h_display}'

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
            f'{round(param_used["fov_h"], 2)}{deg} × {round(result["fov_v_deg"], 2)}{deg}',
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

    need_superstructure_eval = param_used["diameter"] >= 10000

    r1c1, r1c2 = st.columns(2)

    with r1c1:
        fig1 = make_sphere_fig(
            diameter=param_used["diameter"],
            fov_h=param_used["fov_h"],
            fov_v_n_final=result["fov_v_n_final"],
            fov_v_s_final=result["fov_v_s_final"],
            n_equator_final=result["n_equator_final"],
            n_vertical_final=result["n_vertical_final"],
            bottom_edge_height=param_used.get("bottom_edge_height", 0.0),
            show_room_box=False,
            elev=0,
            azim=180,
            title="View 1 (Front)"
        )
        st.pyplot(fig1, clear_figure=True)

    with r1c2:
        fig2 = make_sphere_fig(
            diameter=param_used["diameter"],
            fov_h=param_used["fov_h"],
            fov_v_n_final=result["fov_v_n_final"],
            fov_v_s_final=result["fov_v_s_final"],
            n_equator_final=result["n_equator_final"],
            n_vertical_final=result["n_vertical_final"],
            bottom_edge_height=param_used.get("bottom_edge_height", 0.0),
            show_room_box=False,
            elev=25,
            azim=-145,
            title="View 2 (Iso)"
        )
        st.pyplot(fig2, clear_figure=True)

    if not need_superstructure_eval:
        r2c1, r2c2 = st.columns(2)

        with r2c1:
            fig3 = make_sphere_fig(
                diameter=param_used["diameter"],
                fov_h=param_used["fov_h"],
                fov_v_n_final=result["fov_v_n_final"],
                fov_v_s_final=result["fov_v_s_final"],
                n_equator_final=result["n_equator_final"],
                n_vertical_final=result["n_vertical_final"],
                bottom_edge_height=param_used.get("bottom_edge_height", 0.0),
                show_room_box=False,
                show_height_dims=True,
                elev=0,
                azim=180,
                title="Front View (Heights)"
            )
            st.pyplot(fig3, use_container_width=True, clear_figure=True)

        with r2c2:
            fig4 = make_sphere_fig(
                diameter=param_used["diameter"],
                fov_h=param_used["fov_h"],
                fov_v_n_final=result["fov_v_n_final"],
                fov_v_s_final=result["fov_v_s_final"],
                n_equator_final=result["n_equator_final"],
                n_vertical_final=result["n_vertical_final"],
                room_w=result["room_size_w"],
                room_l=result["room_size_l"],
                room_h=result["room_size_h"],
                bottom_edge_height=param_used.get("bottom_edge_height", 0.0),
                show_room_box=True,
                show_room_dims=True,
                flip_xy=False,
                elev=25,
                azim=-145,
                title="Recommended Room Dimensions"
            )
            st.pyplot(fig4, use_container_width=True, clear_figure=True)

    # =============================
    # BOM List (Quotation)
    # =============================
    if show_bom:
        st.divider()
        st.subheader("BOM List (Quotation)")

        PART_CATALOG = {
            "LED": {"LED_A": 100, "LED_B": 200},
            "PWM IC": {"PWM_A": 100, "PWM_B": 200},
            "SCAN IC": {"SCAN_A": 100, "SCAN_B": 200},
            "Module": {"Module_A": 100, "Module_B": 200},
            "RX": {"RX_A": 100, "RX_B": 200},
            "PSU": {"PSU_A": 100, "PSU_B": 200},
            "Hub": {"Hub_A": 100, "Hub_B": 200},
            "Controller": {"Controller_A": 100, "Controller_B": 200},
        }

        qty_map = {
            "LED": int(result["total_n_led_kpcs"]),
            "PWM IC": int(result["total_n_pwm"]),
            "SCAN IC": int(result["total_n_scan"]),
            "Module": int(result["total_n_module"]),
            "RX": int(result["total_n_hub"]),
            "PSU": int(result["total_n_hub"]),
            "Hub": int(result["total_n_hub"]),
            "Controller": int(result["total_n_controller"]),
        }

        # ⚠️ 這裡用「固定 key」：不要綁 document_no，避免你每次按 Calculate 選擇被清掉
        quote_key = "quote_parts"
        if quote_key not in st.session_state:
            st.session_state[quote_key] = {
                item: list(PART_CATALOG[item].keys())[0]
                for item in PART_CATALOG.keys()
            }

        h1, h2, h3, h4, h5 = st.columns([2.2, 3.2, 1.2, 1.4, 1.6])
        with h1: st.caption("Item")
        with h2: st.caption("Part No.")
        with h3: st.caption("Qty")
        with h4: st.caption("Unit price")
        with h5: st.caption("Total price")

        st.markdown("---")

        grand_total = 0.0

        for item in PART_CATALOG.keys():
            c1, c2, c3, c4, c5 = st.columns([2.2, 3.2, 1.2, 1.4, 1.6])

            qty = qty_map[item]
            options = list(PART_CATALOG[item].keys())

            current = st.session_state[quote_key].get(item, options[0])
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
                    key=f"{quote_key}_{item}"
                )
                st.session_state[quote_key][item] = selected

            unit_price = float(PART_CATALOG[item][selected])
            total_price = unit_price * qty
            grand_total += total_price

            with c3:
                st.write(f"{qty:,}")
            with c4:
                st.write(f"{unit_price:,.2f}")
            with c5:
                st.write(f"{total_price:,.2f}")

        st.markdown("---")
        st.metric("Grand Total", f"{grand_total:,.2f}")

else:
    st.info("Click the >> button in the top-left corner, fill in the parameters and click Calculate.")