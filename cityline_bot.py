import json
import os
import time
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# We need selenium-wire to intercept network requests. It's an extension for selenium.
# Please make sure to run: pip install selenium-wire
# We will also continue to use undetected_chromedriver to better disguise the browser.
import seleniumwire.undetected_chromedriver as uc

class CitylineBot:
    def __init__(self):
        """
        Initializes the Bot, loads settings, and creates a requests.Session to manage cookies.
        """
        self.settings = self._load_settings()
        self.session = requests.Session()
        self.driver = None  # Initialize driver as a class attribute
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Referer": self.settings['event_url']
        })
        print("[Cityline] Bot initialized.")

    def _load_settings(self):
        """
        Loads settings from settings.json.
        """
        settings_path = os.path.join(os.path.dirname(__file__), 'settings.json')
        with open(settings_path, 'r', encoding='utf-8') as f:
            return json.load(f)['cityline']

    def _get_google_login_token(self):
        """
        Uses selenium-wire to launch a browser, lets the user log in manually,
        and intercepts the accessToken from the Google login process.
        The browser will remain open.
        """
        print("[Cityline] Launching browser for manual login...")
        print("[Cityline] Please manually click login and complete the Google login process in the popup window.")
        print("[Cityline] The script will automatically listen for and capture the token after successful login...")

        # Configure selenium-wire options
        selenium_wire_options = {
            'verify_ssl': False,
            'disable_capture': False,
        }

        # Configure Chrome options
        chrome_options = uc.ChromeOptions()
        chrome_options.add_argument('--ignore-certificate-errors')
        
        # Use selenium-wire's undetected_chromedriver with the specified options
        self.driver = uc.Chrome(
            options=chrome_options,
            seleniumwire_options=selenium_wire_options,
            version_main=145
        )
        
        try:
            # Go to the event page to trigger the login process
            self.driver.get(self.settings['event_url'])

            # Wait for the request to Cityline's Google login API
            request = self.driver.wait_for_request(
                '/api/login/google.do',
                timeout=300
            )
            
            print("[Cityline] Successfully intercepted login request!")

            body = request.body.decode('utf-8')
            payload = json.loads(body)
            access_token = payload.get('accessToken')

            if not access_token:
                print("[Cityline] Error: accessToken not found in the intercepted request.")
                return None

            print(f"[Cityline] Successfully acquired accessToken!")
            
            print("[Cityline] Syncing cookies from browser...")
            cookies = self.driver.get_cookies()
            for cookie in cookies:
                self.session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
            
            print("[Cityline] Cookies synced.")
            return access_token

        except Exception as e:
            print(f"[Cityline] An error occurred while acquiring accessToken: {e}")
            return None
        # Note: We removed driver.quit() from the finally block to keep the browser open

    def login(self):
        """
        Executes the complete login flow.
        """
        access_token = self._get_google_login_token()

        if not access_token:
            print("[Cityline] Login failed: Could not acquire accessToken.")
            return False

        print("[Cityline] Verifying login status using requests...")
        user_api_url = "https://www.cityline.com/api/user.do"
        
        try:
            response = self.session.get(user_api_url)
            response.raise_for_status()
            
            user_info = response.json().get("userInfo")
            if user_info and user_info.get("loginId"):
                print(f"[Cityline] Login successful! Welcome, {user_info.get('name')} ({user_info.get('loginId')})")
                return True
            else:
                print("[Cityline] Login verification failed, could not retrieve user information.")
                print(f"[Cityline] Response: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"[Cityline] Login verification request failed: {e}")
            return False

    def run(self):
        """
        Executes the main bot flow.
        """
        print("=================================================")
        print(f"[Cityline] Target Event: {self.settings['event_url']}")
        print("=================================================")
        
        if self.login():
            print("\n================ STARTING AUTOMATED PURCHASE ================")
            print("[Cityline] Login successful. The browser will remain open.")
            print(f"[Cityline] Target Date keyword: {self.settings.get('target_date', 'ANY')}")
            print(f"[Cityline] Target Price keyword: {self.settings.get('target_price', 'ANY')}")
            print(f"[Cityline] Target Ticket Qty: {self.settings.get('ticket_qty', 2)}")
            
            # Go back to event page in case login redirects
            self.driver.get(self.settings['event_url'])

            if self._wait_for_sale_start():
                if self._select_performance():
                    if self._select_tickets():
                        self._submit_order()

            print("\n[Cityline] Script paused for manual verification or payment.")
            print(">>> Please complete any reCAPTCHA or payment on the browser if needed. <<<")
            input(">>> Press Enter in this terminal to close the browser and exit...")

        else:
            print("[Cityline] Login failed. Exiting program.")
        
        # Ensure the browser is closed before the program exits
        if self.driver:
            print("[Cityline] Closing browser...")
            self.driver.quit()
            print("[Cityline] Browser closed.")

    def _wait_for_sale_start(self):
        print("[Cityline] Waiting for sale to start...")
        while True:
            try:
                # Basic check for "Buy", "Purchase" or "購票" buttons on event page.
                buy_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), '購票') or contains(text(), 'Buy') or contains(text(), 'Purchase')]")
                links = self.driver.find_elements(By.XPATH, "//a[contains(text(), '購票') or contains(text(), 'Buy') or contains(text(), 'Purchase')]")
                buy_classes = self.driver.find_elements(By.CSS_SELECTOR, ".btn-buy, .buy-btn")
                
                if buy_buttons or links or buy_classes:
                    print("[Cityline] Sale has started! Purchase element found.")
                    return True
                
                print("[Cityline] Not yet open or no buttons found. Refreshing...")
                time.sleep(1) # Refresh interval
                self.driver.refresh()
            except Exception as e:
                print(f"[Cityline] Error checking for sale status: {e}")
                time.sleep(1)

    def _select_performance(self):
        print("[Cityline] Attempting to select performance...")
        target_date = self.settings.get('target_date', '')
        try:
            time.sleep(1) # Let DOM stabilize
            if target_date and target_date != "ANY":
                xpath = f"//*[contains(text(), '{target_date}')]/following::button[contains(text(), '購票') or contains(text(), 'Buy')][1]"
            else:
                xpath = "(//button[contains(text(), '購票') or contains(text(), 'Buy')])[1]"
                
            btn = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            self.driver.execute_script("arguments[0].click();", btn)
            print(f"[Cityline] Clicked performance related to target: {target_date or 'first available'}")
            return True
        except Exception:
            try:
                print("[Cityline] Button not found, trying anchor links...")
                if target_date and target_date != "ANY":
                    xpath_a = f"//*[contains(text(), '{target_date}')]/following::a[contains(text(), '購票') or contains(text(), 'Buy')][1]"
                else:
                    xpath_a = "(//a[contains(text(), '購票') or contains(text(), 'Buy')])[1]"
                btn = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath_a)))
                self.driver.execute_script("arguments[0].click();", btn)
                print("[Cityline] Clicked performance link.")
                return True
            except Exception as e2:
                print(f"[Cityline] Failed to automatically select performance (possibly queue system or popup). Details: {e2}")
                return True

    def _select_tickets(self):
        print("[Cityline] Selecting ticket price and quantity...")
        target_price = self.settings.get('target_price', '')
        ticket_qty = str(self.settings.get('ticket_qty', 2))
        
        try:
            dropdowns = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "select"))
            )
            
            selected = False
            if target_price and target_price != "ANY":
                print(f"[Cityline] Looking for row with price '{target_price}'...")
                for select in dropdowns:
                    parent_text = ""
                    for xpath in ["./ancestor::tr", "./ancestor::li", "./ancestor::div[contains(@class, 'row')]"]:
                        try:
                            parent_text = select.find_element(By.XPATH, xpath).text
                            if parent_text: break
                        except: pass
                            
                    if target_price in parent_text:
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", select)
                        self._set_select_value(select, ticket_qty)
                        selected = True
                        break
                        
            if not selected and dropdowns:
                print("[Cityline] Target price specific row not found. Selecting the first available active dropdown...")
                for select in dropdowns:
                    if select.is_displayed() and select.is_enabled():
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", select)
                        self._set_select_value(select, ticket_qty)
                        selected = True
                        break

            print(f"[Cityline] Successfully selected {ticket_qty} tickets." if selected else "[Cityline] Could not find any valid quantity dropdowns.")
            return True

        except Exception as e:
            print(f"[Cityline] Ticket selection timeout/error. Likely in Waiting Room queue. Do not worry. Error: {e}")
            return True

    def _set_select_value(self, select_element, value):
        for option in select_element.find_elements(By.TAG_NAME, 'option'):
            if option.text.strip() == value or option.get_attribute('value') == value:
                option.click()
                return

    def _submit_order(self):
        print("[Cityline] Submitting order...")
        try:
            submit_xpath = "(//button[contains(text(), '加入購物車') or contains(text(), 'Add') or contains(text(), '確認') or contains(text(), 'Confirm')])[1]"
            btn = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.XPATH, submit_xpath)))
            self.driver.execute_script("arguments[0].click();", btn)
            print("[Cityline] Found and clicked submit/add to cart button!")
        except Exception as e:
            print(f"[Cityline] Auto submit button not found, please click manually if on page. Error: {e}")

    def api_get_performances(self, event_hash, event_id):
        """
        利用 API 取得該活動所有可用的場次資訊
        :param event_hash: 例如 'MUSICUNLIVEM-fc2f5379-0d26-3c92-b5b8-77f2fff43aa7'
        :param event_id: 例如 '54832'
        :return: JSON 格式的場次資料或 None
        """
        timestamp = int(time.time() * 1000)
        api_url = f"https://venue.cityline.com/utsvInternet/activity/api/{event_hash}/event/{event_id}/performances?_={timestamp}"
        
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7,ja;q=0.6,zh-CN;q=0.5",
            "Referer": f"https://venue.cityline.com/utsvInternet/{event_hash.split('-')[0]}/eventDetail?event={event_id}",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": self.session.headers.get("User-Agent")
        }

        print(f"[Cityline API] 正在取得此活動 ({event_id}) 的所有場次資訊...")
        try:
            response = self.session.get(api_url, headers=headers)
            if response.status_code == 200:
                print("[Cityline API] 成功取得場次資料！")
                return response.json()
            else:
                print(f"[Cityline API] 取得場次失敗，HTTP 狀態碼: {response.status_code}")
        except Exception as e:
            print(f"[Cityline API] 取得場次發生例外錯誤: {e}")
        return None

    def api_get_pricezones(self, event_hash, event_id, perform_id):
        """
        利用 API 取得特定場次下所有票價區塊資訊
        :param event_hash: 例如 'MUSICUNLIVEM-fc2f5379-0d26-3c92-b5b8-77f2fff43aa7'
        :param event_id: 例如 '54832'
        :param perform_id: 場次的 ID，例如 '90681'
        :return: JSON 格式的票價區資料或 None
        """
        timestamp = int(time.time() * 1000)
        api_url = f"https://venue.cityline.com/utsvInternet/activity/api/{event_hash}/event/{event_id}/performance/{perform_id}/pricezones?_={timestamp}"
        
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7,ja;q=0.6,zh-CN;q=0.5",
            "Referer": f"https://venue.cityline.com/utsvInternet/{event_hash.split('-')[0]}/performance?event={event_id}&perfId={perform_id}",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": self.session.headers.get("User-Agent")
        }

        print(f"[Cityline API] 正在取得此場次 ({perform_id}) 的票價區資訊...")
        try:
            response = self.session.get(api_url, headers=headers)
            if response.status_code == 200:
                print("[Cityline API] 成功取得票價區資料！")
                return response.json()
            else:
                print(f"[Cityline API] 取得票價區失敗，HTTP 狀態碼: {response.status_code}")
        except Exception as e:
            print(f"[Cityline API] 取得票價區發生例外錯誤: {e}")
        return None


def run():
    bot = CitylineBot()
    bot.run()

if __name__ == '__main__':
    run()