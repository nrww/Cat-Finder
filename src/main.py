# main.py
import time
import threading
import logging
from telegram_bot_handler import TelegramBotHandler
from video_processor import VideoProcessor
import config
from logger_config import setup_logger

def main():
    setup_logger()
    bot_handler = TelegramBotHandler(config.BOT_TOKEN)
    cam_urls = [
        (config.CAM_URL1, 1),
        (config.CAM_URL2, 2),
        (config.CAM_URL3, 3),
        (config.CAM_URL4, 4),
        (config.CAM_URL5, 5),
        (config.CAM_URL6, 6)
    ]
    processors = []
    for cam_url, cam_id in cam_urls:
        processor = VideoProcessor(cam_url, bot_handler, cam_id)
        processors.append(processor)

    bot_thread = threading.Thread(target=bot_handler.start_bot)
    bot_thread.daemon = True
    bot_thread.start()

    for processor in processors:
        t = threading.Thread(target=processor.start_processing)
        t.daemon = True
        t.start()

    logging.info('Бот запущен')
    while True:
        time.sleep(1)

if __name__ == '__main__':
    main()
