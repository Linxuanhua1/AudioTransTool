import concurrent.futures, os, tomllib, logging, multiprocessing
from tqdm import tqdm
from lib.audio_handler import AudioHandler, Splitter, EXCLUDED_DIRS
from lib.image_handler import ImageHandler
from lib.common_method import check_input_folder_path, setup_logger


if __name__ == '__main__':
    with multiprocessing.Manager() as manager:
        os.environ['PATH'] = os.environ['PATH'] + os.pathsep + os.getcwd() + '/encoders/'
        logger, queue, listener = setup_logger(manager)

        with open("lib/config.toml", 'rb') as f:
            config = tomllib.load(f)

        folder_path = check_input_folder_path()
        logger.info('开始音频转码')
        all_audio = []
        for root, dirs, files in os.walk(folder_path):
            [dirs.remove(d) for d in list(dirs) if d.lower() in EXCLUDED_DIRS]
            for file in files:
                audio_path = os.path.join(root, file)
                handler = AudioHandler.append_task(audio_path)
                if handler:
                    all_audio.append((queue, audio_path, handler, config))
        if all_audio:
            with concurrent.futures.ProcessPoolExecutor(max_workers=config['max_workers']) as executor:
                list(tqdm(executor.map(AudioHandler.worker_wrapper, all_audio), total=len(all_audio),
                                   desc='音频转码中'))
        else:
            logger.info("没有符合条件的音频需要转码")
        logger.info('音频转码结束')
        logger.info('-' * 100)

        lock = manager.Lock()
        all_splitting = []
        if config['activate_cue_splitting']:
            logger.info('开始音频分轨')
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = Splitter.append_task(root, file)
                    if file_path:
                        all_splitting.append((queue, file_path, config, lock))  # 传 manager.Lock()
            if all_splitting:
                with concurrent.futures.ProcessPoolExecutor(max_workers=config['max_workers']) as executor:
                    list(tqdm(executor.map(Splitter.worker_wrapper, all_splitting), total=len(all_splitting),
                                       desc='音频分轨中'))
            else:
                logger.info("没有符合条件的音频需要分轨")
            logger.info('音频分轨结束')
        logger.info('-' * 100)

        if config['activate_image_transc']:
            logger.info('开始图片转码')
            all_img = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    img_path = os.path.join(root, file)
                    result = ImageHandler.append_task(img_path)
                    if result:
                        img_path, handler, name = result
                        all_img.append((queue, img_path, handler, name, config))
            if all_img:
                with concurrent.futures.ProcessPoolExecutor(max_workers=config['max_workers']) as executor:
                    list(tqdm(executor.map(ImageHandler.worker_wrapper, all_img),
                                       total=len(all_img), desc='图片转码中'))
            else:
                logger.info("没有符合条件的图片需要转码")
            logger.info('图片转码结束')

            queue.put_nowait(None)
            listener.join()