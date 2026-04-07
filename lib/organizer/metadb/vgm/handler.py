from pathlib import Path
from bs4 import BeautifulSoup
import random, time, requests

from lib.organizer.metadb.vgm.consts import PRODUCT_FOLDER_TPL, HEADERS
from lib.organizer.metadb.vgm.vgm_data_type import AlbumInfo, SubProduct
from lib.organizer.metadb.vgm.vgm_parser import VgmParser
from lib.common.path_manager import PathManager
from lib.common.log import setup_logger


logger = setup_logger(__name__)


class VgmFileHandler:
    """处理文件系统操作"""
    @staticmethod
    def create_album_folders(parent: Path, albums: list[AlbumInfo]) -> None:
        """为专辑列表创建文件夹"""
        for album in albums:
            name = album.folder_name()
            if not name:
                continue
            folder = parent / name
            folder.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def create_product_folder(name: str) -> Path:
        """创建并返回作品根目录"""
        safe_name = PathManager.safe_filename(name)
        root = PathManager.to_unc_path(Path(safe_name))
        root.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建文件夹: {root}")
        return root


class AlbumBatchProcessor:
    """批量处理专辑获取"""

    def __init__(self, http_client: VgmHttpClient):
        self.http_client = http_client

    def fetch_albums(self, stubs: list[dict], referer: str | None = None) -> list[AlbumInfo]:
        """并发获取多张专辑的详情页"""
        results: list[AlbumInfo] = []
        total = len(stubs)
        done = 0

        def fetch_one(stub: dict) -> AlbumInfo | None:
            try:
                soup = self.http_client.get(stub["url"], referer=referer)
                info = VgmParser.parse_album_page(soup, stub["url"])
                if not info.title:
                    info.title = stub.get("title", "")
                if not info.catno:
                    info.catno = stub.get("catno", "")
                return info
            except Exception as e:
                logger.error(f"获取专辑失败 {stub['url']}: {e}")
                return None

        for stub in stubs:
            info = fetch_one(stub)
            done += 1
            if done == total or done % 10 == 0:
                logger.info(f"专辑详情进度: {done}/{total}")
            if info:
                results.append(info)

        results.sort(key=lambda a: a.date)
        return results


