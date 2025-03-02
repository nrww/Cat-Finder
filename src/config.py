import os

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
# Переменная окружения CAM_URLS должна содержать список URL камер, разделённых запятыми
CAM_URLS = [url.strip() for url in os.getenv("CAM_URLS", "").split(",") if url.strip()]

MODEL_PATH = "models/yolo11x.pt"

