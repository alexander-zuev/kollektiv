from src.crawling.crawler import FireCrawler
from src.utils.config import FIRECRAWL_API_KEY


def test_fire_crawler_initialization():
    """
    Test the initialization of the FireCrawler class.

    Args:
        None

    Returns:
        None

    Raises:
        AssertionError: If the assertions regarding the FireCrawler instance fail.
    """
    crawler = FireCrawler(FIRECRAWL_API_KEY)
    assert crawler is not None
    assert crawler.api_key == FIRECRAWL_API_KEY
