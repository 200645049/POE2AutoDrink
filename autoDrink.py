import pyautogui
import numpy as np
import time
from datetime import datetime
import os
import sys
import ctypes
import cv2

# ---------------------- 配置参数 ----------------------
# 生命球参数
HEALTH_CENTER = (186, 1301)  # 圆心坐标(x, y)
HEALTH_RADIUS = 80  # 半径

# 生命球颜色范围（HSV）
# 红色分两段：0~10 和 160~179
HEALTH_HEALTHY_MIN1 = np.array([0, 101, 51])   # H, S, V
HEALTH_HEALTHY_MAX1 = np.array([10, 224, 175])
HEALTH_HEALTHY_MIN2 = np.array([160, 101, 51])
HEALTH_HEALTHY_MAX2 = np.array([179, 224, 175])
HEALTH_THRESHOLD = 0.6

# 魔力球参数
MANA_CENTER = (2379, 1301)
MANA_RADIUS = 80

# 魔力球颜色范围（HSV 蓝色）
MANA_HEALTHY_MIN = np.array([98, 81, 51])
MANA_HEALTHY_MAX = np.array([116, 227, 203])
MANA_THRESHOLD = 0.2

# 喝药按键
HEALTH_POTION_KEY = '1'
MANA_POTION_KEY = '2'

# 检测间隔
CHECK_INTERVAL = 0.5

# 截图设置
SAVE_SCREENSHOTS = False
SCREENSHOT_INTERVAL = 5
LAST_SCREENSHOT_TIME = 0


# 检查是否以管理员身份运行
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


# ---------------------- 核心函数 ----------------------
def get_circular_color_data(center, radius, hsv_min, hsv_max, hsv_min2=None, hsv_max2=None, save_screenshot=False, name="unknown"):
    """获取圆形区域内的颜色数据（HSV），支持保存截图"""
    x, y = center
    region = (x - radius, y - radius, radius * 2, radius * 2)

    # 截图并转成数组（RGB）
    screenshot = pyautogui.screenshot(region=region)
    img_array = np.array(screenshot)

    # 转换为 HSV
    hsv_img = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)

    # 圆形掩码
    height, width, _ = hsv_img.shape
    y_indices, x_indices = np.ogrid[:height, :width]
    center_x, center_y = radius, radius
    dist_from_center = np.sqrt((x_indices - center_x) ** 2 + (y_indices - center_y) ** 2)
    mask = dist_from_center <= radius

    # inRange 判断
    mask1 = cv2.inRange(hsv_img, hsv_min, hsv_max)
    if hsv_min2 is not None and hsv_max2 is not None:  # 处理红色两段
        mask2 = cv2.inRange(hsv_img, hsv_min2, hsv_max2)
        mask_total = cv2.bitwise_or(mask1, mask2)
    else:
        mask_total = mask1

    # 应用圆形掩码
    mask_total = mask_total & mask.astype(np.uint8) * 255

    in_range_pixels = hsv_img[mask_total > 0]
    all_pixels = hsv_img[mask]

    ratio = np.sum(mask_total > 0) / np.sum(mask)

    # 保存截图
    if save_screenshot:
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshots/{name}_circle_{timestamp}.png"
        screenshot.save(filename)
        print(f"已保存截图: {filename}")

    return {
        'ratio': ratio,
        'in_range_pixels': in_range_pixels,
        'all_pixels': all_pixels,
        'screenshot': screenshot
    }


def check_health_need(save_screenshot=False):
    health_data = get_circular_color_data(
        HEALTH_CENTER, HEALTH_RADIUS,
        HEALTH_HEALTHY_MIN1, HEALTH_HEALTHY_MAX1,
        hsv_min2=HEALTH_HEALTHY_MIN2, hsv_max2=HEALTH_HEALTHY_MAX2,
        save_screenshot=save_screenshot,
        name="health"
    )
    return health_data['ratio'] < HEALTH_THRESHOLD, health_data


def check_mana_need(save_screenshot=False):
    mana_data = get_circular_color_data(
        MANA_CENTER, MANA_RADIUS,
        MANA_HEALTHY_MIN, MANA_HEALTHY_MAX,
        save_screenshot=save_screenshot,
        name="mana"
    )
    return mana_data['ratio'] < MANA_THRESHOLD, mana_data


def get_color_stats(pixels):
    if len(pixels) == 0:
        return "无数据"
    min_h, min_s, min_v = np.min(pixels, axis=0)
    max_h, max_s, max_v = np.max(pixels, axis=0)
    avg_h, avg_s, avg_v = np.mean(pixels, axis=0).astype(int)
    return (f"HSV范围: H[{min_h}-{max_h}], S[{min_s}-{max_s}], V[{min_v}-{max_v}] "
            f"平均: ({avg_h}, {avg_s}, {avg_v})")


def auto_drink():
    global LAST_SCREENSHOT_TIME
    print("圆形状态条自动喝药程序启动 (HSV版)，按Ctrl+C停止")

    try:
        while True:
            sleep = True
            current_time = time.time()
            save_screenshots = SAVE_SCREENSHOTS and (current_time - LAST_SCREENSHOT_TIME >= SCREENSHOT_INTERVAL)

            # 检查生命状态
            need_health, health_data = check_health_need(save_screenshot=save_screenshots)
            health_ratio = health_data['ratio']
            health_color_stats = get_color_stats(health_data['in_range_pixels'])

            # 检查魔力状态
            need_mana, mana_data = check_mana_need(save_screenshot=save_screenshots)
            mana_ratio = mana_data['ratio']
            mana_color_stats = get_color_stats(mana_data['in_range_pixels'])

            if save_screenshots:
                LAST_SCREENSHOT_TIME = current_time

            print(f"\n[状态更新] 生命占比: {health_ratio:.2f} | 魔力占比: {mana_ratio:.2f}")
            print(f"生命颜色: {health_color_stats}")
            print(f"魔力颜色: {mana_color_stats}")

            if need_health:
                sleep = False
                pyautogui.press(HEALTH_POTION_KEY)
                print(f"喝生命药！当前生命占比: {health_ratio:.2f}")
                time.sleep(0.5)

            if need_mana:
                sleep = False
                pyautogui.press(MANA_POTION_KEY)
                print(f"喝魔力药！当前魔力占比: {mana_ratio:.2f}")
                time.sleep(1)

            if sleep:
                time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("\n程序已停止")


if __name__ == "__main__":
    if not is_admin():
        print("请求管理员权限...")
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit()

    auto_drink()
