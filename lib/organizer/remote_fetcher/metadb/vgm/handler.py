from pathlib import Path
from bs4 import BeautifulSoup
import random, time, threading, requests, logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import AlbumInfo, SubProduct, VgmParser
from lib.common import PathManager


logger = logging.getLogger(__name__)

# ======================================================================= #
# HTTP 客户端（放在最前，其余类依赖它）
# ======================================================================= #

class VgmHttpClient:
    """带请求间隔 & 指数退避的 HTTP 客户端，防止 Cloudflare 风控"""

    _lock = threading.Lock()          # 全局请求节流锁
    _last_request_time: float = 0.0   # 上次请求时间戳

    # 两次请求之间的最小间隔（秒）
    MIN_INTERVAL: float = 1.2
    MAX_RETRIES: int = 4

    @classmethod
    def get(cls, url: str, headers, referer: str | None = None) -> BeautifulSoup:
        req_headers = headers.copy()
        if referer:
            req_headers["referer"] = referer

        last_error: Exception | None = None

        for attempt in range(cls.MAX_RETRIES):
            # ---- 全局节流：保证任意线程之间请求间隔 ----
            cls._throttle()

            try:
                resp = requests.get(url, headers=req_headers, timeout=(10, 30))

                if resp.status_code in (403, 429):
                    wait = cls._backoff_seconds(attempt)
                    logger.warning(
                        f"{resp.status_code} @ {url}，第 {attempt + 1} 次重试，"
                        f"等待 {wait:.1f}s"
                    )
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                return BeautifulSoup(resp.text, "html.parser")

            except requests.RequestException as e:
                last_error = e
                if attempt < cls.MAX_RETRIES - 1:
                    wait = cls._backoff_seconds(attempt)
                    logger.warning(f"请求异常 {url}: {e}，{wait:.1f}s 后重试")
                    time.sleep(wait)

        raise last_error or RuntimeError(f"请求失败: {url}")

    @classmethod
    def _throttle(cls) -> None:
        """线程安全的全局请求节流"""
        with cls._lock:
            now = time.monotonic()
            elapsed = now - cls._last_request_time
            if elapsed < cls.MIN_INTERVAL:
                time.sleep(cls.MIN_INTERVAL - elapsed + random.uniform(0.05, 0.2))
            cls._last_request_time = time.monotonic()

    @staticmethod
    def _backoff_seconds(attempt: int) -> float:
        """指数退避 + 随机抖动"""
        base = 2.0 ** (attempt + 1)            # 2, 4, 8, 16 …
        jitter = random.uniform(0.3, 1.0)
        return min(base + jitter, 30.0)


# ======================================================================= #
# 文件系统操作
# ======================================================================= #

class VgmFileHandler:
    @staticmethod
    def create_album_folders(parent: Path, albums: list[AlbumInfo], template) -> None:
        for album in albums:
            name = album.folder_name(template)
            if not name:
                continue
            folder = parent / name
            folder.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def create_product_folder(name: str) -> Path:
        safe_name = PathManager.safe_filename(name)
        root = PathManager.to_unc_path(Path(safe_name))
        root.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建文件夹: {root}")
        return root


# ======================================================================= #
# 专辑批量获取（支持并发）
# ======================================================================= #

class AlbumBatchProcessor:
    def __init__(self, http_client: VgmHttpClient, fetch_threads: int):
        self.http_client = http_client
        self.fetch_threads = fetch_threads

    def fetch_albums(
        self, stubs: list[dict], referer: str | None = None,
    ) -> list[AlbumInfo]:
        results: list[AlbumInfo] = []
        total = len(stubs)
        done = 0

        def _fetch_one(stub: dict) -> AlbumInfo | None:
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

        with ThreadPoolExecutor(max_workers=self.fetch_threads) as pool:
            futures = {pool.submit(_fetch_one, s): s for s in stubs}
            for future in as_completed(futures):
                info = future.result()
                done += 1
                if done == total or done % 10 == 0:
                    logger.info(f"专辑详情进度: {done}/{total}")
                if info:
                    results.append(info)

        results.sort(key=lambda a: a.date)
        return results


# ======================================================================= #
# Product 处理器
# ======================================================================= #

class ProductHandler:
    def __init__(self, album_processor: AlbumBatchProcessor, album_fld_tpl: str):
        self.album_processor = album_processor
        self.album_fld_tpl = album_fld_tpl

    def process(self, soup: BeautifulSoup, url: str) -> None:
        name = VgmParser.parse_page_name(soup)
        root = VgmFileHandler.create_product_folder(name)

        stubs = VgmParser.parse_album_stubs(soup)
        logger.info(f"发现 {len(stubs)} 张专辑，正在获取详情...")

        albums = self.album_processor.fetch_albums(stubs, referer=url)
        VgmFileHandler.create_album_folders(root, albums, self.album_fld_tpl)


