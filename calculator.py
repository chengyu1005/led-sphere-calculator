# calculator.py
import math
import numpy as np
import matplotlib.pyplot as plt


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

        # power
        "R_current_mA": R_current,
        "G_current_mA": G_current,
        "B_current_mA": B_current,
        "LED_power_W": LED_power,
        "system_power_W": system_power,
        "total_power_W": total_power/1000,
    }


def make_sphere_fig(diameter, fov_h, fov_v_n_final, fov_v_s_final, n_equator_final, n_vertical_final, elev, azim, title):
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

    phi_eq = np.linspace(phi_min, phi_max, 400)
    theta_eq = np.deg2rad(90)
    x_eq = R * np.sin(theta_eq) * np.cos(phi_eq)
    y_eq = R * np.sin(theta_eq) * np.sin(phi_eq)
    z_eq = R * np.cos(theta_eq) * np.ones_like(phi_eq)

    fig = plt.figure(figsize=(7, 7))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(x, y, z, color="lightblue", edgecolor="gray", linewidth=0.2, alpha=0.85)
    ax.plot(x_eq, y_eq, z_eq, linewidth=2.0)

    phi_lines = np.linspace(phi_min, phi_max, n_equator_final + 1)
    for p in phi_lines:
        th_line = np.linspace(theta_min, theta_max, 200)
        ax.plot(R * np.sin(th_line) * np.cos(p),
                R * np.sin(th_line) * np.sin(p),
                R * np.cos(th_line),
                color="black", linewidth=0.5)

    theta_lines = np.linspace(theta_min, theta_max, n_vertical_final + 1)
    for t in theta_lines:
        ph_line = np.linspace(phi_min, phi_max, 400)
        ax.plot(R * np.sin(t) * np.cos(ph_line),
                R * np.sin(t) * np.sin(ph_line),
                R * np.cos(t) * np.ones_like(ph_line),
                color="black", linewidth=0.5)

    ax.set_box_aspect([1, 1, 1])
    ax.set_axis_off()
    ax.view_init(elev=elev, azim=azim)
    plt.title(title)
    return fig
