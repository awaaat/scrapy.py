# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

class JijiApartmentsForSalePipeline:
    def __init__(self):
        self.seen_urls = set()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        url = adapter.get('property_url')
        
        if url in self.seen_urls:
            raise DropItem(f"Duplicate item found with URL: {url}")
        else:
            self.seen_urls.add(url)
            return item