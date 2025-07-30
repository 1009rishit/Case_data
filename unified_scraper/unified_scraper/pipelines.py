# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter


class PhhcCrawlerPipeline:
    def process_item(self, item, spider):
        return item

import pandas as pd

class ExcelExportPipeline:
    def __init__(self):
        self.items = []

    def process_item(self, item, spider):
        self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        if self.items:
            df = pd.DataFrame(self.items)
            df.to_excel("results.xlsx", index=False)
