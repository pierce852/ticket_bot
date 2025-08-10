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
            version_main=138  # Specify Chrome major version
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
            print("\n==================== FINAL RECONNAISSANCE ====================")
            print("[Cityline] Login successful. The browser will remain open.")
            print(">>> Please switch to the browser window now.")
            print(">>> Manually navigate to the page where you select ticket price and quantity.")
            print(">>> STOP on that page, right before you would click the final 'Confirm' button.")
            print("\n>>> Once on that page, use the F12 DevTools to find where the security tokens are stored.")
            print("    1. Check the 'Elements' tab: Search for hidden inputs like <input type=\"hidden\"> with values for 'challengeTs' or 'dataString'.")
            print("    2. Check the 'Console' tab: Type in possible JavaScript variable names like 'challengeTs', 'dataString', or inspect the 'window' object.")
            print("\n>>> Our goal is to find the location of these dynamic tokens.")
            input(">>> Press Enter here when you are finished investigating to close the browser...")

        else:
            print("[Cityline] Login failed. Exiting program.")
        
        # Ensure the browser is closed before the program exits
        if self.driver:
            print("[Cityline] Closing browser...")
            self.driver.quit()
            print("[Cityline] Browser closed.")


def run():
    bot = CitylineBot()
    bot.run()

if __name__ == '__main__':
    run()