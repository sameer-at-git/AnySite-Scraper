from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
import os
import time
import shutil
import platform
import subprocess
import re


def get_chrome_path():
    """Get the Chrome/Chromium binary path for the current OS."""
    # Check if we're on Linux (Streamlit Cloud)
    if platform.system() == 'Linux':
        chrome_paths = [
            '/usr/bin/chromium',           # Debian Bookworm (primary)
            '/usr/bin/chromium-browser',   # Older Debian/Ubuntu
            '/usr/bin/google-chrome',      # Google Chrome
            '/usr/bin/google-chrome-stable',  # Google Chrome stable
            '/snap/bin/chromium',          # Snap package
            '/opt/google/chrome/chrome',   # Alternative Google Chrome
        ]
        for path in chrome_paths:
            if path and os.path.exists(path) and os.access(path, os.X_OK):
                return path
        # Try to find in PATH (chromium is primary on Debian Bookworm)
        for cmd in ['chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable']:
            found = shutil.which(cmd)
            if found and os.access(found, os.X_OK):
                return found
    # Windows/Mac - webdriver-manager will handle it
    return None


def get_chrome_version(chrome_path=None):
    """Get the full version of Chrome/Chromium installed."""
    if not chrome_path:
        chrome_path = get_chrome_path()
    
    if not chrome_path:
        return None
    
    try:
        # Try to get version using --version flag
        result = subprocess.run(
            [chrome_path, '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Extract full version number (e.g., "Chromium 142.0.7444.59" -> "142.0.7444.59")
            match = re.search(r'(\d+\.\d+\.\d+\.\d+)', result.stdout)
            if match:
                return match.group(1)  # Return full version
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    
    return None


def get_chrome_options(headless=True):
    """Get Chrome options configured for both local and cloud deployment."""
    chrome_options = Options()
    
    # Set Chrome binary path if on Linux
    chrome_path = get_chrome_path()
    if chrome_path:
        chrome_options.binary_location = chrome_path
    
    if headless:
        chrome_options.add_argument('--headless')
    
    # Required for Linux/cloud environments (Streamlit Cloud)
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-setuid-sandbox')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # Set user agent based on OS
    if platform.system() == 'Linux':
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    else:
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    return chrome_options


def fetch_html(url: str, timeout: int = 30, headless: bool = True) -> str:
    if not url or not isinstance(url, str):
        raise ValueError("Invalid URL provided")
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    chrome_options = get_chrome_options(headless)
    driver = None
    try:
        # Check if Chrome is available and get version on Linux
        chrome_path = None
        chrome_version = None
        if platform.system() == 'Linux':
            chrome_path = get_chrome_path()
            if not chrome_path:
                raise WebDriverException(
                    "Chrome/Chromium not found on the server. "
                    "Please ensure packages.txt includes chromium and the app has been redeployed."
                )
            chrome_version = get_chrome_version(chrome_path)
        
        # Use ChromeDriverManager with proper version matching for Chromium
        if platform.system() == 'Linux' and chrome_path:
            # For Chromium on Linux, we need to force webdriver-manager to get the LATEST driver
            # The cached driver (114) is too old. Clear cache and download fresh.
            try:
                # Try to clear old cached driver first to force fresh download
                wdm_cache_dir = os.path.expanduser('~/.wdm/drivers/chromedriver')
                if os.path.exists(wdm_cache_dir):
                    # Remove old cached drivers to force fresh download
                    try:
                        shutil.rmtree(wdm_cache_dir)
                    except Exception:
                        pass  # If we can't delete, continue anyway
                
                # Use Chromium type which should match better with Chromium browser
                driver_manager = ChromeDriverManager(chrome_type=ChromeType.CHROMIUM)
                service = Service(driver_manager.install())
            except Exception:
                try:
                    # Fallback: try standard manager but it might use old cached driver
                    driver_manager = ChromeDriverManager()
                    service = Service(driver_manager.install())
                except Exception:
                    # Last resort
                    service = Service(ChromeDriverManager().install())
        else:
            # Windows/Mac - standard detection
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
    
    chrome_options = get_chrome_options(headless)
    driver = None
    try:
        # Check if Chrome is available and get version on Linux
        chrome_path = None
        chrome_version = None
        if platform.system() == 'Linux':
            chrome_path = get_chrome_path()
            if not chrome_path:
                raise WebDriverException(
                    "Chrome/Chromium not found on the server. "
                    "Please ensure packages.txt includes chromium and the app has been redeployed."
                )
            chrome_version = get_chrome_version(chrome_path)
        
        # Use ChromeDriverManager with proper version matching for Chromium
        if platform.system() == 'Linux' and chrome_path:
            # For Chromium on Linux, we need to force webdriver-manager to get the LATEST driver
            # The cached driver (114) is too old. Clear cache and download fresh.
            try:
                # Try to clear old cached driver first to force fresh download
                wdm_cache_dir = os.path.expanduser('~/.wdm/drivers/chromedriver')
                if os.path.exists(wdm_cache_dir):
                    # Remove old cached drivers to force fresh download
                    try:
                        shutil.rmtree(wdm_cache_dir)
                    except Exception:
                        pass  # If we can't delete, continue anyway
                
                # Use Chromium type which should match better with Chromium browser
                driver_manager = ChromeDriverManager(chrome_type=ChromeType.CHROMIUM)
                service = Service(driver_manager.install())
            except Exception:
                try:
                    # Fallback: try standard manager but it might use old cached driver
                    driver_manager = ChromeDriverManager()
                    service = Service(driver_manager.install())
                except Exception:
                    # Last resort
                    service = Service(ChromeDriverManager().install())
        else:
            # Windows/Mac - standard detection
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