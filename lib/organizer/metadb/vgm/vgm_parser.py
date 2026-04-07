import re
from bs4 import BeautifulSoup, Tag

from lib.organizer.metadb.vgm.vgm_data_type import AlbumInfo
from lib.organizer.metadb.vgm.consts import VGM_FIELD_MAP, PRODUCT_CATEGORIES, BASE_URL, MONTH_MAP


class VgmParser:
    @staticmethod
    def is_franchise(soup: BeautifulSoup) -> bool:
        sub_div = soup.select_one("div#collapse_sub")
        if not sub_div:
            return False
        return bool(sub_div.find_all("a", href=re.compile(r"/product/\d+")))

    @staticmethod
    def parse_page_name(soup):
        page_name = (
                soup.select_one('h1 .albumtitle[lang="ja"]')
                or soup.select_one('h1 .albumtitle[lang="en"]')
        )
        if not page_name:
            h1 = soup.select_one("h1")
            return h1.get_text(strip=True) if h1 else "Unknown"

        em = page_name.find("em")
        if em:
            em.decompose()

        return page_name.get_text(strip=True)

    @staticmethod
    def parse_page_date(soup: BeautifulSoup) -> str:
        raw = ""

        for b in soup.find_all("b"):
            text = b.get_text(strip=True)
            if "Release" in text or "Date" in text:
                sib = b.next_sibling
                while sib and not str(sib).strip():
                    sib = sib.next_sibling
                if sib:
                    raw = str(sib).strip().strip(":").strip()
                    break

        return VgmParser.normalize_date(raw)

    @staticmethod
    def normalize_date(raw: str) -> str:
        if not raw:
            return ""

        raw = raw.strip()

        # 1. 只有年份，如 2004
        m = re.fullmatch(r"(\d{4})", raw)
        if m:
            year = int(m.group(1))
            return f"{year:04d}.00.00"

        # 2. 英文月份缩写 + 日期 + 年份，后面允许跟额外后缀
        # 例如 Aug 15, 2004
        #     Aug 15, 2004C66
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

    @staticmethod
    def parse_category(soup: BeautifulSoup) -> str:
        text = soup.get_text()
        for cat in PRODUCT_CATEGORIES:
            if re.search(rf"\b{re.escape(cat)}\b", text):
                return cat
        return "Other"

    @staticmethod
    def parse_album_stubs(soup: BeautifulSoup) -> list[dict]:
        """
        从product页面获取专辑列表
        """
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

            # 尝试从同行 <td> 取 catalog number
            catno = ""
            row = a.find_parent("tr")
            if row:
                first_td = row.find("td")
                if first_td and first_td != a.find_parent("td"):
                    catno = first_td.get_text(strip=True)

            title = (a.select_one('.albumtitle[lang="ja"]')
                    or a.select_one('.albumtitle[lang="en"]'))
            if not title:
                title = a.get_text(strip=True)

            em = title.find("em")
            if em:
                em.decompose()

            albums.append({
                "url": full_url,
                "album_id": aid,
                "title": title.get_text(strip=True),
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

    @staticmethod
    def parse_album_page(soup: BeautifulSoup, url: str = "") -> AlbumInfo:
        info = AlbumInfo(url=url)

        m = re.search(r"/album/(\d+)", url)
        if m:
            info.album_id = m.group(1)

        title_tag = soup.select_one("#albumtitle") or soup.select_one("h1")
        if title_tag:
            info.title = title_tag.get_text(separator=" ", strip=True)

        # 专辑信息
        infobit = (soup.select_one("#album_infobit_large")
                   or soup.select_one(".album_infobit_large"))
        if infobit:
            VgmParser._parse_infobit(infobit, info)

        return info

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
                    VgmParser._set_field(info, field_name,
                                         line[len(field_name):].strip())
                    break

    @staticmethod
    def _set_field(info: AlbumInfo, key: str, value: str) -> None:
        attr = VGM_FIELD_MAP.get(key)
        if attr:
            setattr(info, attr, value)
