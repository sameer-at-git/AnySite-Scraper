from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import time


def fetch_html(url: str, timeout: int = 30, headless: bool = True) -> str:
    if not url or not isinstance(url, str):
        raise ValueError("Invalid URL provided")
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(timeout)
        driver.get(url)
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2)
        html_content = driver.page_source
        return html_content
    except TimeoutException:
        raise TimeoutException(f"Page failed to load within {timeout} seconds")
    except WebDriverException as e:
        raise WebDriverException(f"WebDriver error: {str(e)}")
    finally:
        if driver:
            driver.quit()


def fetch_html_with_info(url: str, timeout: int = 30, headless: bool = True) -> dict:
    if not url or not isinstance(url, str):
        raise ValueError("Invalid URL provided")
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(timeout)
        driver.get(url)
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2)
        html_content = driver.page_source
        page_title = driver.title
        final_url = driver.current_url
        return {
            'html': html_content,
            'title': page_title,
            'url': final_url
        }
    except TimeoutException:
        raise TimeoutException(f"Page failed to load within {timeout} seconds")
    except WebDriverException as e:
        raise WebDriverException(f"WebDriver error: {str(e)}")
    finally:
        if driver:
            driver.quit()
