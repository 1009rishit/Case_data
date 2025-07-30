# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class PhhcCrawlerItem(scrapy.Item):
    case_type = scrapy.Field()
    date = scrapy.Field()
    columns = scrapy.Field()  # Dictionary of column_name: value
    links = scrapy.Field()    # List of URLs in the row


class DelhiJudgmentItem(scrapy.Item):
    case_no = scrapy.Field()
    party = scrapy.Field()
    pdf_link = scrapy.Field()