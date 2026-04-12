import json, subprocess, logging
from pathlib import Path


logger = logging.getLogger(__name__)


class MediaProbe:
    @staticmethod
    def probe(file_p: Path | list[Path]) -> list[dict]:
        paths = MediaProbe._normalize_paths(file_p)
        if not paths:
            return None

        wv_paths = [p for p in paths if p.suffix.lower() == ".wv"]
        other_paths = [p for p in paths if p.suffix.lower() != ".wv"]

        results: list[dict] = []

        # exiftool 可以批量
        if other_paths:
            other_results = MediaProbe._probe_other_batch(other_paths)
            if other_results:
                results.extend(other_results)

        # wvunpack -s 不能一次直接传多个文件，否则第二个会被当成 outfile
        for path in wv_paths:
            result = MediaProbe._probe_wv(path)
            if result:
                results.append(result)

        return results

    @staticmethod
    def _normalize_paths(file_p: Path | list[Path]) -> list[Path]:
        if isinstance(file_p, Path):
            return [file_p]
        return list(file_p)

    @staticmethod
    def _probe_wv(file_p: Path) -> dict | None:
        try:
            cmd = ["wvunpack", "-s", str(file_p)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding="utf-8")
            parsed = MediaProbe.parse_wvunpack_output(result.stdout)
            parsed['SourceFile'] = str(file_p)
            return parsed
        except subprocess.CalledProcessError as e:
            logger.error(e.stderr)
            logger.error(e.stdout)
            return None

    @staticmethod
    def _probe_other_batch(paths: list[Path]) -> list[dict] | None:
        try:
            cmd = ["exiftool", "-j", "-n", "-@", "-"]
            input_text = "\n".join(str(p) for p in paths)

            result = subprocess.run(cmd, input=input_text, capture_output=True, text=True, check=True, encoding="utf-8")
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            error_msg = []
            for result in json.loads(e.stdout):
                error = result.get("Error", None)
                if error:
                    error_msg.append(error)

            for error in error_msg:
                if error == "Unknown file type":
                    logger.error(e.stdout)
                    return None

            return json.loads(e.stdout)

    @staticmethod
    def parse_wvunpack_output(text: str) -> dict:
        result = {}

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            if line.startswith("WVUNPACK"):
                continue
            if line.startswith("Copyright"):
                continue

            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()

        return result