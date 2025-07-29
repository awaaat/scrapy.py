import scrapy
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from urllib.parse import urlencode, urlparse, parse_qs
import json
import time
import logging
import random
import re

logger = logging.getLogger(__name__)

class AptsForSaleSpider(scrapy.Spider):
    name = "apts_for_sale"
    allowed_domains = ["jiji.co.ke"]
    start_urls = ["https://jiji.co.ke/houses-apartments-for-sale"]
    api_base_url = "https://jiji.co.ke/api_web/v1/listing"
    max_retries = 5  # Defined here for reference

    custom_settings = {
        'DOWNLOAD_DELAY': 2,  # Base delay between requests
        'CONCURRENT_REQUESTS': 1,  # Limit concurrency with Selenium
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize Selenium WebDriver
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Run in headless mode
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        # Specify path to ChromeDriver if not in PATH
        # service = Service('/path/to/chromedriver')
        # self.driver = webdriver.Chrome(service=service, options=options)
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(120)

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                callback=self.parse,
                meta={'selenium': True},
                errback=self.errback,
            )

    def parse(self, response):
        # Use Selenium to load the page
        try:
            self.driver.get(response.url)
            # Wait for ads to load
            WebDriverWait(self.driver, 120).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.b-list-advert-base"))
            )
            # Scroll to the bottom to load all content
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Wait for content to load after scroll

            # Extract apartment URLs using Scrapy selector on Selenium's page source
            sel = scrapy.Selector(text=self.driver.page_source)
            apartment_urls = sel.css("a.b-list-advert-base::attr(href)").getall()
            logger.info(f"Found {len(apartment_urls)} ads on page {response.url}")

            for apartment_url in apartment_urls:
                apartment_url = apartment_url.lstrip("/")
                full_apt_url = f"https://jiji.co.ke/{apartment_url}"
                yield scrapy.Request(
                    full_apt_url,
                    callback=self.parse_details,
                    meta={'selenium': True},
                    errback=self.errback,
                )

            # Construct API URL
            current_url = response.url
            parsed_url = urlparse(current_url)
            query_params = parse_qs(parsed_url.query)
            page_num = int(query_params.get("page", [1])[0])
            api_params = {
                "slug": "houses-apartments-for-sale",
                "init_page": "true",
                "page": str(page_num),
                "webp": "false",
                "lsmid": str(int(time.time() * 1000)),
            }
            api_url = f"{self.api_base_url}?{urlencode(api_params)}"
            time.sleep(random.uniform(1, 3))  # Random delay
            yield scrapy.Request(
                api_url,
                callback=self.parse_api_response,
                meta={'selenium': True, 'page_num': page_num},
                errback=self.errback,
            )
        except (TimeoutException, WebDriverException) as e:
            logger.error(f"Error loading page {response.url}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in parse: {response.url}: {str(e)}")

    def parse_api_response(self, response):
        page_num = response.meta['page_num']
        logger.debug(f"API response for page {page_num} (first 1000 chars): {response.text[:1000]}")
        # Extract JSON from HTML-wrapped response
        json_str = re.search(r'\s*({.*})', response.text, re.DOTALL)
        if json_str:
            data = json.loads(json_str.group(1))
        else:
            logger.error(f"No JSON found in API response for page {page_num}")
            logger.error(f"Full response content: {response.text}")
            return

        # Process ads from API
        adverts = data.get("adverts_list", {}).get("adverts", [])
        total_pages = data.get("adverts_list", {}).get("total_pages", 1)
        logger.info(f"Processing page {page_num} with {len(adverts)} ads, total pages: {total_pages}")
        for advert in adverts:
            bedrooms_value = next((attr["semantic_value"] for attr in advert.get("attrs", []) if attr["name"] == "Bedrooms"), None)
            type_value = bedrooms_value.replace(" bedrooms", "") if bedrooms_value else None
            item = {
                "title": advert.get("title"),
                "location": advert.get("region_item_text"),
                "type": type_value,
                "bedrooms": bedrooms_value,
                "bathrooms": next((attr["semantic_value"] for attr in advert.get("attrs", []) if attr["name"] == "Bathrooms"), None),
                "address": None,  # Handled in parse_details
                "estate": advert.get("region_name"),
                "size": next((attr["value"] for attr in advert.get("attrs", []) if attr["name"] == "Property size"), None),
                "condition": None,  # Handled in parse_details
                "furnishing": next((attr["value"] for attr in advert.get("attrs", []) if attr["name"] == "Furnishing"), None),
                "toilets": None,  # Handled in parse_details
                "price_rent": advert.get("price_obj", {}).get("view"),
                "price_with_period": advert.get("price_obj", {}).get("view"),
                "seller_or_agent_name": None,  # Handled in parse_details
                "time_on_jiji": None,  # Handled in parse_details
                "property_url": f"https://jiji.co.ke{advert.get('url')}",
            }
            yield item

        # Follow next API page if available
        next_url = data.get("next_url")
        if next_url and page_num < total_pages:
            logger.info(f"Fetching next API page: {next_url}")
            time.sleep(random.uniform(1, 3))
            yield scrapy.Request(
                next_url,
                callback=self.parse_api_response,
                meta={'selenium': True, 'page_num': page_num + 1},
                errback=self.errback,
            )

        # Follow next HTML page if within total_pages
        if page_num < total_pages:
            next_html_url = f"https://jiji.co.ke/houses-apartments-for-sale?page={page_num + 1}"
            time.sleep(random.uniform(1, 3))
            yield scrapy.Request(
                next_html_url,
                callback=self.parse,
                meta={'selenium': True},
                errback=self.errback,
            )

    def parse_details(self, response):
        logger.debug(f"Processing details for {response.url}")
        try:
            self.driver.get(response.url)
            # Wait for key elements to load
            WebDriverWait(self.driver, 120).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.b-advert-attributes-wrapper"))
            )
            # Multiple scrolls to trigger lazy-loaded content
            for _ in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            time.sleep(5)  # Additional delay for stability

            # Retry loop for critical fields
            max_attempts = 3
            item = None
            for attempt in range(max_attempts):
                try:
                    # Use Scrapy selector on Selenium's page source
                    sel = scrapy.Selector(text=self.driver.page_source)

                    title = sel.css("div.b-advert-title-inner::text").get()
                    title = title.strip() if title else None

                    location = sel.css("div.b-advert-info-statistics--region::text").get()
                    location = location.rsplit(',', 1)[0].strip() if location else None

                    subtype = sel.css("div.b-advert-icon-attributes-container div.b-advert-icon-attribute:nth-child(1) span::text").get()
                    subtype = subtype.strip() if subtype else None

                    property_address = location or None
                    estate_name = None
                    if location and "/" in location:
                        estate_name = location.split("/")[1].strip() or None

                    icon_attributes = sel.css("div.b-advert-icon-attributes-container div.b-advert-icon-attribute span::text").getall()
                    icon_attributes = [attr.strip() for attr in icon_attributes if attr.strip()]

                    attributes = sel.css("div.b-advert-attributes-wrapper .b-advert-attribute")
                    bedrooms = None
                    bathrooms = None
                    toilets = None
                    property_size = None
                    condition = None
                    furnishing = None

                    for attr in icon_attributes:
                        if "bedroom" in attr.lower() or "bdrm" in attr.lower():
                            bedrooms = attr
                        elif "bathroom" in attr.lower():
                            bathrooms = attr
                        elif "toilet" in attr.lower():
                            toilets = attr

                    for attr in attributes:
                        key = attr.css("div.b-advert-attribute__key::text").get()
                        key = key.lower().strip() if key else ""
                        value = attr.css("div.b-advert-attribute__value::text").get()
                        value = value.strip() if value else None
                        if "property size" in key:
                            property_size = value
                        elif "condition" in key:
                            condition = value
                        elif "furnishing" in key:
                            furnishing = value
                        elif "toilet" in key or "toilets" in key:
                            toilets = value

                    price_rent = sel.css("div.qa-advert-price-view span.qa-advert-price-view-value::text").get()
                    price_rent = price_rent.strip() if price_rent else None

                    price_with_period_parts = sel.css("div.qa-advert-price-view span.qa-advert-price-view-value::text, div.qa-advert-price-view span.b-alt-advert-price__period::text").getall()
                    price_with_period = ' '.join([part.strip() for part in price_with_period_parts if part]) or None

                    seller_or_agent_name = sel.css("div.b-seller-block__info div.b-seller-block__name::text").get()
                    seller_or_agent_name = seller_or_agent_name.strip() if seller_or_agent_name else None

                    time_on_jiji = sel.css("div.b-seller-block__info div.b-seller-block__info__stat:nth-child(2)::text").get()
                    time_on_jiji = time_on_jiji.strip() if time_on_jiji else None

                    # Check if critical fields are populated
                    if seller_or_agent_name and time_on_jiji and condition and furnishing:
                        item = {
                            'title': title,
                            'location': location,
                            'type': subtype,
                            'property_address': property_address,
                            'estate_name': estate_name,
                            'property_size': property_size,
                            'condition': condition,
                            'furnishing': furnishing,
                            'toilets': toilets,
                            'bedrooms': bedrooms,
                            'bathrooms': bathrooms,
                            'price_rent': price_rent,
                            'price_with_period': price_with_period,
                            'seller_or_agent_name': seller_or_agent_name,
                            'time_on_jiji': time_on_jiji,
                            'property_url': response.url
                        }
                        break
                    else:
                        logger.warning(f"Attempt {attempt + 1}/{max_attempts}: Missing fields for {response.url}: "
                                      f"seller={seller_or_agent_name}, time={time_on_jiji}, condition={condition}, furnishing={furnishing}, toilets={toilets}")
                        if attempt < max_attempts - 1:
                            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(3)
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed for {response.url}: {str(e)}")
                    if attempt < max_attempts - 1:
                        time.sleep(3)

            if item is None:
                logger.error(f"Failed to extract all fields after {max_attempts} attempts for {response.url}")
                item = {
                    'title': title,
                    'location': location,
                    'type': subtype,
                    'property_address': property_address,
                    'estate_name': estate_name,
                    'property_size': property_size,
                    'condition': condition,
                    'furnishing': furnishing,
                    'toilets': toilets,
                    'bedrooms': bedrooms,
                    'bathrooms': bathrooms,
                    'price_rent': price_rent,
                    'price_with_period': price_with_period,
                    'seller_or_agent_name': seller_or_agent_name,
                    'time_on_jiji': time_on_jiji,
                    'property_url': response.url
                }

            yield item
        except (TimeoutException, WebDriverException) as e:
            logger.error(f"Error processing {response.url}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in parse_details: {response.url}: {str(e)}")

    def errback(self, failure):
        logger.error(f"Errback triggered for {failure.request.url}: {failure.value}")

    def closed(self, reason):
        # Close the Selenium WebDriver when the spider is done
        self.driver.quit()