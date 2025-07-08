import json
import os
import time
import random
import re
import requests
import ddddocr
from PIL import Image
import io
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

def load_settings():
    settings_path = os.path.join(os.path.dirname(__file__), 'settings.json')
    with open(settings_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_url_from_style(style_str):
    """
    從 style 屬性中提取圖片 URL
    """
    match = re.search(r'url\("(.*?)"\)', style_str)
    if match:
        return match.group(1)
    return None

def run():
    settings = load_settings()["cityline"]
    print("[Cityline] 讀取設定檔...")
    print(f"[Cityline] 帳號: {settings['username']}")
    print(f"[Cityline] 活動網址: {settings['event_url']}")

    print("[Cityline] 啟動瀏覽器...")
    driver = uc.Chrome()
    driver.get(settings['event_url'])
    wait = WebDriverWait(driver, 20)
    time.sleep(2)

    # --- ddddocr滑塊驗證 ---
    try:
        print("[Cityline] 偵測到滑塊驗證碼，啟動 ddddocr 分析...")
        time.sleep(5) # 等待 iframe 和圖片完全加載

        # 首先檢查是否存在 iframe
        try:
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, 'tcaptcha_iframe_dy')))
            print("[Cityline] 已成功切換到 iframe。")
            iframe_mode = True
        except:
            print("[Cityline] 未找到 tcaptcha_iframe_dy，將在主頁面尋找元素。")
            iframe_mode = False

        # 獲取背景圖和滑塊圖的 URL
        print("[Cityline] 正在定位背景圖...")
        bg_img_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#slideBg, .JDJRV-bigimg > img')))
        print("[Cityline] 已成功定位背景圖。")
        print("[Cityline] 正在定位滑塊圖...")
        slider_img_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[style*='img_index=0'], .JDJRV-smallimg > img")))
        print("[Cityline] 已成功定位滑塊圖。")
        
        # 測量網頁上背景圖的實際顯示寬度
        element_width = bg_img_element.size['width']

        # 根據不同網站結構獲取 URL
        bg_url = bg_img_element.get_attribute('src') or get_url_from_style(bg_img_element.get_attribute('style'))
        slider_url = slider_img_element.get_attribute('src') or get_url_from_style(slider_img_element.get_attribute('style'))

        print(f"[Cityline] 背景圖 URL: {bg_url}")
        print(f"[Cityline] 滑塊圖 URL: {slider_url}")
        print("[Cityline] 已獲取驗證碼圖片 URL。")

        # 下載圖片
        print("[Cityline] 正在下載驗證碼圖片...")
        bg_response = requests.get(bg_url)
        slider_response = requests.get(slider_url)
        
        # 初始化 ddddocr
        ocr = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)

        # 進行滑塊匹配
        print("[Cityline] 正在使用 ddddocr 進行滑塊匹配...")
        res = ocr.slide_match(slider_response.content, bg_response.content, simple_target=True)
        target_x = res['target'][0]
        print(f"[Cityline] ddddocr 識別出的目標位置 (原始像素): {target_x}px")

        # 獲取背景圖原始寬度
        bg_image = Image.open(io.BytesIO(bg_response.content))
        original_bg_width = bg_image.width
        print(f"[Cityline] 圖片原始寬度: {original_bg_width}px")
        print(f"[Cityline] 網頁元素寬度: {element_width}px")

        # 根據網頁顯示大小進行縮放
        scale = element_width / original_bg_width
        distance = target_x * scale
        print(f"[Cityline] 座標縮放比例: {scale:.4f}")
        print(f"[Cityline] 換算出的滑動距離為: {distance:.2f}px")

        # 四捨五入最終距離
        distance = round(distance)
        print(f"[Cityline] 四捨五入後的最終滑動距離: {distance}px")

        # 定位滑塊控制柄
        print("[Cityline] 正在定位滑塊控制柄...")
        slider_handle = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.tc-slider-normal, .JDJRV-slide-btn')))
        print("[Cityline] 已成功定位滑塊控制柄。")

        # 執行人性化拖曳
        action = ActionChains(driver)
        action.click_and_hold(slider_handle)

        # 根據距離決定步數
        if distance < 50:
            num_steps = random.randint(2, 4)
        else:
            num_steps = random.randint(5, 10)

        # 生成隨機步長
        horizontal_steps = []
        remaining_distance = distance
        for i in range(num_steps - 1):
            max_step = remaining_distance - (num_steps - 1 - i) * 1 # 確保至少 1px 給剩餘步數
            if max_step <= 0:
                horizontal_steps.append(remaining_distance)
                remaining_distance = 0
                break
            step = random.uniform(1, max_step)
            horizontal_steps.append(step)
            remaining_distance -= step
        horizontal_steps.append(remaining_distance) # 將剩餘距離作為最後一步

        for dx in horizontal_steps:
            dy = random.randint(-3, 3) # 輕微的垂直偏移
            action.move_by_offset(dx, dy)
            action.pause(random.uniform(0.05, 0.15)) # 隨機的短暫停頓

        action.release().perform()

        print("[Cityline] 已根據計算結果嘗試自動滑動驗證碼。")
        if iframe_mode:
            driver.switch_to.default_content()
        time.sleep(5)

    except Exception as e:
        print(f"[Cityline] 自動滑動驗證碼失敗: {e}")
        if 'iframe_mode' in locals() and iframe_mode:
            driver.switch_to.default_content()
        print("[Cityline] 請手動完成驗證，完成後按 Enter 繼續...")
        input()

    # ...後續流程...
    print("[Cityline] 登入成功或驗證完成，請檢查頁面。")
    time.sleep(10)
    driver.quit()

if __name__ == "__main__":
    run()