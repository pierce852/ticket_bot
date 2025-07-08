import json
import os
import time
import random
import re
import requests
import cv2
import numpy as np
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

def load_settings():
    settings_path = os.path.join(os.path.dirname(__file__), 'settings.json')
    with open(settings_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_track(distance):
    def __ease_out_expo(step):
        return 1 if step == 1 else 1 - pow(2, -10 * step)
    tracks = []
    tracks.append([0, 0, random.randint(150, 250)])
    count = 30 + int(distance / 2)
    _x, _y = 0, 0
    for item in range(count):
        x = round(__ease_out_expo(item / count) * distance)
        t = random.randint(10, 20)
        if x == _x: continue
        tracks.append([x - _x, _y, t])
        _x = x
    if _x < distance: tracks.append([distance - _x, _y, random.randint(15, 25)])
    tracks.append([0, 0, random.randint(200, 300)])
    return tracks

def find_gap_by_screenshot_analysis(screenshot_bytes):
    image_np = np.asarray(bytearray(screenshot_bytes), dtype=np.uint8)
    image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    cv2.imwrite("captcha_edges.png", edges)
    print("[UrbTix] 已儲存驗證碼區域的邊緣檢測圖 captcha_edges.png")
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        area = cv2.contourArea(contour)
        x, y, w, h = cv2.boundingRect(contour)
        if area > 100 and w > 20 and h > 20 and x > 50:
             print(f"[UrbTix] 找到一個候選缺口，面積: {area}, 位置: x={x}")
             return x
    raise Exception("未能在截圖中通過輪廓分析找到缺口")

def run():
    settings = load_settings()["urbtix"]
    print(f"[UrbTix] 讀取設定檔... 帳號: {settings['username']}")

    print("[UrbTix] 啟動瀏覽器...")
    options = uc.ChromeOptions()
    # 移除 "enable-automation" 旗幟，降低被偵測風險
    options.add_argument('--disable-blink-features=AutomationControlled')

    driver = uc.Chrome(options=options)

    # 偽裝成真人瀏覽器
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    # 最大化瀏覽器視窗，降低被偵測風險
    driver.maximize_window()

    driver.get(settings['event_url'])
    wait = WebDriverWait(driver, 20)
    time.sleep(random.uniform(3, 5)) # 初始頁面載入後隨機延遲

    try:
        login_id_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[name="loginId"]')))
        login_id_input.click()
        login_id_input.send_keys(settings['username'])
        password_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[name="password"]')))
        password_input.click()
        password_input.send_keys(settings['password'])
        print("[UrbTix] 已自動填寫帳號密碼")
        login_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.login-button')))
        driver.execute_script("arguments[0].click();", login_btn)
        print("[UrbTix] 已自動點擊登入按鈕，等待驗證碼...")
        time.sleep(random.uniform(3, 5)) # 登入按鈕點擊後隨機延遲
    except Exception as e:
        print(f"[UrbTix] 自動填寫登入資訊失敗: {e}")
        driver.quit()
        return

    """
    try:
        print("[UrbTix] 偵測到滑塊驗證碼，啟動截圖分析方案...")
        time.sleep(5)
        try:
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, 'tcaptcha_iframe_dy')))
            print("[UrbTix] 已成功切換到 iframe。")
            iframe_mode = True
        except:
            print("[UrbTix] 未找到 iframe，將在主頁面尋找元素。")
            iframe_mode = False

        print("[UrbTix] 正在定位驗證碼背景圖元素...")
        bg_img_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#slideBg')))
        
        print("[UrbTix] 正在對驗證碼背景圖進行截圖...")
        screenshot_bytes = bg_img_element.screenshot_as_png
        with open("captcha_screenshot.png", "wb") as f:
            f.write(screenshot_bytes)
        print("[UrbTix] 已儲存驗證碼截圖 captcha_screenshot.png")

        print("[UrbTix] 正在使用截圖分析算法尋找目標位置...")
        target_x = find_gap_by_screenshot_analysis(screenshot_bytes)
        print(f"[UrbTix] 識別出的目標位置 (原始像素): {target_x}px")

        print("[UrbTix] 正在定位滑塊控制柄...")
        slider_handle = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.tc-slider-normal')))
        print("[UrbTix] 已成功定位滑塊控制柄。")

        # 關鍵修正：減去滑塊的初始偏移量，並加入一個小的隨機誤差
        initial_offset = slider_handle.size['width'] / 2
        distance = target_x - initial_offset - random.randint(5, 8)
        print(f"[UrbTix] 考慮初始偏移和隨機誤差後，最終滑動距離: {distance}px")

        action = ActionChains(driver)
        action.click_and_hold(slider_handle)
        tracks = generate_track(distance)
        print(f"[UrbTix] 生成的滑動軌跡: {tracks}")
        for dx, dy, dt in tracks:
            action.move_by_offset(xoffset=dx, yoffset=dy)
            action.pause(dt / 1000)
        action.release().perform()

        print("[UrbTix] 已根據計算結果嘗試自動滑動驗證碼。")
        if iframe_mode: driver.switch_to.default_content()
        time.sleep(5)

    except Exception as e:
        print(f"[UrbTix] 自動滑動驗證碼失敗: {e}")
        if 'iframe_mode' in locals() and iframe_mode: driver.switch_to.default_content()
        print("[UrbTix] 請手動完成驗證，完成後按 Enter 繼續...")
        input()
    """

    # --- 等待主頁載入 ---
    # WebDriverWait(driver, 10).until(
    #     EC.presence_of_element_located((By.CSS_SELECTOR, 'input.search[placeholder="關鍵字搜尋"]'))
    # )
    print("[UrbTix] 主頁已載入，檢查是否有 popup message...")

    # --- 檢查並自動關閉所有 popup message ---
    try:
        popup_found = False
        # 最多等3秒，每0.5秒檢查一次
        for _ in range(6):
            popup_close_buttons = driver.find_elements(By.CSS_SELECTOR, 'div.modal-wrapper.popup-message .close-icon[title="關閉"]')
            for btn in popup_close_buttons:
                if btn and btn.is_displayed() and btn.is_enabled():
                    print("[UrbTix] 偵測到 popup message，正在自動關閉...")
                    btn.click()
                    time.sleep(0.5)
                    print("[UrbTix] 已自動關閉 popup message。")
                    popup_found = True
            if popup_found:
                # 檢查是否還有其他 popup，若有則繼續關閉
                popup_found = False
                continue
            time.sleep(0.5)
    except Exception as e:
        print(f"[UrbTix] 處理 popup message 時發生錯誤: {e}")

    print("[UrbTix] 已完成 popup message 處理，請檢查頁面狀態。")
    time.sleep(5)
    # driver.quit()

if __name__ == "__main__":
    run()