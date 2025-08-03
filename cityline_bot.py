import json
import os
import time
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 我們需要 selenium-wire 來攔截網路請求，它是一個 selenium 的擴充
# 請務必先執行: pip install selenium-wire
# 同時，我們繼續使用 undetected_chromedriver 來更好地偽裝瀏覽器
import seleniumwire.undetected_chromedriver as uc

class CitylineBot:
    def __init__(self):
        """
        初始化 Bot，載入設定並建立一個 requests.Session 來管理 cookies。
        """
        self.settings = self._load_settings()
        self.session = requests.Session()
        # 更新 User-Agent，讓 requests 的請求看起來更像真實瀏覽器
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Referer": self.settings['event_url']
        })
        print("[Cityline] Bot 初始化完成。")

    def _load_settings(self):
        """
        從 settings.json 載入設定。
        """
        settings_path = os.path.join(os.path.dirname(__file__), 'settings.json')
        with open(settings_path, 'r', encoding='utf-8') as f:
            return json.load(f)['cityline']

    def _get_google_login_token(self):
        """
        使用 selenium-wire 啟動瀏覽器，讓使用者手動登入，並從中攔截 Google 登入的 accessToken。
        這是整個混合模式最關鍵的一步。
        """
        print("[Cityline] 啟動瀏覽器以進行手動登入...")
        print("[Cityline] 請在彈出的瀏覽器視窗中，手動點擊登入並完成 Google 登入流程。")
        print("[Cityline] 程式將會自動監聽並捕獲登入成功後的 token...")

        # 設定 selenium-wire 的選項，讓它自動處理憑證問題
        seleniumwire_options = {
            'verify_ssl': False,
            'disable_capture': False, # 我們需要捕獲請求
        }

        # 設定 Chrome 選項，加入忽略憑證錯誤的參數
        chrome_options = uc.ChromeOptions()
        chrome_options.add_argument('--ignore-certificate-errors')
        
        # 使用 selenium-wire 的 undetected_chromedriver，並傳入設定
        driver = uc.Chrome(
            options=chrome_options,
            seleniumwire_options=seleniumwire_options
        )
        
        try:
            # 前往活動頁面，觸發登入流程
            driver.get(self.settings['event_url'])

            # 等待發送到 Cityline Google 登入 API 的請求
            # 這裡我們設置了長達 5 分鐘的超時，讓使用者有足夠的時間完成登入
            request = driver.wait_for_request(
                '/api/login/google.do',
                timeout=300
            )
            
            print("[Cityline] 成功攔截到登入請求！")

            # 從攔截到的請求中，解析出 body，再從 body 中提取 accessToken
            body = request.body.decode('utf-8')
            payload = json.loads(body)
            access_token = payload.get('accessToken')

            if not access_token:
                print("[Cityline] 錯誤：在攔截到的請求中未找到 accessToken。")
                return None

            print(f"[Cityline] 成功獲取 accessToken！")
            
            # 提取瀏覽器中的 cookies 並注入到我們的 requests.Session 中
            print("[Cityline] 正在從瀏覽器同步 Cookies...")
            cookies = driver.get_cookies()
            for cookie in cookies:
                self.session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
            
            print("[Cityline] Cookies 同步完成。")
            return access_token

        except Exception as e:
            print(f"[Cityline] 在獲取 accessToken 過程中發生錯誤: {e}")
            return None
        finally:
            # 無論成功或失敗，都關閉瀏覽器
            print("[Cityline] 關閉瀏覽器。")
            driver.quit()

    def login(self):
        """
        執行完整的登入流程。
        """
        # 步驟 1: 透過 selenium-wire 獲取 accessToken
        access_token = self._get_google_login_token()

        if not access_token:
            print("[Cityline] 登入失敗：未能獲取 accessToken。")
            return False

        # 步驟 2: 使用獲取到的 accessToken 和同步好的 cookies，透過 requests 驗證登入狀態
        # 雖然 accessToken 可能已經被瀏覽器發送過一次，但我們自己再次發送可以確保 session 狀態，並便於後續操作
        print("[Cityline] 正在使用 requests 驗證登入狀態...")
        
        # 檢查登入狀態的 API (這是我們之前分析出的第三個請求)
        user_api_url = "https://www.cityline.com/api/user.do"
        
        try:
            response = self.session.get(user_api_url)
            response.raise_for_status() # 如果請求失敗 (如 4xx, 5xx)，會拋出異常
            
            user_info = response.json().get("userInfo")
            if user_info and user_info.get("loginId"):
                print(f"[Cityline] 登入成功！歡迎，{user_info.get('name')} ({user_info.get('loginId')})")
                return True
            else:
                print("[Cityline] 登入驗證失敗，未能獲取用戶資訊。")
                print(f"[Cityline] 回應: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"[Cityline] 登入驗證請求失敗: {e}")
            return False

    def run(self):
        """
        執行機器人的主流程。
        """
        print("==============================================")
        print(f"[Cityline] 目標活動: {self.settings['event_url']}")
        print("==============================================")
        
        if self.login():
            # TODO: 在這裡繼續執行搶票的邏輯
            print("[Cityline] 登入成功，已準備就緒，可以開始分析搶票 API。")
            pass
        else:
            print("[Cityline] 登入失敗，程式結束。")


def run():
    bot = CitylineBot()
    bot.run()

if __name__ == '__main__':
    run()