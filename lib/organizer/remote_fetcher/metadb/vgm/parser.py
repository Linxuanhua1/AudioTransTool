import re
from bs4 import BeautifulSoup, Tag

from lib.organizer.remote_fetcher.metadb.vgm.data_type import AlbumInfo
from lib.organizer.remote_fetcher.metadb.vgm.consts import VGM_FIELD_MAP, PRODUCT_CATEGORIES, BASE_URL, MONTH_MAP


class VgmParser:

    # ------------------------------------------------------------------ #
    # 通用工具
    # ------------------------------------------------------------------ #

    @staticmethod
    def _extract_title(tag: Tag, fallback: str = "") -> str:
        """从标签中优先取 ja，其次 en，否则取整个标签文本。自动移除 <em>。"""
        el = (
            tag.select_one('.albumtitle[lang="ja"]')
            or tag.select_one('.albumtitle[lang="en"]')
        )
        target = el if el else tag
        em = target.find("em")
        if em:
            em.decompose()
        text = target.get_text(strip=True)
        return text or fallback

    # ------------------------------------------------------------------ #
    # 页面类型 & 基础信息
    # ------------------------------------------------------------------ #

    @staticmethod
    def is_franchise(soup: BeautifulSoup) -> bool:
        sub_div = soup.select_one("div#collapse_sub")
        if not sub_div:
            return False
        return bool(sub_div.find_all("a", href=re.compile(r"/product/\d+")))

    @staticmethod
    def parse_page_name(soup: BeautifulSoup) -> str:
        h1 = soup.select_one("h1")
        if not h1:
            return "Unknown"
        return VgmParser._extract_title(h1, fallback="Unknown")

    @staticmethod
    def parse_category(soup: BeautifulSoup) -> str:
        text = soup.get_text()
        for cat in PRODUCT_CATEGORIES:
            if re.search(rf"\b{re.escape(cat)}\b", text):
                return cat
        return "Other"

    # ------------------------------------------------------------------ #
    # 日期处理
    # ------------------------------------------------------------------ #

    @staticmethod
    def _normalize_date(raw: str) -> str:
        if not raw:
            return ""

        raw = raw.strip()

        # 1. 已经是 YYYY.MM.DD 格式
        m = re.fullmatch(r"(\d{4})\.(\d{2})\.(\d{2})", raw)
        if m:
            return raw

        # 2. 只有年份，如 2004
        m = re.fullmatch(r"(\d{4})", raw)
        if m:
            return f"{int(m.group(1)):04d}.00.00"

        # 3. 英文月份缩写，如 "Aug 15, 2004" 或 "Aug 15, 2004C66"
        m = re.match(r"([A-Z][a-z]{2})\s+(\d{1,2}),\s*(\d{4})", raw)
        if m:
            mon_str, day, year = m.groups()
            month = MONTH_MAP.get(mon_str)
            if month:
                return f"{int(year):04d}.{month:02d}.{int(day):02d}"

        return ""

    @staticmethod
    def normalize_url(url: str) -> str:
        return re.sub(r"^http://", "https://", url.strip(), flags=re.IGNORECASE)

    # ------------------------------------------------------------------ #
    # Product 页面解析
    # ------------------------------------------------------------------ #

    @staticmethod
    def parse_album_stubs(soup: BeautifulSoup) -> list[dict]:
        """从 product 页面获取专辑列表（轻量 stub）"""
        albums: list[dict] = []
        seen: set[str] = set()

        for a in soup.find_all("a", href=re.compile(r"/album/\d+")):
            href = a["href"]
            aid = re.search(r"/album/(\d+)", href).group(1)
            if aid in seen:
                continue
            seen.add(aid)

            full_url = href if href.startswith("http") else BASE_URL + href
            full_url = VgmParser.normalize_url(full_url)

            catno = ""
            row = a.find_parent("tr")
            if row:
                first_td = row.find("td")
                if first_td and first_td != a.find_parent("td"):
                    catno = first_td.get_text(strip=True)

            title_text = VgmParser._extract_title(a)

            albums.append({
                "url": full_url,
                "album_id": aid,
                "title": title_text,
                "catno": catno,
            })
        return albums

    @staticmethod
    def parse_sub_products(soup: BeautifulSoup) -> list[dict]:
        products: list[dict] = []
        seen: set[str] = set()

        container = soup.select_one("div#collapse_sub") or soup

        for a in container.find_all("a", href=re.compile(r"/product/\d+")):
            href = a["href"]
            pid = re.search(r"/product/(\d+)", href).group(1)
            if pid in seen:
                continue
            seen.add(pid)

            full_url = href if href.startswith("http") else BASE_URL + href
            full_url = VgmParser.normalize_url(full_url)
            date_str, ptype = "", ""

            row = a.find_parent("tr")
            if row:
                for cell in row.find_all("td"):
                    cell_text = cell.get_text(strip=True)
                    if re.match(r"\d{4}", cell_text) and cell != a.find_parent("td"):
                        if not date_str:
                            date_str = cell_text
                    for cat in PRODUCT_CATEGORIES:
                        if cat.lower() in cell_text.lower():
                            ptype = cat
                            break

            products.append({
                "url": full_url,
                "product_id": pid,
                "name": a.get_text(strip=True),
                "date": date_str,
                "type": ptype or "Other",
            })
        return products

    # ------------------------------------------------------------------ #
    # Album 详情页解析
    # ------------------------------------------------------------------ #

    @staticmethod
    def parse_album_page(soup: BeautifulSoup, url: str = "") -> AlbumInfo:
        info = AlbumInfo(url=url)

        m = re.search(r"/album/(\d+)", url)
        if m:
            info.album_id = m.group(1)

        # 标题
        title_tag = soup.select_one("#albumtitle") or soup.select_one("h1")
        if title_tag:
            info.title = VgmParser._extract_title(title_tag)

        # 专辑信息表
        infobit = (
            soup.select_one("#album_infobit_large")
            or soup.select_one(".album_infobit_large")
        )
        if infobit:
            VgmParser._parse_infobit(infobit, info)

        # 日期归一化
        info.date = VgmParser._normalize_date(info.date)

        return info

    # ------------------------------------------------------------------ #
    # infobit 内部解析
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_infobit(container: Tag, info: AlbumInfo) -> None:
        rows = container.select("tr")
        if rows:
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).rstrip(":")
                    val = cells[1].get_text(strip=True)
                    VgmParser._set_field(info, key, val)
            return

        # 纯文本结构
        for line in container.get_text(separator="\n", strip=True).split("\n"):
            line = line.strip()
            if not line:
                continue
            for field_name in VGM_FIELD_MAP:
                if line.startswith(field_name):
                    VgmParser._set_field(
                        info, field_name, line[len(field_name):].strip()
                    )
                    break

    @staticmethod
    def _set_field(info: AlbumInfo, key: str, value: str) -> None:
        attr = VGM_FIELD_MAP.get(key)
        if attr:
            setattr(info, attr, value)
