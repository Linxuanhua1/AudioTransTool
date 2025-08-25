import os, tifffile, subprocess, logging
from PIL import Image
from lib.utils import get_root_dir_and_name

os.environ['PATH'] = os.environ['PATH'] + os.pathsep + os.path.dirname(os.getcwd()) + '/bin/'

logger = logging.getLogger(__name__)

SUPPORTED_COLOR_SPACE = ['L', 'RGB', 'RGBA', 'YCbCr', 'I', 'I;16', 'P', '1', 'LA', 'RGBX']

Image.MAX_IMAGE_PIXELS = None


def setup_image_module_logger(work_logger):
    global logger
    logger = work_logger


class ImageProbe:
    @classmethod
    def is_allowed_to_convert(cls, file_path):
        if file_path.lower().endswith('.tif') or file_path.lower().endswith('.tiff'):
            return cls._get_tif_color_space_and_bits_per_sample(file_path)
        else:
            return cls._get_common_format_color_space(file_path)

    @staticmethod
    def _get_tif_color_space_and_bits_per_sample(file_path):
        with tifffile.TiffFile(file_path) as tif:
            page = tif.pages[0]
            color_space = page.tags.get('PhotometricInterpretation').value
            bits_per_sample = page.tags.get('BitsPerSample').value
            bits_per_sample = bits_per_sample if isinstance(bits_per_sample, int) else bits_per_sample[0]
        match color_space:
            case 0:  # 灰度图 0=白
                mode =  "L"
            case 1:  # 灰度图 0=黑
                mode = "L"
            case 2:  # 标准RGB
                mode = 'RGB'
            case 3:  # 索引色
                mode = 'P'
            case 4:  # 透明遮罩
                mode = '1'
            case 5:  # CMYK
                mode = 'CMYK'
            case 6:  # 亮度-色度
                mode = "YCbCr"
            case _:
                mode = 'Unsupported'
        if mode in SUPPORTED_COLOR_SPACE and bits_per_sample <= 8:
            return True
        else:
            logger.info(f"不支持的tif图像，{file_path}")
            return False

    @staticmethod
    def _get_common_format_color_space(file_path):
        img = Image.open(file_path)
        mode = img.mode
        img.close()
        if mode in SUPPORTED_COLOR_SPACE:
            return True
        else:
            return False


class ImageEncoder:
    @staticmethod
    def copy_metadata(input_file_path, output_file_path):
        cmd = ['exiftool', '-m', '-overwrite_original', '-tagsFromFile', f'{input_file_path}', f'-all:all', f'{output_file_path}']
        subprocess.run(cmd, capture_output=True, text=True, check=True)

    @staticmethod
    def to_png(file_path):
        root, _ = os.path.splitext(file_path)
        output = f'{root}.png'
        with Image.open(file_path) as img:
            img.save(output)
        return output

    @staticmethod
    def to_jxl(file_path):
        root, _ = os.path.splitext(file_path)
        cmd = ['cjxl', '-j', '1', '--container', '1', '-q', '100', '--num_threads=16', f'{file_path}', f'{root}.jxl']
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8')
        except subprocess.CalledProcessError as e:
            raise Exception('可能是单个文件夹路径超过了260字符，请检查一下')
        return f'{root}.jxl'


class ImageConversionExecutor:
    @staticmethod
    def direct2jxl(file_path, is_del_source_img):
        logger.info('正在将图片转换为jxl')
        output_path = ImageEncoder.to_jxl(file_path)
        logger.info('成功转换为jxl')
        ImageEncoder.copy_metadata(file_path, output_path)
        logger.info('成功复制源图片的exif和xmp信息到jxl文件')
        if is_del_source_img:
            os.remove(file_path)
            logger.info(f"成功删除源文件")

    @staticmethod
    def via_png2jxl(file_path, is_del_source_img):
        logger.info('正在将图片转换为png缓存')
        tmp_png_path = ImageEncoder.to_png(file_path)
        logger.info('缓存成功')
        logger.info('正在将图片转换为jxl')
        output_path = ImageEncoder.to_jxl(tmp_png_path)
        logger.info('成功转换为jxl')
        ImageEncoder.copy_metadata(file_path, output_path)
        logger.info('成功复制源图片的exif和xmp信息到jxl文件')
        os.remove(tmp_png_path)
        logger.info(f"成功删除缓存文件")
        if is_del_source_img:
            os.remove(file_path)
            logger.info(f"成功删除源文件")

    @staticmethod
    def cover2png(file_path):
        _, ext = os.path.splitext(file_path)
        root, name = get_root_dir_and_name(file_path)
        if ext.lower() != '.png':
            with Image.open(file_path) as img:
                img.save(f"{root}/Cover.png")
            logger.info(f'成功将封面源文件转换为png')
            os.remove(file_path)
            logger.info(f'成功删除封面源文件')
            return
        if name != 'Cover':
            tmp_cover_path = f"{root}/Cover_tmp.png"
            output_path = f"{root}/Cover.png"
            os.rename(file_path, tmp_cover_path)
            os.rename(tmp_cover_path, output_path)
            logger.info("成功将封面重命名为Cover.png")


class ImageHandler:
    @staticmethod
    def jpg2jxl(file_path, is_del_source_img):
        return ImageConversionExecutor.direct2jxl(file_path, is_del_source_img)

    @staticmethod
    def png2jxl(file_path, is_del_source_img):
        return ImageConversionExecutor.direct2jxl(file_path, is_del_source_img)

    @staticmethod
    def bmp2jxl(file_path, is_del_source_img):
        return ImageConversionExecutor.via_png2jxl(file_path, is_del_source_img)

    @staticmethod
    def webp2jxl(file_path, is_del_source_img):
        return ImageConversionExecutor.via_png2jxl(file_path, is_del_source_img)

    @staticmethod
    def tif2jxl(file_path, is_del_source_img):
        return ImageConversionExecutor.via_png2jxl(file_path, is_del_source_img)

    @staticmethod
    def cover2png(file_path):
        return ImageConversionExecutor.cover2png(file_path)