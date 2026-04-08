from lib.img.image_handler import *


IMAGE_HANDLER = {
    '.jpeg': JpgHandler,
    '.jpg': JpgHandler,
    '.png': PngHandler,
    '.bmp': BmpHandler,
    '.tif': TiffHandler,
    '.tiff': TiffHandler,
    '.webp': WebpHandler
}