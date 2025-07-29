import scrapy
import json

class JijiSpider(scrapy.Spider):
    name = 'apts_for_sale'
    start_urls = ['https://jiji.co.ke/api_web/v1/listing?slug=houses-apartments-for-rent&init_page=true&page=1&webp=true']

    def parse(self, response):
        data = json.loads(response.text)
        adverts = data.get('adverts_list', {}).get('adverts', [])
        
        for advert in adverts:
            attrs = {attr['name']: attr['value'] for attr in advert.get('attrs', [])}
            initial_item = {
                'title': advert.get('title'),
                'rent_per_period': advert.get('price_obj', {}).get('value'),
                'rent_period': advert.get('price_obj', {}).get('period'),
                'region': advert.get('region'),
                'property_size_sqm': attrs.get('Property size'),
                'bedrooms': attrs.get('Bedrooms'),
                'bathrooms': attrs.get('Bathrooms'),
                'furnishing': attrs.get('Furnishing'),
                'listing_by': attrs.get('Listing by'),
                'user_id': advert.get('user_id'),
                'is_owner': advert.get('is_owner'),
                'can_view_contacts': advert.get('can_view_contacts'),
                'status': advert.get('status'),
                'property_url': advert.get('url')
            }
            # Follow the property_url
            yield scrapy.Request(
                url=f'https://jiji.co.ke{advert.get("url")}',
                callback=self.parse_property,
                meta={'initial_item': initial_item}
            )

        next_url = data.get('next_url')
        if next_url:
            yield scrapy.Request(url=next_url, callback=self.parse)

    def parse_property(self, response):
        initial_item = response.meta['initial_item']
        
        # Extract estate name by matching the attribute key
        estate_name = next((
            attr.css('div.b-advert-attribute__value::text').get(default='').strip()
            for attr in response.css('div.b-advert-attributes--tiles div.b-advert-attribute')
            if attr.css('div.b-advert-attribute__key::text').get(default='').strip().lower() == 'estate name'
        ), None)

        # Extract additional details
        item = {
            **initial_item,
            'description': response.xpath('//div[contains(@class, "description")]/text()').get() or \
                        response.css('div.description::text').get(default='').strip() or None,
            'property_address': response.css('div.b-advert-info-statistics--region::text').get(default='').strip() or \
                                response.xpath('//div[contains(@class, "advert-info-statistics--region")]/text()').get(default='').strip() or None,
            'estate_name': estate_name,
            'condition': next((
                attr.css('div.b-advert-attribute__value::text').get(default='').strip()
                for attr in response.css('div.b-advert-attributes--tiles div.b-advert-attribute')
                if any(kw in attr.css('div.b-advert-attribute__key::text').get(default='').lower()
                    for kw in ['condition', 'built', 'status'])
            ), None),
            'toilets': next((
                attr.css('div.b-advert-attribute__value::text').get(default='').strip().split(' ')[0]
                for attr in response.css('div.b-advert-attributes--tiles div.b-advert-attribute')
                if 'toilet' in attr.css('div.b-advert-attribute__key::text').get(default='').lower()
            ), None) or \
                    next((
                        attr.css('div.b-advert-attribute__value::text').get(default='').strip().split(' ')[0]
                        for attr in response.css('div.b-advert-attributes--tiles div.b-advert-attribute')
                        if 'bathroom' in attr.css('div.b-advert-attribute__key::text').get(default='').lower()
                    ), None),
            'ranter_or_agent_name': response.css('div.b-seller-block__name::text').get(default='').strip() or \
                                response.xpath('//div[contains(@class, "seller-block__name")]/text()').get(default='').strip() or None,
            'time_on_jiji': response.css('div.b-seller-block__info__stat:contains("on Jiji")::text').get(default='').strip() or \
                            response.xpath('//div[contains(@class, "seller-block__info__stat") and contains(text(), "on Jiji")]/text()').get(default='').strip() or None,
            'property_details': response.xpath('//div[contains(@class, "b-advert__description-wrapper")]//span[contains(@class, "qa-description-text")]/text()').getall()
        }
        # Join the property details into a single string with newlines preserved
        item['property_details'] = '\n'.join([text.strip() for text in item['property_details'] if text.strip()]) if item['property_details'] else None
        
        yield item