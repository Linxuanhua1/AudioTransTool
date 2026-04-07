from bs4 import BeautifulSoup

from lib.common.log import setup_logger
from lib.organizer.metadb.vgm.consts import FRANCHISE_MODE, URL_RE
from lib.organizer.metadb.vgm.vgm_parser import VgmParser
from lib.organizer.metadb.vgm.handler import (FranchiseFlatHandler, FranchiseGroupedHandler, VgmFileHandler,
                                              VgmHttpClient, AlbumBatchProcessor, ProductHandler)


logger = setup_logger(__name__)


class VgmFetcher:
    """VGM数据获取器 - 主协调器"""
    def __init__(self):
        self.http_client = VgmHttpClient()
        self.album_processor = AlbumBatchProcessor(self.http_client)
        self.product_handler = ProductHandler(self.album_processor)
        self.flat_handler = FranchiseFlatHandler(self.album_processor)
        self.grouped_handler = FranchiseGroupedHandler(self.http_client, self.album_processor)
    
    def process(self, url: str) -> None:
        """处理VGM URL，自动识别类型并分发"""
        url = url.strip().rstrip("/")
        if not URL_RE.match(url):
            logger.info(f"不支持的 URL: {url}", extra={"plain": True})
            logger.info("仅支持 https://vgmdb.net/product/<id>", extra={"plain": True})
            return

        soup = self.http_client.get(url)

        if VgmParser.is_franchise(soup):
            self._handle_franchise(soup, url)
        else:
            self._handle_product(soup, url)
    
    def _handle_franchise(self, soup: BeautifulSoup, url: str) -> None:
        """处理Franchise页面"""
        logger.info(f"{url} 识别为 Franchise（系列）页面")
        name = VgmParser.parse_page_name(soup)
        root = VgmFileHandler.create_product_folder(name)
        logger.info(f"创建系列文件夹: {root}")
        
        if FRANCHISE_MODE == "flat":
            self.flat_handler.process(soup, root, url)
        elif FRANCHISE_MODE == "grouped":
            self.grouped_handler.process(soup, root)
        else:
            logger.error(f"不支持的保存模式: {FRANCHISE_MODE}")
    
    def _handle_product(self, soup: BeautifulSoup, url: str) -> None:
        """处理Product页面"""
        logger.info(f"{url} 识别为 Product（具体作品）页面")
        self.product_handler.process(soup, url)
