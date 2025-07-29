# Scrapy settings for accountsplacescraper project

BOT_NAME = "accountsplacescraper"

SPIDER_MODULES = ["accountsplacescraper.spiders"]
NEWSPIDER_MODULE = "accountsplacescraper.spiders"

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = None  # Will be handled by RotateUserAgentMiddleware

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 8  # Reduced to avoid overwhelming the server

# Configure a delay for requests for the same website (default: 0)
DOWNLOAD_DELAY = 0  # Add delay to mimic human behavior

# Disable cookies (optional, depending on site requirements)
COOKIES_ENABLED = False

# Override the default request headers
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://accountsplace.co.ke/',
}

# Enable Playwright downloader middleware
DOWNLOADER_MIDDLEWARES = {
    'scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler': 543,
    'accountsplacescraper.middlewares.RotateUserAgentMiddleware': 400,
}

# Playwright settings
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 60000  # 60 seconds
PLAYWRIGHT_BROWSER_TYPE = 'chromium'
PLAYWRIGHT_LAUNCH_OPTIONS = {
    'headless': True,
}

# Set settings whose default value is deprecated to a future-proof value
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"