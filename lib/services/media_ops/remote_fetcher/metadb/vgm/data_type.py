from dataclasses import dataclass, field

from lib.services.utils import PathManager


# --------------------------------------------------------------------------- #
# 数据结构
# --------------------------------------------------------------------------- #

@dataclass
class AlbumInfo:
    album_id: str = ""
    url: str = ""
    title: str = ""                # albumtitle
    date: str = ""                 # Release Date
    catno: str = ""                # Catalog Number
    media_format: str = ""         # CD / Digital / Vinyl …
    publish_format: str = ""       # Commercial / Doujin …
    classification: str = ""       # Soundtrack+Arrange …
    publisher: str = ""
    composer: str = ""
    arranger: str = ""
    performer: str = ""
    price: str = ""

    def folder_name(self, template) -> str:
        name = template.format(
            date=self.date, catno=self.catno, album=self.title,
            media_format=self.media_format, publish_format=self.publish_format,
            classification=self.classification, publisher=self.publisher,
            composer=self.composer, arranger=self.arranger,
            performer=self.performer, price=self.price,
        )
        return PathManager.safe_filename(name)


@dataclass
class SubProduct:
    product_id: str = ""
    url: str = ""
    name: str = ""
    date: str = ""
    category: str = ""             # Game / Animation / …
    albums: list[AlbumInfo] = field(default_factory=list)
