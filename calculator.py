# calculator.py
import math
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import proj3d


def calculate(param: dict) -> dict:
    diameter = param["diameter"]
    fov_h = param["fov_h"]
    fov_v_n = param["fov_v_n"]
    fov_v_s = param["fov_v_s"]
    resolution_h = int(param["resolution_h"])
    luminance = param["luminance"]
    frame_rate = int(param["frame_rate"])
    module_angle_limit = param["module_angle_limit"]
    module_size_limit = param["module_size_limit"]
    dclk_limit = param["dclk_limit"]
    waveform_duty = param["waveform_duty"]
    scan_ratio_limit = int(param["scan_ratio_limit"])
    channel_threshold_for_double_scan = param["channel_threshold_for_double_scan"]
    calibration_ratio = param["calibration_ratio"]
    bottom_edge_height = float(param.get("bottom_edge_height", 0.0))

    arc_h = math.pi * diameter * (fov_h / 360)
    pitch = arc_h / resolution_h

    fov_v = float(fov_v_n) + float(fov_v_s)
    resolution_v = int(round(float(resolution_h) * (float(fov_v) / float(fov_h))))

    if frame_rate == 60:
        receiver_capacity = 262144
    elif frame_rate == 120:
        receiver_capacity = 131072
    else:
        # 先用保守值，避免 UI 直接炸（你也可以改成 raise）
        receiver_capacity = 262144

    arc_length_limit = diameter * math.pi / (360 / module_angle_limit)
    module_width_limit = min(module_size_limit, arc_length_limit)

    n_equator = math.ceil(arc_h / module_width_limit)
    if n_equator % 4 != 0:
        n_equator += (4 - n_equator % 4)
    while resolution_h % n_equator != 0:
        n_equator += 4

    n_equator_final = n_equator
    angle_per_module = fov_h / n_equator_final
    width_per_module = arc_h / n_equator_final
    px_per_module_h = resolution_h // n_equator_final

    arc_v = math.pi * diameter * (fov_v / 360)
    n_vertical = math.ceil(arc_v / module_size_limit)
    if n_vertical % 4 != 0:
        n_vertical += (4 - n_vertical % 4)

    cands = [n_vertical + 4 * k for k in range(0, 5)]
    ok = []
    for nv in cands:
        if resolution_v % nv == 0:
            pxv = resolution_v // nv
            if (pxv % 3 == 0) or (pxv % 4 == 0):
                ok.append(nv)

    if ok:
        n_vertical_final = ok[0]
        resolution_v_final = int(resolution_v)
        arc_v_final = arc_v
        fov_v_final = fov_v
    else:
        n_vertical_final = cands[0]
        base = 4 * n_vertical_final
        resolution_v_final = max(base, int(round(resolution_v / base) * base))
        arc_v_final = pitch * resolution_v_final
        fov_v_final = arc_v_final * 360 / (math.pi * diameter)

    height_per_module = arc_v_final / n_vertical_final
    px_per_module_v = resolution_v_final // n_vertical_final

    ratio_n = fov_v_n / (fov_v_n + fov_v_s)
    ratio_s = fov_v_s / (fov_v_n + fov_v_s)
    fov_v_n_ideal = fov_v_final * ratio_n
    fov_v_s_ideal = fov_v_final * ratio_s
    angle_per_module_v = fov_v_final / n_vertical_final
    n_vertical_n = round(fov_v_n_ideal / angle_per_module_v)
    n_vertical_s = n_vertical_final - n_vertical_n
    fov_v_n_final = n_vertical_n * angle_per_module_v
    fov_v_s_final = n_vertical_s * angle_per_module_v

    display_area = abs(2 * math.pi * (diameter/2000) * (diameter/2000) * (math.sin(fov_v_n_final / 180 * math.pi)+math.sin(fov_v_s_final / 180 * math.pi)) * fov_h / 360)

    if px_per_module_h * px_per_module_v * 8 <= receiver_capacity:
        n_module_per_receiver = 8
    elif px_per_module_h * px_per_module_v * 4 <= receiver_capacity:
        n_module_per_receiver = 4
    else:
        n_module_per_receiver = 1

    max_data_groups_per_module = int(32 / n_module_per_receiver)

    scan_candidates = []
    scan_min = max(8, px_per_module_v // max_data_groups_per_module)
    for scan in range(int(scan_min), scan_ratio_limit + 1):
        if px_per_module_v % scan == 0 and (scan * px_per_module_h * frame_rate * 16 / 1_000_000) <= dclk_limit:
            scan_candidates.append(scan)

    max_scan = max(scan_candidates) if scan_candidates else scan_ratio_limit
    data_groups_per_module = px_per_module_v / max_scan
    dclk = max_scan * px_per_module_h * frame_rate * 16 / 1_000_000

    # ===== 每片燈板水平方向 LED 顆數（你的公式保留）=====
    horizontal_led_counts_lower = []
    horizontal_led_counts_upper = []

    for i in range(1, n_vertical_n + 1):
        board_index = n_vertical_n + 1 - i
        lower = round((diameter * math.pi * math.cos(((board_index - 1) * angle_per_module_v) / 180 * math.pi)
                       * fov_h / 360 / n_equator_final) / pitch, 0)
        upper = round((diameter * math.pi * math.cos(((board_index) * angle_per_module_v) / 180 * math.pi)
                       * fov_h / 360 / n_equator_final) / pitch, 0)
        horizontal_led_counts_lower.append(lower)
        horizontal_led_counts_upper.append(upper)

    for i in range(1, n_vertical_s + 1):
        board_index = i
        lower = round((diameter * math.pi * math.cos(((board_index) * angle_per_module_v) / 180 * math.pi)
                       * fov_h / 360 / n_equator_final) / pitch, 0)
        upper = round((diameter * math.pi * math.cos(((board_index - 1) * angle_per_module_v) / 180 * math.pi)
                       * fov_h / 360 / n_equator_final) / pitch, 0)
        horizontal_led_counts_lower.append(lower)
        horizontal_led_counts_upper.append(upper)

    # ===== IC / LED count（保留你的算法）=====
    n_module_led_counts = []
    n_module_pwm_counts = []
    n_module_scan_counts = []

    for i in range(1, n_vertical_final + 1):
        board_index = i
        n_module_led = round((horizontal_led_counts_upper[i - 1] + horizontal_led_counts_lower[i - 1]) * px_per_module_v / 2, 0)
        n_module_led_counts.append(n_module_led)

        max_pixel = max(horizontal_led_counts_upper[board_index - 1], horizontal_led_counts_lower[board_index - 1])
        scan_region = 1 if max_pixel <= channel_threshold_for_double_scan else 2
        n_module_scan = math.ceil(max_scan / 8) * scan_region * data_groups_per_module
        n_module_scan_counts.append(n_module_scan)

        n_module_pwm = math.ceil(max_pixel / 16) * 3 * data_groups_per_module
        n_module_pwm_counts.append(n_module_pwm)

    total_n_led = sum(n_module_led_counts) * n_equator_final / 1000
    total_n_scan = sum(n_module_scan_counts) * n_equator_final
    total_n_pwm = sum(n_module_pwm_counts) * n_equator_final
    total_n_module = n_equator_final * n_vertical_final
    total_n_hub = total_n_module / n_module_per_receiver
    total_n_controller = math.ceil(px_per_module_h * px_per_module_v * total_n_module / 3840 / 2160)

    # ===== Power（保留你原本常數與邏輯）=====
    LED_0606_R, LED_0606_G, LED_0606_B = 12.09, 27.59, 5.09
    LED_1010_R, LED_1010_G, LED_1010_B = 15, 36, 6
    LED_1515_R, LED_1515_G, LED_1515_B = 4.2, 22.46, 4.56
    LED_2020_R, LED_2020_G, LED_2020_B = 7.15, 24.8, 7

    if pitch < 1.2:
        LED_R, LED_G, LED_B = LED_0606_R, LED_0606_G, LED_0606_B
        RR_V, GB_V = 2.8, 3.8
    elif pitch < 1.7:
        LED_R, LED_G, LED_B = LED_1010_R, LED_1010_G, LED_1010_B
        RR_V, GB_V = 4.2, 4.2
    elif pitch < 2.2:
        LED_R, LED_G, LED_B = LED_1515_R, LED_1515_G, LED_1515_B
        RR_V, GB_V = 4.2, 4.2
    else:
        LED_R, LED_G, LED_B = LED_2020_R, LED_2020_G, LED_2020_B
        RR_V, GB_V = 4.2, 4.2

    R_nits = luminance / (1 - calibration_ratio) * 0.2715
    G_nits = luminance / (1 - calibration_ratio) * 0.6715
    B_nits = luminance / (1 - calibration_ratio) * 0.057

    R_current = R_nits / ((LED_R / 1000) / (pitch / 1000) / (pitch / 1000) * waveform_duty / max_scan)
    G_current = G_nits / ((LED_G / 1000) / (pitch / 1000) / (pitch / 1000) * waveform_duty / max_scan)
    B_current = B_nits / ((LED_B / 1000) / (pitch / 1000) / (pitch / 1000) * waveform_duty / max_scan)

    R_LED_power = (R_current / 1000) * waveform_duty / max_scan * RR_V
    G_LED_power = (G_current / 1000) * waveform_duty / max_scan * GB_V
    B_LED_power = (B_current / 1000) * waveform_duty / max_scan * GB_V
    LED_power = (R_LED_power + G_LED_power + B_LED_power) * total_n_led * 1000
    system_power = (total_n_pwm + total_n_scan) * 0.006 * GB_V + total_n_hub * 3
    total_power = (LED_power + system_power) * 1.2

    weight = display_area / 10.4576 * 870

    if fov_h <= 180:
        room_size_w = diameter * math.sin((fov_h/2)/180*math.pi) + 3000
        room_size_l = diameter / 2  - (diameter / 2 * math.cos((fov_h/2)/180*math.pi)) + 3000
    else:
        room_size_w = diameter + 3000
        room_size_l = diameter / 2  + (diameter / 2 * math.sin(((fov_h-180)/2)/180*math.pi)) + 3000

    room_size_h = diameter / 2 * (math.sin(fov_v_n_final/180*math.pi) + math.sin(fov_v_s_final/180*math.pi)) + 1500 + bottom_edge_height

    return {
        # basics
        "pitch_mm": pitch,
        "fov_v_deg": fov_v,
        "resolution_v_final": resolution_v_final,
        "receiver_capacity": receiver_capacity,

        # module H/V
        "n_equator_final": n_equator_final,
        "angle_per_module_h_deg": angle_per_module,
        "width_per_module_mm": width_per_module,
        "px_per_module_h": px_per_module_h,

        "n_vertical_final": n_vertical_final,
        "angle_per_module_v_deg": angle_per_module_v,
        "height_per_module_mm": height_per_module,
        "px_per_module_v": px_per_module_v,

        "n_vertical_n": n_vertical_n,
        "n_vertical_s": n_vertical_s,
        "fov_v_n_final": fov_v_n_final,
        "fov_v_s_final": fov_v_s_final,
        "display_area": display_area,

        # data
        "n_module_per_receiver": n_module_per_receiver,
        "data_groups_per_module": data_groups_per_module,
        "scan_candidates": scan_candidates,
        "max_scan": max_scan,
        "dclk_mhz": dclk,

        # lists
        "horizontal_led_counts_upper": horizontal_led_counts_upper,
        "horizontal_led_counts_lower": horizontal_led_counts_lower,
        "n_module_led_counts": n_module_led_counts,
        "n_module_pwm_counts": n_module_pwm_counts,
        "n_module_scan_counts": n_module_scan_counts,

        # totals
        "total_n_led_kpcs": total_n_led,
        "total_n_pwm": total_n_pwm,
        "total_n_scan": total_n_scan,
        "total_n_module": total_n_module,
        "total_n_hub": total_n_hub,
        "total_n_controller": total_n_controller,

        # power
        "R_current_mA": R_current,
        "G_current_mA": G_current,
        "B_current_mA": B_current,
        "LED_power_W": LED_power,
        "system_power_W": system_power,
        "total_power_W": total_power/1000,

        # mechanical
        "weight": weight,
        "room_size_w": room_size_w,
        "room_size_l": room_size_l,
        "room_size_h": room_size_h,
    }


def make_sphere_fig(
    diameter, fov_h, fov_v_n_final, fov_v_s_final,
    n_equator_final, n_vertical_final,
    elev, azim, title,
    room_w=None, room_l=None, room_h=None,
    bottom_edge_height=0.0,
    show_room_box=False,
    flip_xy=False,   # ✅ 把球與框在 XY 平面旋轉 180°
    show_room_dims=False,  # ✅ 新增：標出 W/L/H
    show_height_dims=False,
):
    R = diameter / 2
    fov_v_n = float(fov_v_n_final)
    fov_v_s = float(fov_v_s_final)

    theta_min = np.deg2rad(90 - fov_v_n)
    theta_max = np.deg2rad(90 + fov_v_s)
    phi_min = np.deg2rad(-fov_h / 2)
    phi_max = np.deg2rad(fov_h / 2)

    theta = np.linspace(theta_min, theta_max, n_vertical_final)
    phi = np.linspace(phi_min, phi_max, n_equator_final)
    theta, phi = np.meshgrid(theta, phi)

    x = R * np.sin(theta) * np.cos(phi)
    y = R * np.sin(theta) * np.sin(phi)
    z = R * np.cos(theta)

    # =============================
    # Z 對齊：最低點 = bottom_edge_height
    # =============================
    z_min = float(np.min(z))
    z_shift = float(bottom_edge_height) - z_min
    z = z + z_shift

    phi_eq = np.linspace(phi_min, phi_max, 400)
    theta_eq = np.deg2rad(90)
    x_eq = R * np.sin(theta_eq) * np.cos(phi_eq)
    y_eq = R * np.sin(theta_eq) * np.sin(phi_eq)
    z_eq = (R * np.cos(theta_eq) * np.ones_like(phi_eq)) + z_shift

    # =============================
    # 方向翻轉（XY 旋轉 180°）
    # =============================
    if flip_xy:
        x = -x
        y = -y
        x_eq = -x_eq
        y_eq = -y_eq

    fig = plt.figure(figsize=(6,6), dpi=120)
    ax = fig.add_subplot(111, projection="3d")

    # ===== 球面 =====
    ax.plot_surface(
        x, y, z,
        color="lightblue",
        edgecolor="gray",
        linewidth=0.2,
        alpha=0.85
    )
    ax.plot(x_eq, y_eq, z_eq, linewidth=2.0)

    # ===== 垂直分割線 =====
    phi_lines = np.linspace(phi_min, phi_max, n_equator_final + 1)
    for p in phi_lines:
        th_line = np.linspace(theta_min, theta_max, 200)
        gx = R * np.sin(th_line) * np.cos(p)
        gy = R * np.sin(th_line) * np.sin(p)
        gz = (R * np.cos(th_line)) + z_shift
        if flip_xy:
            gx, gy = -gx, -gy
        ax.plot(gx, gy, gz, color="black", linewidth=0.5)

    # ===== 水平分割線 =====
    theta_lines = np.linspace(theta_min, theta_max, n_vertical_final + 1)
    for t in theta_lines:
        ph_line = np.linspace(phi_min, phi_max, 400)
        gx = R * np.sin(t) * np.cos(ph_line)
        gy = R * np.sin(t) * np.sin(ph_line)
        gz = (R * np.cos(t) * np.ones_like(ph_line)) + z_shift
        if flip_xy:
            gx, gy = -gx, -gy
        ax.plot(gx, gy, gz, color="black", linewidth=0.5)



    # =============================
    # 可選：Room Box（XY 置中，地面=0）
    # =============================
    def draw_room_box(ax, w, l, h):
        x0, x1 = -l / 2, l / 2
        y0, y1 = -w / 2, w / 2
        z0, z1 = 0.0, h

        corners = [
            (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
            (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
        ]

        edges = [
            (0,1),(1,2),(2,3),(3,0),
            (4,5),(5,6),(6,7),(7,4),
            (0,4),(1,5),(2,6),(3,7)
        ]

        for i, j in edges:
            ax.plot(
                [corners[i][0], corners[j][0]],
                [corners[i][1], corners[j][1]],
                [corners[i][2], corners[j][2]],
                color="#6C86B7",
                linewidth=1.0,
                alpha=0.8
            )

    # ✅ Room box
    if show_room_box and (room_w is not None) and (room_l is not None) and (room_h is not None):
        rw = float(room_w)
        rl = float(room_l)
        rh = float(room_h)

        draw_room_box(ax, rw, rl, rh)

        # =============================
        # ✅ Room dimension annotations (W/L/H)
        # 放在「畫完框」之後、「Fix aspect」之前
        # =============================
        if show_room_dims:
            off = 0.07
            x0, x1 = -rl / 2, rl / 2
            y0, y1 = -rw / 2, rw / 2
            z0 = 0.0

            y_dim = y0 - rw * off
            x_dim = x0 - rl * off

            # L (X方向)
            ax.text((x0 + x1) / 2, y_dim, z0,
                    f"L = {math.ceil(rl)} mm",
                    ha="center", va="top")

            # W (Y方向)
            ax.text(x_dim, (y0 + y1) / 2, z0,
                    f"W = {math.ceil(rw)} mm",
                    ha="right", va="center")

            # H (Z方向)
            ax.text(x_dim, y_dim, rh / 2,
                    f"H = {math.ceil(rh)} mm",
                    ha="right", va="center")

    # =============================
    # Fix aspect so sphere won't distort
    # =============================
    x_min, x_max = float(np.min(x)), float(np.max(x))
    y_min, y_max = float(np.min(y)), float(np.max(y))
    z_min, z_max = float(np.min(z)), float(np.max(z))

    if show_room_box and (room_w is not None) and (room_l is not None) and (room_h is not None):
        rw = float(room_w)
        rl = float(room_l)
        rh = float(room_h)

        x_min = min(x_min, -rl / 2)
        x_max = max(x_max, rl / 2)
        y_min = min(y_min, -rw / 2)
        y_max = max(y_max, rw / 2)
        z_min = min(z_min, 0.0)
        z_max = max(z_max, rh)

    pad = 0.05
    xr = x_max - x_min
    yr = y_max - y_min
    zr = z_max - z_min

    x_min -= xr * pad
    x_max += xr * pad
    y_min -= yr * pad
    y_max += yr * pad
    z_min -= zr * pad
    z_max += zr * pad


    ax.set_ylim(y_min, y_max)
    ax.set_zlim(z_min, z_max)

    ax.set_box_aspect([1,1,1])

    ax.set_axis_off()
    ax.view_init(elev=elev, azim=azim)

    # =============================
    # Front view height diagram
    # Display arrow = exact sphere height
    # Bottom arrow = proportional scale
    # =============================
    if show_height_dims:
        # ----- physical heights (mm)
        display_height_mm = (diameter / 2.0) * (
                math.sin(math.radians(fov_v_n_final)) +
                math.sin(math.radians(fov_v_s_final))
        )

        bhe_mm = float(bottom_edge_height)

        # ----- projection helper
        def proj_axes(x3, y3, z3):
            x2, y2, _ = proj3d.proj_transform(x3, y3, z3, ax.get_proj())
            xd, yd = ax.transData.transform((x2, y2))
            xa, ya = ax.transAxes.inverted().transform((xd, yd))
            return xa, ya

        xf = x.flatten()
        yf = y.flatten()
        zf = z.flatten()

        pts = [proj_axes(xf[i], yf[i], zf[i]) for i in range(len(xf))]

        xa = np.array([p[0] for p in pts])
        ya = np.array([p[1] for p in pts])

        # ----- sphere silhouette
        y_top = float(np.max(ya))
        y_bottom = float(np.min(ya))

        # ----- arrow X position
        x_dim = min(0.965, np.max(xa) + 0.04)

        # ----- proportional scaling
        display_len = y_top - y_bottom

        ratio = bhe_mm / display_height_mm

        bottom_len = display_len * ratio

        y_floor = y_bottom - bottom_len

        # ----- clamp
        def clamp(v):
            return max(0.02, min(0.98, v))

        y_top = clamp(y_top)
        y_bottom = clamp(y_bottom)
        y_floor = clamp(y_floor)

        tr = ax.transAxes

        arrow_kw = dict(
            arrowstyle="<->",
            linewidth=1.5,
            color="black",
            shrinkA=0,
            shrinkB=0,
            mutation_scale=12
        )

        bbox_kw = dict(
            boxstyle="round,pad=0.2",
            fc="white",
            ec="none",
            alpha=0.9
        )

        # ----- floor line
        ax.plot(
            [x_dim - 0.08, x_dim + 0.02],
            [y_floor, y_floor],
            transform=tr,
            color="black",
            linewidth=3
        )

        # ----- display arrow
        ax.annotate(
            "",
            xy=(x_dim, y_top),
            xytext=(x_dim, y_bottom),
            xycoords=tr,
            textcoords=tr,
            arrowprops=arrow_kw
        )

        ax.text2D(
            x_dim + 0.015,
            (y_top + y_bottom) / 2,
            f"{int(round(display_height_mm))}mm",
            transform=tr,
            fontsize=13,
            bbox=bbox_kw
        )

        # ----- bottom arrow
        ax.annotate(
            "",
            xy=(x_dim, y_bottom),
            xytext=(x_dim, y_floor),
            xycoords=tr,
            textcoords=tr,
            arrowprops=arrow_kw
        )

        ax.text2D(
            x_dim + 0.015,
            (y_floor + y_bottom) / 2,
            f"{int(round(bhe_mm))}mm",
            transform=tr,
            fontsize=13,
            bbox=bbox_kw
        )



    plt.title(title)
    plt.subplots_adjust(
        left=0.06,
        right=0.94,
        bottom=0.06,
        top=0.92
    )
    return fig


