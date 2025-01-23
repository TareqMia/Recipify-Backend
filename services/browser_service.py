from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import os

class BrowserService:
    def __init__(self):
        self.options = Options()
        self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(options=self.options)
        
    def get_youtube_cookies(self):
        # Login to YouTube first
        self.driver.get('https://accounts.google.com')
        # ... handle login ...
        
        # Get cookies after login
        self.driver.get('https://youtube.com')
        cookies = self.driver.get_cookies()
        
        # Save cookies to file
        cookie_file = 'youtube_cookies.txt'
        with open(cookie_file, 'w') as f:
            for cookie in cookies:
                f.write(f"{cookie['domain']}\tTRUE\t{cookie['path']}\t"
                       f"{'TRUE' if cookie['secure'] else 'FALSE'}\t{cookie['expiry']}\t"
                       f"{cookie['name']}\t{cookie['value']}\n")
        
        return cookie_file 