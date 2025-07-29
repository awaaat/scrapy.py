# Scrapy settings for jiji_apartments_for_sale project

BOT_NAME = "jiji_apartments_for_sale"

SPIDER_MODULES = ["jiji_apartments_for_sale.spiders"]
NEWSPIDER_MODULE = "jiji_apartments_for_sale.spiders"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Rate limiting settings (optimized for API)
DOWNLOAD_DELAY = 1.0  # Reduced to 1 second for efficiency, adjustable based on API tolerance
CONCURRENT_REQUESTS = 16  # Increased to handle more requests, monitor for 429 errors
CONCURRENT_REQUESTS_PER_DOMAIN = 8  # Balanced for Jiji's API

# Retry settings
RETRY_TIMES = 5
RETRY_HTTP_CODES = [429, 500, 502, 503, 504, 408, 522, 524]  # Keep full list

# Middleware settings (API-focused, remove Playwright unless needed)
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,  # Disabled default retry
    'jiji_apartments_for_sale.middlewares.CustomRetryMiddleware': 550,  # Use custom retry
    # Remove Playwright handler unless HTML scraping is required
    # 'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler': 600,
    'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 750,  # Keep proxy if needed
}

# Optional: Re-enable Playwright if needed (uncomment and adjust)
"""
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 120000
PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 15
PLAYWRIGHT_MAX_CONCURRENT_PAGES = 15
PLAYWRIGHT_CONTEXTS = {}
PLAYWRIGHT_CONTEXT_ARGS = {
    'bypass_csp': True,
    'java_script_enabled': True,
    'viewport': {'width': 1280, 'height': 720},
    'ignore_https_errors': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
}
"""

# Pipeline settings
ITEM_PIPELINES = {
    'jiji_apartments_for_sale.pipelines.JijiApartmentsForSalePipeline': 300,
}

# Logging
LOG_LEVEL = "DEBUG"
LOG_FILE = "scrapy.log"

# Optional: Proxy settings (uncomment if needed)
# HTTP_PROXY = "http://your_proxy:port"
# HTTPS_PROXY = "http://your_proxy:port"