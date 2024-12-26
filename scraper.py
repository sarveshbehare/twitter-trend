import time
from datetime import datetime
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient
import uuid
import requests
from config.config import *

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TwitterTrendsScraper:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        self.collection = self.db[COLLECTION_NAME]
        
    def setup_driver(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-notifications')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-infobars')
            chrome_options.add_argument('--lang=en')
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.implicitly_wait(10)
            logger.info("Chrome WebDriver setup successful")
            return driver
        except Exception as e:
            logger.error(f"Failed to setup WebDriver: {str(e)}")
            raise

    def login_to_twitter(self, driver):
        try:
            logger.info("Attempting to login to Twitter")
            driver.get(TWITTER_LOGIN_URL)
            time.sleep(5)

            username_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[autocomplete="username"]'))
            )
            username_input.clear()
            username_input.send_keys(TWITTER_USERNAME)
            time.sleep(1)
            username_input.send_keys(Keys.RETURN)
            logger.info("Username entered successfully")
            time.sleep(3)

            password_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="password"]'))
            )
            password_input.clear()
            password_input.send_keys(TWITTER_PASSWORD)
            time.sleep(1)
            password_input.send_keys(Keys.RETURN)
            logger.info("Password entered successfully")
            time.sleep(5)

            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="primaryColumn"]'))
            )
            logger.info("Successfully logged in to Twitter")

        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            raise

    def extract_trend_name(self, trend_element):
        """Extract the actual trend name from a trend element"""
        try:
            # Try to find the trend name (usually the second or third span)
            spans = trend_element.find_elements(By.TAG_NAME, "span")
            
            # Filter out category labels and empty spans
            valid_spans = [span.text for span in spans if span.text and 
                         not any(label in span.text for label in 
                               ["Trending", "Entertainment", "Politics", "Sports", "in India"])]
            
            # Get the first valid trend name
            if valid_spans:
                trend_name = valid_spans[0].strip()
                logger.info(f"Found trend name: {trend_name}")
                return trend_name
            
            return None
        except Exception as e:
            logger.warning(f"Failed to extract trend name: {str(e)}")
            return None

    def extract_trends(self, driver, max_retries=3):
        """Extract actual trend names with retries"""
        trends = []
        retry_count = 0
        
        while retry_count < max_retries and len(trends) < 5:
            try:
                # Wait for trends to load
                time.sleep(5)
                
                # Try to find all trend elements
                trend_elements = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[data-testid="trend"]'))
                )
                
                # Process each trend element
                for trend_element in trend_elements:
                    try:
                        trend_name = self.extract_trend_name(trend_element)
                        if trend_name and trend_name not in trends:
                            trends.append(trend_name)
                            logger.info(f"Added trend: {trend_name}")
                        
                        if len(trends) >= 5:
                            break
                    except Exception as e:
                        logger.warning(f"Failed to process trend element: {str(e)}")
                        continue
                
            except Exception as e:
                logger.warning(f"Attempt {retry_count + 1} failed: {str(e)}")
            
            if len(trends) < 5:
                retry_count += 1
                logger.info(f"Found {len(trends)} trends, retrying... (attempt {retry_count}/{max_retries})")
                driver.refresh()
                time.sleep(5)
        
        return trends

    def get_trending_topics(self):
        driver = None
        try:
            logger.info("Starting trend scraping process")
            driver = self.setup_driver()
            self.login_to_twitter(driver)
            
            logger.info("Navigating to Twitter home page")
            driver.get(TWITTER_HOME_URL)
            time.sleep(5)
            
            # Extract trends
            trends = self.extract_trends(driver)
            logger.info(f"Found {len(trends)} valid trends")
            
            # Only use placeholder if absolutely necessary
            while len(trends) < 5:
                placeholder = f"No trend found {len(trends) + 1}"
                trends.append(placeholder)
                logger.warning(f"Added placeholder: {placeholder}")
            
            # Get IP address
            try:
                ip_response = requests.get('https://api.ipify.org?format=json', timeout=5)
                ip_address = ip_response.json()['ip']
            except Exception as e:
                logger.error(f"Failed to get IP address: {str(e)}")
                ip_address = "Unable to fetch IP"

            # Create record
            record = {
                "_id": str(uuid.uuid4()),
                "timestamp": datetime.now(),
                "ip_address": ip_address,
            }
            
            for i, trend in enumerate(trends[:5], 1):
                record[f"nameoftrend{i}"] = trend

            self.collection.insert_one(record)
            logger.info("Successfully saved trends to MongoDB")
            return record

        except Exception as e:
            logger.error(f"Error in get_trending_topics: {str(e)}")
            raise

        finally:
            if driver:
                driver.quit()
                logger.info("WebDriver closed")

    def get_latest_record(self):
        try:
            record = self.collection.find_one(sort=[('timestamp', -1)])
            return record
        except Exception as e:
            logger.error(f"Error fetching latest record: {str(e)}")
            raise