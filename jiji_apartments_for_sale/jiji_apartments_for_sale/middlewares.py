from scrapy import signals
from scrapy.http import Request
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message
import random
import logging
import time

# Enhanced user-agent list
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

logger = logging.getLogger(__name__)

class AptsForSaleSpiderMiddleware:
    """Enhanced spider middleware optimized for API scraping"""

    @classmethod
    def from_crawler(cls, crawler):
        s = cls(crawler.settings)
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(s.spider_closed, signal=signals.spider_closed)
        return s

    def __init__(self, settings):
        self.settings = settings
        self.retry_times = settings.getint('RETRY_TIMES', 3)
        self.retry_http_codes = set(int(x) for x in settings.getlist('RETRY_HTTP_CODES'))
        self.stats = {}

    def process_start(self, start_requests, spider):
        """Process start requests with random user-agent"""
        for request in start_requests:
            request.headers['User-Agent'] = random.choice(USER_AGENTS)
            yield request

    def process_spider_input(self, response, spider):
        """Process spider input with enhanced logging"""
        logger.debug(f"Processing response for {response.url} - Status: {response.status}")
        
        status = response.status
        if status not in self.stats:
            self.stats[status] = 0
        self.stats[status] += 1
        
        if hasattr(response, 'text'):
            text = response.text.lower()
            if any(error in text for error in ['blocked', 'rate limit', 'too many requests']):
                logger.warning(f"Potential blocking detected for {response.url}")
        
        return None

    def process_spider_output(self, response, result, spider):
        """Process spider output with validation"""
        item_count = 0
        request_count = 0
        
        for item in result:
            if isinstance(item, dict):  # It's a scraped item
                item_count += 1
                required_fields = ['title', 'price', 'region']
                missing_fields = [field for field in required_fields if not item.get(field)]
                if missing_fields:
                    logger.warning(f"Item missing required fields {missing_fields} from {response.url}")
            elif isinstance(item, Request):  # It's a request
                request_count += 1
            
            yield item
        
        if item_count > 0:
            logger.info(f"Extracted {item_count} items from {response.url}")
        if request_count > 0:
            logger.debug(f"Generated {request_count} new requests from {response.url}")

    def process_spider_exception(self, response, exception, spider):
        """Enhanced exception handling for API"""
        logger.error(f"Spider exception for {response.url}: {type(exception).__name__}: {exception}")
        
        retry_count = response.meta.get('retry_count', 0)
        if retry_count < self.retry_times:
            logger.info(f"Retrying {response.url} due to exception (attempt {retry_count + 1}/{self.retry_times})")
            delay = min(2 ** retry_count, 30)
            return Request(
                url=response.url,
                callback=response.request.callback,
                meta={
                    **response.meta,
                    'retry_count': retry_count + 1,
                    'download_delay': delay,
                },
                headers={'User-Agent': random.choice(USER_AGENTS)},
                dont_filter=True,
                priority=response.request.priority - 1
            )
        
        return None

    def spider_opened(self, spider):
        spider.logger.info(f"Spider '{spider.name}' opened with enhanced middleware")
        spider.logger.info(f"Using {len(USER_AGENTS)} user agents for rotation")
        spider.logger.info(f"Retry times: {self.retry_times}")

    def spider_closed(self, spider):
        spider.logger.info(f"Spider '{spider.name}' closed")
        if self.stats:
            spider.logger.info(f"Response status statistics: {self.stats}")

class CustomRetryMiddleware(RetryMiddleware):
    def __init__(self, settings):
        super().__init__(settings)
        self.max_retry_times = settings.getint('RETRY_TIMES', 5)
        self.retry_http_codes = set(int(x) for x in settings.getlist('RETRY_HTTP_CODES'))
        self.priority_adjust = settings.getint('RETRY_PRIORITY_ADJUST', -1)

    def retry(self, request, reason, spider):
        retry_times = request.meta.get('retry_times', 0) + 1
        
        if retry_times <= self.max_retry_times:
            logger.info(f"Retrying {request.url} (attempt {retry_times}/{self.max_retry_times}): {reason}")
            delay = min(2 ** (retry_times - 1), 30)
            retry_req = request.copy()
            retry_req.meta['retry_times'] = retry_times
            retry_req.meta['download_delay'] = delay
            retry_req.priority = request.priority + self.priority_adjust * retry_times
            retry_req.headers['User-Agent'] = random.choice(USER_AGENTS)
            
            return retry_req
        else:
            logger.error(f"Gave up retrying {request.url} after {self.max_retry_times} attempts: {reason}")
            return None