import os, tifffile, subprocess, logging
from PIL import Image
from lib.common_method import get_root_dir_and_name, setup_worker_logger

logger = logging.getLogger(__name__)

SUPPORTED_COLOR_SPACE = ['L', 'RGB', 'RGBA', 'YCbCr', 'I', 'I;16', 'P', '1', 'LA', 'RGBX']

Image.MAX_IMAGE_PIXELS = None

class ImageHandler:
    @staticmethod
    def is_allowed_to_convert(file_path):
        if file_path.lower().endswith('.tif') or file_path.lower().endswith('.tiff'):
            return ImageHandler._get_tif_color_space_and_bits_per_sample(file_path)
        else:
            return ImageHandler._get_common_format_color_space(file_path)

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

    @staticmethod
    def _copy_metadata(input_file_path, output_file_path):
        cmd = ['exiftool', '-m', '-overwrite_original', '-tagsFromFile', f'{input_file_path}', f'-all:all', f'{output_file_path}']
        subprocess.run(cmd, capture_output=True, text=True, check=True)

    @staticmethod
    def _bmp_webp_tif2png(file_path):
        root, _ = os.path.splitext(file_path)
        output = f'{root}.png'
        with Image.open(file_path) as img:
            img.save(output)
        return output

    @staticmethod
    def _encode_jxl(file_path):
        root, _ = os.path.splitext(file_path)
        cmd = ['cjxl', '-j', '1', '--container', '1', '-q', '100', '--num_threads=16', f'{file_path}', f'{root}.jxl']
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise Exception('可能是单个文件夹路径超过了260字符，请检查一下')
        return f'{root}.jxl'

    @staticmethod
    def jpg_png2jxl(file_path, is_delete_origin_img):
        logger.info('正在将图片转换为jxl')
        output_path = ImageHandler._encode_jxl(file_path)
        logger.info('成功转换为jxl')
        ImageHandler._copy_metadata(file_path, output_path)
        logger.info('成功复制源图片的exif和xmp信息到jxl文件')
        if is_delete_origin_img:
            os.remove(file_path)
            logger.info(f"成功删除源文件")

    @staticmethod
    def bmp_webp_tif2jxl(file_path, is_delete_origin_img):
        logger.info('正在将图片转换为png缓存')
        tmp_png_path = ImageHandler._bmp_webp_tif2png(file_path)
        logger.info('缓存成功')
        logger.info('正在将图片转换为jxl')
        output_path = ImageHandler._encode_jxl(tmp_png_path)
        logger.info('成功转换为jxl')
        ImageHandler._copy_metadata(file_path, output_path)
        logger.info('成功复制源图片的exif和xmp信息到jxl文件')
        os.remove(tmp_png_path)
        logger.info(f"成功删除缓存文件")
        if is_delete_origin_img:
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

# ---------------------------- 多线程部分 -----------------------------------------------
    @staticmethod
    def process_image(img_path, handler, name, config):
        logger.info(f'即将处理图片')
        if name.lower() == 'cover':
            ImageHandler.cover2png(img_path)
        else:
            handler(img_path, config['is_delete_origin_img'])
        logger.info(f'转换完成')
        logger.info('-' * 100)

    @staticmethod
    def append_task(img_path):
        _, ext = os.path.splitext(img_path)
        _, name = get_root_dir_and_name(img_path)
        handler = IMAGE_HANDLER.get(ext)
        if name + ext == 'Cover.png':
            return
        if handler:
            if ImageHandler.is_allowed_to_convert(img_path):
                return img_path, handler, name

    @staticmethod
    def worker_wrapper(task):
        try:
            queue, img_path, handler, name, config = task
            if not logger.handlers:
                setup_worker_logger(logger, queue)
            ImageHandler.process_image(img_path, handler, name, config)
        except Exception as e:
            logger.error(f"{task[1]} 图片转码失败: {e}")


IMAGE_HANDLER = {
    '.jpeg': ImageHandler.jpg_png2jxl,
    '.jpg': ImageHandler.jpg_png2jxl,
    '.png': ImageHandler.jpg_png2jxl,
    '.bmp': ImageHandler.bmp_webp_tif2jxl,
    '.tif': ImageHandler.bmp_webp_tif2jxl,
    '.tiff': ImageHandler.bmp_webp_tif2jxl,
    '.webp': ImageHandler.bmp_webp_tif2jxl
}