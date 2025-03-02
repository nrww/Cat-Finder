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
    processors = []
    
    # Для каждого URL из списка CAM_URLS создаём процессор
    for idx, cam_url in enumerate(config.CAM_URLS, start=1):
        processor = VideoProcessor(cam_url, bot_handler, cam_id=idx)
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