class FranchiseGroupedHandler:
    """处理Franchise的grouped模式"""

    def __init__(self, http_client: VgmHttpClient, album_processor: AlbumBatchProcessor):
        self.http_client = http_client
        self.album_processor = album_processor

    def process(self, soup: BeautifulSoup, root: Path) -> None:
        """处理grouped模式的franchise"""
        franchise_stubs = VgmParser.parse_album_stubs(soup)
        sub_raws = VgmParser.parse_sub_products(soup)
        logger.info(f"[grouped] 发现 {len(sub_raws)} 个子作品")

        # 并发获取子作品
        sub_products = self._fetch_sub_products(sub_raws)

        # 分析专辑归属
        album_mapping = self._analyze_album_ownership(sub_products, franchise_stubs)

        # 创建文件夹结构
        self._create_folder_structure(root, sub_products, album_mapping)

    def _fetch_sub_products(self, sub_raws: list[dict]) -> list[SubProduct]:
        """并发获取所有子作品"""
        results: list[SubProduct] = []
        total = len(sub_raws)
        done = 0

        def fetch_one(raw: dict) -> SubProduct:
            soup = self.http_client.get(raw["url"])
            category = raw["type"] if raw.get("type") and raw["type"] != "Other" else VgmParser.parse_category(soup)

            sp = SubProduct(
                product_id=raw["product_id"],
                url=raw["url"],
                name=raw["name"],
                date=raw["date"],
                category=category,
            )

            stubs = VgmParser.parse_album_stubs(soup)
            logger.info(f"子作品抓取: {sp.name}（{len(stubs)} 张专辑）")
            sp.albums = self.album_processor.fetch_albums(stubs, referer=raw["url"])
            return sp

        for raw in sub_raws:
            sp = fetch_one(raw)
            results.append(sp)
            done += 1
            logger.info(f"[grouped] 子作品进度: {done}/{total}")

        return results

    def _analyze_album_ownership(
            self,
            sub_products: list[SubProduct],
            franchise_stubs: list[dict]
    ) -> dict:
        """分析专辑归属：独占、共享、孤儿"""
        album_owners: dict[str, list[SubProduct]] = {}
        all_album_ids: set[str] = set()

        # 统计每个专辑出现在哪些子作品中
        for sp in sub_products:
            for album in sp.albums:
                all_album_ids.add(album.album_id)
                if album.album_id not in album_owners:
                    album_owners[album.album_id] = []
                album_owners[album.album_id].append(sp)

        # 分类
        exclusive_albums: dict[SubProduct, list[AlbumInfo]] = {sp: [] for sp in sub_products}
        shared_albums: list[AlbumInfo] = []
        orphan_stubs: list[dict] = []

        # 处理子作品中的专辑
        for sp in sub_products:
            for album in sp.albums:
                if len(album_owners[album.album_id]) == 1:
                    exclusive_albums[sp].append(album)
                elif album.album_id not in [a.album_id for a in shared_albums]:
                    shared_albums.append(album)

        # 找出孤儿专辑
        for stub in franchise_stubs:
            if stub["album_id"] not in all_album_ids:
                orphan_stubs.append(stub)

        return {
            "exclusive": exclusive_albums,
            "shared": shared_albums,
            "orphan_stubs": orphan_stubs,
        }

    def _create_folder_structure(
            self,
            root: Path,
            sub_products: list[SubProduct],
            album_mapping: dict,
    ) -> None:
        """根据分析结果创建文件夹结构"""
        # 为每个子作品创建独占专辑文件夹
        for sp in sub_products:
            exclusive_albums = album_mapping["exclusive"][sp]
            if not exclusive_albums:
                continue

            cat_dir = root / PathManager.safe_filename(sp.category)
            prod_name = PRODUCT_FOLDER_TPL.format(
                date=sp.date,
                product_name=PathManager.safe_filename(sp.name),
            )
            prod_dir = cat_dir / PathManager.safe_filename(prod_name)
            VgmFileHandler.create_album_folders(prod_dir, exclusive_albums)

        # 共享专辑放入Compilation
        shared_albums = album_mapping["shared"]
        orphan_stubs = album_mapping["orphan_stubs"]

        if shared_albums or orphan_stubs:
            comp_dir = root / "Compilation"
            comp_dir.mkdir(parents=True, exist_ok=True)

            if shared_albums:
                VgmFileHandler.create_album_folders(comp_dir, shared_albums)

            if orphan_stubs:
                orphan_albums = self.album_processor.fetch_albums(orphan_stubs)
                VgmFileHandler.create_album_folders(comp_dir, orphan_albums)


class ProductHandler:
    """处理单个Product页面"""

    def __init__(self, album_processor: AlbumBatchProcessor):
        self.album_processor = album_processor

    def process(self, soup: BeautifulSoup, url: str) -> None:
        """处理Product页面"""
        name = VgmParser.parse_page_name(soup)
        root = VgmFileHandler.create_product_folder(name)

        stubs = VgmParser.parse_album_stubs(soup)
        logger.info(f"发现 {len(stubs)} 张专辑，正在获取详情...")

        albums = self.album_processor.fetch_albums(stubs, referer=url)
        VgmFileHandler.create_album_folders(root, albums)


class FranchiseFlatHandler:
    """处理Franchise的flat模式"""

    def __init__(self, album_processor: AlbumBatchProcessor):
        self.album_processor = album_processor

    def process(self, soup: BeautifulSoup, root: Path, url: str) -> None:
        """处理flat模式的franchise"""
        stubs = VgmParser.parse_album_stubs(soup)
        logger.info(f"[flat] 发现 {len(stubs)} 张专辑，正在获取详情...")

        albums = self.album_processor.fetch_albums(stubs, referer=url)
        VgmFileHandler.create_album_folders(root, albums)


class VgmHttpClient:
    """处理所有HTTP请求，包含重试逻辑"""

    @staticmethod
    def get(url: str, referer: str | None = None) -> BeautifulSoup:
        """带重试的页面请求，处理Cloudflare风控"""
        req_headers = HEADERS.copy()
        if referer:
            req_headers["referer"] = referer

        last_error: Exception | None = None
        for attempt in range(2):
            try:
                if attempt > 0:
                    time.sleep(1.0 * attempt + random.uniform(0.2, 0.6))

                resp = requests.get(url, headers=req_headers, timeout=(10, 20))
                if resp.status_code == 403 and attempt < 1:
                    logger.info(f"403，重试中: {url}")
                    continue

                resp.raise_for_status()
                return BeautifulSoup(resp.text, "html.parser")
            except requests.RequestException as e:
                last_error = e
                if attempt >= 1:
                    raise

        if last_error:
            raise last_error
        raise RuntimeError("请求失败且未返回具体异常")