import logging
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

logger = logging.getLogger(__name__)


class WebAutomator:
    def __init__(self, headless: bool = True, timeout: int = 10, screenshots_dir: str = "./screenshots"):
        self.timeout = timeout
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options,
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.quit()

    def quit(self):
        if self.driver:
            self.driver.quit()

    def go(self, url: str):
        logger.info(f"Navegando para {url}")
        self.driver.get(url)

    def wait_for(self, selector: str, by: str = By.CSS_SELECTOR) -> object:
        return WebDriverWait(self.driver, self.timeout).until(
            EC.presence_of_element_located((by, selector))
        )

    def safe_find(self, by: str, selector: str):
        try:
            return self.driver.find_element(by, selector)
        except Exception:
            return None

    def type_into(self, selector: str, text: str, by: str = By.CSS_SELECTOR):
        element = self.wait_for(selector, by)
        element.clear()
        element.send_keys(text)

    def click(self, selector: str, by: str = By.CSS_SELECTOR):
        element = self.wait_for(selector, by)
        element.click()

    def screenshot_on_error(self, name: str = "error"):
        path = self.screenshots_dir / f"{name}_{int(time.time())}.png"
        self.driver.save_screenshot(str(path))
        logger.error(f"Screenshot salvo em {path}")
        return str(path)
