import asyncio
import sys
import cmd_arg
import config
import db
from base.base_crawler import AbstractCrawler
from media_platform.zhihu import ZhihuCrawler

def run_main():
    class CrawlerFactory:
        CRAWLERS = {
            "zhihu": ZhihuCrawler
        }

        @staticmethod
        def create_crawler(platform: str) -> AbstractCrawler:
            crawler_class = CrawlerFactory.CRAWLERS.get(platform)
            if not crawler_class:
                raise ValueError("Invalid Media Platform Currently only supported xhs or dy or ks or bili ...")
            return crawler_class()

    async def main():
        # parse cmd
        await cmd_arg.parse_cmd()

        # init db
        if config.SAVE_DATA_OPTION == "db":
            await db.init_db()

        crawler = CrawlerFactory.create_crawler(platform=config.PLATFORM)
        await crawler.start()

        if config.SAVE_DATA_OPTION == "db":
            await db.close()

    if __name__ == '__main__':
        try:
            # asyncio.run(main())
            asyncio.get_event_loop().run_until_complete(main())
        except KeyboardInterrupt:
            sys.exit()
if __name__ == '__main__':
    run_main()