# ======================================================================= #
# Franchise - flat 模式
# ======================================================================= #

class FranchiseFlatHandler:
    def __init__(self, album_processor: AlbumBatchProcessor, album_fld_tpl):
        self.album_processor = album_processor
        self.album_fld_tpl = album_fld_tpl

    def process(self, soup: BeautifulSoup, root: Path, url: str) -> None:
        stubs = VgmParser.parse_album_stubs(soup)
        logger.info(f"[flat] 发现 {len(stubs)} 张专辑，正在获取详情...")

        albums = self.album_processor.fetch_albums(stubs, referer=url)
        VgmFileHandler.create_album_folders(root, albums, self.album_fld_tpl)


# ======================================================================= #
# Franchise - grouped 模式
# ======================================================================= #

class FranchiseGroupedHandler:
    def __init__(
        self,
        http_client: VgmHttpClient,
        album_processor: AlbumBatchProcessor,
        product_fld_template: str,
        album_fld_template: str,
    ):
        self.http_client = http_client
        self.album_processor = album_processor
        self.product_fld_template = product_fld_template
        self.album_fld_template = album_fld_template

    def process(self, soup: BeautifulSoup, root: Path) -> None:
        franchise_stubs = VgmParser.parse_album_stubs(soup)
        sub_raws = VgmParser.parse_sub_products(soup)
        logger.info(f"[grouped] 发现 {len(sub_raws)} 个子作品")

        sub_products = self._fetch_sub_products(sub_raws)
        album_mapping = self._analyze_album_ownership(sub_products, franchise_stubs)
        self._create_folder_structure(root, sub_products, album_mapping)

    # ---------- 子作品获取（串行，每个内部专辑并发） ----------

    def _fetch_sub_products(self, sub_raws: list[dict]) -> list[SubProduct]:
        results: list[SubProduct] = []
        total = len(sub_raws)

        for idx, raw in enumerate(sub_raws, 1):
            soup = self.http_client.get(raw["url"])
            category = (
                raw["type"]
                if raw.get("type") and raw["type"] != "Other"
                else VgmParser.parse_category(soup)
            )

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
            results.append(sp)
            logger.info(f"[grouped] 子作品进度: {idx}/{total}")

        return results

    # ---------- 归属分析 ----------

    @staticmethod
    def _analyze_album_ownership(
        sub_products: list[SubProduct],
        franchise_stubs: list[dict],
    ) -> dict:
        album_owners: dict[str, list[SubProduct]] = {}
        all_album_ids: set[str] = set()

        for sp in sub_products:
            for album in sp.albums:
                all_album_ids.add(album.album_id)
                album_owners.setdefault(album.album_id, []).append(sp)

        exclusive: dict[SubProduct, list[AlbumInfo]] = {sp: [] for sp in sub_products}
        shared: list[AlbumInfo] = []
        shared_ids: set[str] = set()

        for sp in sub_products:
            for album in sp.albums:
                owners = album_owners[album.album_id]
                if len(owners) == 1:
                    exclusive[sp].append(album)
                elif album.album_id not in shared_ids:
                    shared_ids.add(album.album_id)
                    shared.append(album)

        orphan_stubs = [
            s for s in franchise_stubs if s["album_id"] not in all_album_ids
        ]

        return {
            "exclusive": exclusive,
            "shared": shared,
            "orphan_stubs": orphan_stubs,
        }

    # ---------- 文件夹创建 ----------

    def _create_folder_structure(
        self,
        root: Path,
        sub_products: list[SubProduct],
        album_mapping: dict,
    ) -> None:
        for sp in sub_products:
            exclusive_albums = album_mapping["exclusive"][sp]
            if not exclusive_albums:
                continue

            cat_dir = root / PathManager.safe_filename(sp.category)
            prod_name = self.product_fld_template.format(
                date=sp.date,
                product_name=PathManager.safe_filename(sp.name),
            )
            prod_dir = cat_dir / PathManager.safe_filename(prod_name)
            VgmFileHandler.create_album_folders(prod_dir, exclusive_albums, self.album_fld_template)

        shared_albums = album_mapping["shared"]
        orphan_stubs = album_mapping["orphan_stubs"]

        if shared_albums or orphan_stubs:
            comp_dir = root / "Compilation"
            comp_dir.mkdir(parents=True, exist_ok=True)

            if shared_albums:
                VgmFileHandler.create_album_folders(comp_dir, shared_albums, self.album_fld_template)
            if orphan_stubs:
                orphan_albums = self.album_processor.fetch_albums(orphan_stubs)
                VgmFileHandler.create_album_folders(comp_dir, orphan_albums, self.album_fld_template)
