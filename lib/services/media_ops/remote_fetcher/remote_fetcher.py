import musicbrainzngs, logging

from lib.services.media_ops.remote_fetcher.metadb import Vgm


logger = logging.getLogger("musicbox.services.media_ops.remote_fetcher")

musicbrainzngs.set_useragent("MyMusicApp", "1.0", "your@email.com")


class RemoteFetcher:
    """
    远程数据拉取操作类。

    用法
    ----
    fetcher = RemoteFetcher()
    fetcher.fetch_from_musicbrainz()
    fetcher.fetch_vgm_and_create_folder()
    """
    def __init__(self, config):
        self.config = config

    # # ------------------------------------------------------------------ #
    # # MusicBrainz
    # # ------------------------------------------------------------------ #
    #
    # def fetch_from_musicbrainz(self) -> None:
    #     """交互式循环：从音频标签读取光盘编号，搜索 MusicBrainz 并写回 Album ID。"""
    #     print("询问输入文件夹的时候，输入 # 返回主菜单")
    #     while True:
    #         folder_path = PathManager.check_input_folder_path()
    #         if folder_path == "#":
    #             print("返回主菜单")
    #             return
    #         self._process_mb_folder(folder_path)
    #
    # def _process_mb_folder(self, folder_path: str) -> None:
    #     for dir_name in os.listdir(folder_path):
    #         base_path = os.path.join(folder_path, dir_name)
    #         if not os.path.isdir(base_path):
    #             continue
    #
    #         catno = self._read_catno(base_path)
    #         if not catno:
    #             print("该文件夹下的音频没有光盘编号，请标注后再试")
    #             continue
    #
    #         result = musicbrainzngs.search_releases(
    #             catno=catno[0] if isinstance(catno, list) else catno,
    #             limit=5,
    #         )
    #         album_id = self._check_multi_result(result)
    #         if not album_id:
    #             print("没有查询到结果")
    #             continue
    #
    #         self._write_album_id_to_folder(base_path, album_id)
    #         print(f"成功将 albumid 写入 {base_path} 下的音频")
    #
    # @staticmethod
    # def _read_catno(base_path: str) -> str | list[str] | None:
    #     for file in os.listdir(base_path):
    #         file_path = Path(os.path.join(base_path, file))
    #         bundle = AudioTagReader.read(file_path)
    #         if bundle and bundle.catno:
    #             return bundle.catno
    #     return None
    #
    # @staticmethod
    # def _write_album_id_to_folder(base_path: str, album_id: str) -> None:
    #     for file in os.listdir(base_path):
    #         file_path = Path(os.path.join(base_path, file))
    #         AudioTagReader.write_album_id(file_path, album_id)
    #
    # @staticmethod
    # def _check_multi_result(result: dict) -> str | None:
    #     releases = result.get("release-list", [])
    #     if not releases:
    #         return None
    #     if len(releases) == 1:
    #         return releases[0]["id"]
    #
    #     print("找到多条结果，请选择：")
    #     for i, r in enumerate(releases, 1):
    #         title  = r.get("title", "?")
    #         artist = r.get("artist-credit-phrase", "?")
    #         date   = r.get("date", "?")
    #         print(f"  {i}. [{date}] {artist} — {title}  (id: {r['id']})")
    #
    #     choice = input("请输入编号（直接回车跳过）：").strip()
    #     if choice.isdigit() and 1 <= int(choice) <= len(releases):
    #         return releases[int(choice) - 1]["id"]
    #     return None

    # ------------------------------------------------------------------ #
    # VGMdb
    # ------------------------------------------------------------------ #

    def fetch_vgm_and_create_folder(self) -> None:
        """交互式循环：从 VGMdb 页面拉取数据并创建对应文件夹结构。"""
        print("输入 VGMdb product URL，输入 # 返回主菜单")
        print("支持的 URL 格式: https://vgmdb.net/product/<id>")
        while True:
            url = input("请输入链接：").strip()
            if url == "#":
                print("返回主菜单")
                return
            Vgm(self.config['vgm']).process(url)
