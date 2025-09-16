import pyautogui
import numpy as np
import time
from datetime import datetime
import os
import sys
import ctypes

# ---------------------- 配置参数 ----------------------
# 生命球参数（圆心坐标和半径）
HEALTH_CENTER = (186, 1301)  # 圆心坐标(x, y)
HEALTH_RADIUS = 80  # 半径

# 生命球健康颜色范围（RGB）
HEALTH_HEALTHY_MIN = np.array([100, 0, 0])  # 最低健康红色值
HEALTH_HEALTHY_MAX = np.array([255, 50, 50])  # 最高健康红色值
HEALTH_THRESHOLD = 0.3  # 健康颜色占比低于此值喝药

# 魔力球参数
MANA_CENTER = (2379, 1301)  # 圆心坐标(x, y)
MANA_RADIUS = 80  # 半径

# 魔力球健康颜色范围（RGB）
MANA_HEALTHY_MIN = np.array([0, 0, 100])  # 最低健康蓝色值
MANA_HEALTHY_MAX = np.array([50, 110, 255])  # 最高健康蓝色值
MANA_THRESHOLD = 0.2  # 健康颜色占比低于此值喝药

# 喝药按键
HEALTH_POTION_KEY = '1'
MANA_POTION_KEY = '2'

# 检测间隔（秒）
CHECK_INTERVAL = 0.5

# 截图设置
SAVE_SCREENSHOTS = False  # 是否保存截图
SCREENSHOT_INTERVAL = 5  # 截图保存间隔（秒）
LAST_SCREENSHOT_TIME = 0  # 上次截图时间


# 检查是否以管理员身份运行
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


# ---------------------- 核心函数 ----------------------
def get_circular_color_data(center, radius, color_min, color_max, save_screenshot=False, name="unknown"):
    """获取圆形区域内的颜色数据，包括占比和实际RGB值范围，可保存截图"""
    # 计算需要截取的正方形区域（包含整个圆形）
    x, y = center
    region = (
        x - radius,  # 左上角x
        y - radius,  # 左上角y
        radius * 2,  # 宽度
        radius * 2  # 高度
    )

    # 截取区域
    screenshot = pyautogui.screenshot(region=region)

    # 保存截图（如果需要）
    if save_screenshot:
        # 创建截图目录（如果不存在）
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")

        # 生成带时间戳的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshots/{name}_circle_{timestamp}.png"
        screenshot.save(filename)
        print(f"已保存截图: {filename}")

    # 转换为数组
    img_array = np.array(screenshot)
    height, width, _ = img_array.shape

    # 创建圆形掩码（只保留圆形区域内的像素）
    y_indices, x_indices = np.ogrid[:height, :width]
    center_x, center_y = radius, radius  # 圆形在截取区域中的相对中心
    dist_from_center = np.sqrt((x_indices - center_x) ** 2 + (y_indices - center_y) ** 2)
    mask = dist_from_center <= radius  # 圆形内的像素为True

    # 提取圆形区域内的像素
    circular_pixels = img_array[mask]

    if len(circular_pixels) == 0:
        return {
            'ratio': 0.0,
            'in_range_pixels': [],
            'all_pixels': [],
            'screenshot': screenshot
        }

    # 判断每个像素是否在颜色范围内
    in_range = np.logical_and(
        np.all(circular_pixels >= color_min, axis=1),
        np.all(circular_pixels <= color_max, axis=1)
    )

    # 提取符合条件的像素和所有像素
    in_range_pixels = circular_pixels[in_range]
    all_pixels = circular_pixels

    # 计算占比
    ratio = np.sum(in_range) / len(circular_pixels)

    return {
        'ratio': ratio,
        'in_range_pixels': in_range_pixels,
        'all_pixels': all_pixels,
        'screenshot': screenshot
    }


def check_health_need(save_screenshot=False):
    """检查是否需要喝生命药"""
    health_data = get_circular_color_data(
        HEALTH_CENTER, HEALTH_RADIUS,
        HEALTH_HEALTHY_MIN, HEALTH_HEALTHY_MAX,
        save_screenshot=save_screenshot,
        name="health"
    )
    return health_data['ratio'] < HEALTH_THRESHOLD, health_data


def check_mana_need(save_screenshot=False):
    """检查是否需要喝魔力药"""
    mana_data = get_circular_color_data(
        MANA_CENTER, MANA_RADIUS,
        MANA_HEALTHY_MIN, MANA_HEALTHY_MAX,
        save_screenshot=save_screenshot,
        name="mana"
    )
    return mana_data['ratio'] < MANA_THRESHOLD, mana_data


def get_color_stats(pixels):
    """获取像素颜色的统计信息"""
    if len(pixels) == 0:
        return "无数据"

    # 计算RGB各通道的最小值、最大值和平均值
    min_r, min_g, min_b = np.min(pixels, axis=0)
    max_r, max_g, max_b = np.max(pixels, axis=0)
    avg_r, avg_g, avg_b = np.mean(pixels, axis=0).astype(int)

    return (f"RGB范围: R[{min_r}-{max_r}], G[{min_g}-{max_g}], B[{min_b}-{max_b}] "
            f"平均: ({avg_r}, {avg_g}, {avg_b})")


def auto_drink():
    """自动喝药主逻辑"""
    global LAST_SCREENSHOT_TIME
    print("圆形状态条自动喝药程序启动，按Ctrl+C停止")
    print(f"截图将保存到 {os.path.abspath('screenshots')} 目录")

    try:
        while True:
            current_time = time.time()
            # 判断是否需要保存截图
            save_screenshots = SAVE_SCREENSHOTS and (current_time - LAST_SCREENSHOT_TIME >= SCREENSHOT_INTERVAL)

            # 检查生命状态
            need_health, health_data = check_health_need(save_screenshot=save_screenshots)
            health_ratio = health_data['ratio']
            health_color_stats = get_color_stats(health_data['in_range_pixels'])

            # 检查魔力状态
            need_mana, mana_data = check_mana_need(save_screenshot=save_screenshots)
            mana_ratio = mana_data['ratio']
            mana_color_stats = get_color_stats(mana_data['in_range_pixels'])

            # 更新最后截图时间
            if save_screenshots:
                LAST_SCREENSHOT_TIME = current_time

            # 输出当前状态信息
            print(f"\n[状态更新] 生命占比: {health_ratio:.2f} | 魔力占比: {mana_ratio:.2f}")
            print(
                f"生命颜色: {health_color_stats} | 设定范围: {tuple(HEALTH_HEALTHY_MIN)} - {tuple(HEALTH_HEALTHY_MAX)}")
            print(f"魔力颜色: {mana_color_stats} | 设定范围: {tuple(MANA_HEALTHY_MIN)} - {tuple(MANA_HEALTHY_MAX)}")

            if need_health:
                pyautogui.press(HEALTH_POTION_KEY)
                print(f"喝生命药！当前生命健康颜色占比: {health_ratio:.2f}")
                time.sleep(1)  # 防止连续喝药

            if need_mana:
                pyautogui.press(MANA_POTION_KEY)
                print(f"喝魔力药！当前魔力健康颜色占比: {mana_ratio:.2f}")
                time.sleep(1)  # 防止连续喝药

            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("\n程序已停止")


if __name__ == "__main__":
    # 检查是否以管理员身份运行，如果不是则重新请求
    if not is_admin():
        print("请求管理员权限...")
        # 重新启动程序，请求管理员权限
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit()

    auto_drink()
