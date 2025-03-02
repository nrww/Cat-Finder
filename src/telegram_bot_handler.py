# telegram_bot_handler.py
import os
import time
import logging
import telebot

class TelegramBotHandler:
    def __init__(self, token):
        self.bot = telebot.TeleBot(token)
        self.listener_list = []
        self.debug_users = set()  # ID пользователей, включивших режим отладки
        self.conf = 0.5
        self.motion_threshold = 500  # Порог для детекции движения
        self.ip_file = 'clients_id.dat'
        self.load_listeners()

    def load_listeners(self):
        if os.path.exists(self.ip_file):
            with open(self.ip_file, 'r') as f:
                self.listener_list = [int(line.strip()) for line in f if line.strip()]
            logging.info(f"Loaded {len(self.listener_list)} listeners from {self.ip_file}")
        else:
            self.listener_list = []
            logging.info("No listener file found. Starting with an empty list.")

    def save_listener(self, user_id):
        if user_id not in self.listener_list:
            self.listener_list.append(user_id)
            with open(self.ip_file, 'a') as f:
                f.write(f"{user_id}\n")
            logging.info(f"Added new listener: {user_id}")

    def send_notification(self, image_to_process, message):
        # Обычные уведомления для всех подписанных пользователей
        for chat_id in self.listener_list:
            try:
                if message:
                    self.bot.send_message(chat_id=chat_id, text=message)
                self.bot.send_photo(chat_id=chat_id, photo=image_to_process, timeout=30)
                logging.info(f"Sent notification to {chat_id}: {message}")
            except Exception as e:
                logging.error(f"Failed to send notification to {chat_id}: {e}")

    def send_debug_notification(self, image_to_process, message):
        # Уведомления отладки только для пользователей, включивших debug режим
        for chat_id in self.debug_users:
            try:
                if message:
                    self.bot.send_message(chat_id=chat_id, text=message)
                self.bot.send_photo(chat_id=chat_id, photo=image_to_process, timeout=30)
                logging.info(f"Sent debug notification to {chat_id}: {message}")
            except Exception as e:
                logging.error(f"Failed to send debug notification to {chat_id}: {e}")

    def start_bot(self):
        @self.bot.message_handler(commands=['start'])
        def handle_start(message):
            self.bot.send_message(message.chat.id, "Привет! Вы подписаны!")
            self.save_listener(message.chat.id)
            logging.info(f"User {message.chat.id} started the bot and was added to listeners.")

        @self.bot.message_handler(commands=['conf'])
        def handle_conf(message):
            sent_msg = self.bot.send_message(message.chat.id, f"Введите значение порога уверенности (0.0 - 1.0). Сейчас: {self.conf}")
            self.bot.register_next_step_handler(sent_msg, set_confidence)

        def set_confidence(message):
            try:
                conf_value = float(message.text)
                if 0.0 <= conf_value <= 1.0:
                    self.conf = conf_value
                    self.bot.send_message(message.chat.id, f"Значение порога уверенности установлено на {conf_value}")
                    logging.info(f"Confidence threshold updated to {conf_value} by user {message.chat.id}")
                else:
                    self.bot.send_message(message.chat.id, f"Пожалуйста, введите число от 0.0 до 1.0. Сейчас: {self.conf}")
            except ValueError:
                self.bot.send_message(message.chat.id, "Некорректное значение. Пожалуйста, введите число.")

        @self.bot.message_handler(commands=['motion_threshold'])
        def handle_motion_threshold(message):
            sent_msg = self.bot.send_message(message.chat.id, f"Введите значение порога движения (целое число). Сейчас: {self.motion_threshold}")
            self.bot.register_next_step_handler(sent_msg, set_motion_threshold)

        def set_motion_threshold(message):
            try:
                threshold_value = int(message.text)
                if threshold_value > 0:
                    self.motion_threshold = threshold_value
                    self.bot.send_message(message.chat.id, f"Значение порога движения установлено на {threshold_value}")
                    logging.info(f"Motion threshold updated to {threshold_value} by user {message.chat.id}")
                else:
                    self.bot.send_message(message.chat.id, "Пожалуйста, введите положительное целое число.")
            except ValueError:
                self.bot.send_message(message.chat.id, "Некорректное значение. Пожалуйста, введите целое число.")

        @self.bot.message_handler(commands=['debug'])
        def handle_debug(message):
            args = message.text.split()
            if len(args) < 2:
                self.bot.send_message(message.chat.id, "Usage: /debug on|off")
                return
            if args[1].lower() == "on":
                self.debug_users.add(message.chat.id)
                self.bot.send_message(message.chat.id, "Debug mode enabled. Вы будете получать отладочные уведомления.")
                logging.info(f"Debug mode enabled for user {message.chat.id}")
            elif args[1].lower() == "off":
                if message.chat.id in self.debug_users:
                    self.debug_users.remove(message.chat.id)
                self.bot.send_message(message.chat.id, "Debug mode disabled.")
                logging.info(f"Debug mode disabled for user {message.chat.id}")
            else:
                self.bot.send_message(message.chat.id, "Usage: /debug on|off")

        while True:
            try:
                self.bot.polling(none_stop=True)
            except Exception as e:
                logging.error(f"Error in bot polling: {e}")
                time.sleep(15)
