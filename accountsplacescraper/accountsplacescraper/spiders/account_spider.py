import scrapy
from scrapy_playwright.page import PageMethod
from scrapy.http import Request
import random

class AccountSpiderSpider(scrapy.Spider):
    name = "account_spider"
    allowed_domains = ["accountsplace.co.ke"]
    start_urls = ["https://accountsplace.co.ke/?page=1"]

    # Custom settings to enable Playwright
    custom_settings = {
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler': 543,
            'accountsplacescraper.middlewares.RotateUserAgentMiddleware': 400,
        },
        'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT': 60000,  # 60 seconds
        'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            'headless': True,
        },
    }

    def start_requests(self):
        for url in self.start_urls:
            yield Request(
                url,
                meta={
                    'playwright': True,
                    'playwright_include_page': True,
                    'playwright_page_methods': [
                        PageMethod('wait_for_selector', 'h3.add-title a'),
                    ],
                },
                callback=self.parse,
            )

    def parse(self, response):
        account_urls = response.css('h3.add-title a::attr(href)').getall()
        for account_url in account_urls:
            yield response.follow(
                account_url,
                meta={
                    'playwright': True,
                    'playwright_include_page': True,
                    'playwright_page_methods': [
                        PageMethod('wait_for_selector', 'div.slider-left h1'),
                    ],
                },
                callback=self.parse_details,
            )

        current_page_url = response.url
        n = int(current_page_url.split('=')[1])
        next_page_url = f"{current_page_url.split('=')[0]}={n+1}"
        self.logger.info(f"Parsing Details in page {n}.........................................................................................................................................")
        if next_page_url and account_urls:
            yield Request(
                next_page_url,
                meta={
                    'playwright': True,
                    'playwright_include_page': True,
                    'playwright_page_methods': [
                        PageMethod('wait_for_selector', 'h3.add-title a'),
                    ],
                },
                callback=self.parse,
            )

    def parse_details(self, response):
        acc_description = response.css('div.slider-left h1::text').get().strip().split(':', 1)[1]
        acc_price = response.css('aside.panel-details ul li:nth-child(1) p::text').get().strip().split("S")[1]
        acc_level = response.css('aside.panel-details ul li:nth-child(2) p::text').get().strip()
        acc_category = response.css('aside.panel-details ul li:nth-child(3) p::text').get().strip()
        acc_rating = response.css('aside.panel-details ul li:nth-child(4) p::text').get().strip()
        acc_seller = response.css('span.name a::text').get().strip()
        account_url = response.url
        yield {
            'url': account_url,
            'description': acc_description,
            'price': acc_price,
            'level': acc_level,
            'category': acc_category,
            'rating': acc_rating,
            'seller': acc_seller,
        }