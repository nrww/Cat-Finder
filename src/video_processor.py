# video_processor.py
import cv2
import numpy as np
import os
import time
import queue
import threading
import logging
from ultralytics import YOLO
from utils import catmull_rom_spline
from config import MODEL_PATH

class VideoProcessor:
    def __init__(self, cam_url, telegram_bot_handler, cam_id=1):
        self.cam_url = cam_url
        self.bot_handler = telegram_bot_handler
        self.cam_id = cam_id
        # Инициализируем модель
        self.model = YOLO(MODEL_PATH)
        self.cap = self.VideoCapture(self.cam_url)
        self.last_time = time.time() - 30
        self.pos_trace = []
        self.trace_time = time.time()
        self.flag_trace = False
        self.fps_time = time.time()
        self.fps_cnt = 0
        self.last_founded_frame = None
        self.prev_gray = None  # Для детекции движения
        
        frame = self.cap.read()
        self.height, self.width, _ = frame.shape
        self.height = (self.height + 32 - 1) // 32 * 32
        self.width = (self.width + 32 - 1) // 32 * 32
        
        if self.cam_id == 4:
            points = [(1279, 271), (1490, 577), (1710, 980)]
            smooth_points = catmull_rom_spline(points, num_points=200)
            points = np.array(smooth_points, np.int32)
            self.points = points.reshape((-1, 1, 2))
        
            
        logging.info(f"Cam {self.cam_id} activated!")

    class VideoCapture:
        def __init__(self, name):
            self.name = name
            self.cap = None
            self.q = queue.Queue()
            self.running = True
            t = threading.Thread(target=self._reader)
            t.daemon = True
            t.start()

        def _connect(self):
            while self.running:
                try:
                    self.cap = cv2.VideoCapture(self.name)
                    if self.cap.isOpened():
                        logging.info(f"Successfully connected to camera: {self.name}")
                        return
                    else:
                        logging.warning(f"Failed to connect to camera: {self.name}. Retrying...")
                        time.sleep(5)
                except Exception as e:
                    logging.error(f"Error while connecting to camera: {self.name}: {e}")
                    time.sleep(5)

        def _reader(self):
            self._connect()
            while self.running:
                try:
                    if self.cap is None or not self.cap.isOpened():
                        logging.warning(f"Camera {self.name} is not opened. Reconnecting...")
                        self._connect()
                        continue
                    
                    ret, frame = self.cap.read()
                    if not ret:
                        logging.warning(f"Failed to read frame from camera: {self.name}. Retrying...")
                        self._connect()
                        continue
                    
                    if not self.q.empty():
                        try:
                            self.q.get_nowait()
                        except queue.Empty:
                            pass
                    self.q.put(frame)
                except Exception as e:
                    logging.error(f"Error while reading frame from camera: {self.name}: {e}")
                    self._connect()

        def read(self):
            return self.q.get()

        def stop(self):
            self.running = False
            if self.cap and self.cap.isOpened():
                self.cap.release()
            logging.info(f"Stopped video capture for camera: {self.name}")

    def draw_trace(self, image, positions):
        color = (0, 255, 0)
        thickness = 3
        last_pos = positions[0]
        for pos in positions[1:]:
            image = cv2.arrowedLine(image, last_pos, pos, color, thickness)
            last_pos = pos
        success, a_numpy = cv2.imencode('.jpg', image)
        if success:
            a = a_numpy.tobytes()
            self.bot_handler.send_debug_notification(a, 'Trace drawn.')
            logging.info("Sent trace image to debug users.")
        else:
            logging.error("Failed to encode trace image.")

    def mask_datetime(self, frame):
        if self.cam_id == 1:
            x, y, w, h = 2245, 88, 215, 50
        else:
            x, y, w, h = 1755, 35, 135, 30
        mask_color = (0, 0, 0)
        if self.cam_id == 4:
            cv2.polylines(frame, [self.points], isClosed=False, color=mask_color, thickness=45)
        cv2.rectangle(frame, (x, y), (x + w, y + h), mask_color, -1)
        return frame

    def detect_motion(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = self.mask_datetime(gray)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        if self.prev_gray is None:
            self.prev_gray = gray
            return False
        frame_delta = cv2.absdiff(self.prev_gray, gray)
        self.prev_gray = gray

        thresh = cv2.threshold(frame_delta, 20, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        thresh = cv2.erode(thresh, None, iterations=1)
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        motion_detected = False
        min_area = self.bot_handler.motion_threshold
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > min_area:
                motion_detected = True
                logging.debug(f"Motion detected on camera {self.cam_id} with contour area: {area}")
                # Если включен debug режим, отрисовываем контур и отправляем уведомление только debug-пользователю
                if self.bot_handler.debug_users:
                    cv2.drawContours(frame, [contour], -1, (0, 255, 0), 2)
                    debug_message = f"Motion detected on camera {self.cam_id} with contour area: {area}"
                    success, a_numpy = cv2.imencode('.jpg', frame)
                    if success:
                        a = a_numpy.tobytes()
                        self.bot_handler.send_debug_notification(a, debug_message)
                        logging.info(f"Sent debug notification for motion on camera {self.cam_id}")
                    else:
                        logging.error("Failed to encode debug image.")
                break
        return motion_detected

    def start_processing(self):
        while True:
            try:
                frame = self.cap.read()
                if frame is None:
                    logging.warning(f"Received empty frame from camera {self.cam_id}")
                    continue

                motion = self.detect_motion(frame)
                if self.bot_handler.debug_users:
                    self.fps_cnt += 1
                    if time.time() - self.fps_time > 10:
                        fps = self.fps_cnt / (time.time() - self.fps_time)
                        logging.debug(f"Cam {self.cam_id} has {fps:.2f} FPS")
                        self.fps_cnt = 0
                        self.fps_time = time.time()
                if not motion:
                    continue

                results = self.model(frame, conf=0.2, device=0, classes=[15, 16], verbose=False, imgsz=(self.width, self.height))
                for result in results:
                    for box in result.boxes:
                        x, y, w, h = box.xywh.tolist()[0]
                        if float(box.conf.item()) > self.bot_handler.conf:
                            self.last_founded_frame = result.plot()
                            if time.time() - self.last_time > 30:
                                success, a_numpy = cv2.imencode('.jpg', self.last_founded_frame)
                                if success:
                                    a = a_numpy.tobytes()
                                    class_id = int(box.cls.item())
                                    message = 'Кот найден' if class_id == 15 else 'Собака найдена'
                                    self.bot_handler.send_notification(a, message)
                                    self.last_time = time.time()
                                    logging.info(f"{message} on camera {self.cam_id}")
                                else:
                                    logging.error("Failed to encode image for notification.")
                                if not self.flag_trace:
                                    self.flag_trace = True
                        if self.flag_trace:
                            self.pos_trace.append((int(x), int(y)))
                            self.trace_time = time.time()
                if self.flag_trace and time.time() - self.trace_time > 3:
                    if len(self.pos_trace) > 3 and self.last_founded_frame is not None:
                        self.draw_trace(self.last_founded_frame, self.pos_trace)
                        self.flag_trace = False
                    self.pos_trace = []
            except Exception as e:
                logging.error(f"Error in camera {self.cam_id} processing: {e}")
                time.sleep(1)
