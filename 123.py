from telethon import TelegramClient, events
import asyncio
import re
import logging
from datetime import datetime
import os
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация - ЗАМЕНИ ЭТИ ЗНАЧЕНИЯ НА СВОИ!
API_ID = 36901544  # Твой API ID из my.telegram.org
API_HASH = '43fe9955cd5ec97746ed835daf756b03'  # Твой API Hash из my.telegram.org
PHONE_NUMBER = '+13093265422'  # Твой номер телефона

# Группы где слушаем триггеры (ЗАМЕНИ НА СВОИ ID групп!)
TARGET_GROUPS = [
    -1003514324234,  # Группа 1
    -1003624451447,  # Группа 2
    -1003744344962,  # Группа 3
    -1003788614771,
]

# Триггер слова (можно добавить свои)
TRIGGER_WORDS = [
    'слет', 'ckt', 'cktу', 'cktн', 'ном', 'номер',
    'блок', 'заблок', 'блпк', 'блрк', 'нрм', 'слёт',
    'sl', 'slet', 'nomer', 'nom'
]

class SimpleBot:
    def __init__(self):
        # Используем имя сессии 'session_bot' как у тебя
        session_name = 'session_bot'
        
        self.client = TelegramClient(session_name, API_ID, API_HASH)
        
        # Текущий номер
        self.current_number = None
        self.is_waiting_trigger = False
        
        # Отслеживаем куда уже отправили
        self.sent_to_chats = set()
        
        # Сохраняем инфу о последней отправке
        self.last_sent_info = {}
        
        self.me = None
        
        logger.info("Бот инициализирован")
    
    async def start(self):
        """Запуск бота"""
        try:
            # Проверяем существует ли сессия
            session_file = f'{self.client.session.filename}.session'
            if os.path.exists(session_file):
                logger.info(f"Найдена сессия: {session_file}")
                file_size = os.path.getsize(session_file)
                logger.info(f"Размер файла сессии: {file_size} байт")
                
                if file_size == 0:
                    logger.warning("Файл сессии пустой! Будет создана новая сессия.")
            
            # Пробуем подключиться с существующей сессией
            await self.client.start(phone=PHONE_NUMBER)
            self.me = await self.client.get_me()
            logger.info(f"✅ Авторизован как: {self.me.first_name} (@{self.me.username})")
            logger.info(f"Слушаю триггеры в {len(TARGET_GROUPS)} группах")
            logger.info("Бот запущен! Кидай номер в избранное")
            
            self.register_handlers()
            
            # Проверяем соединение
            await self.client.send_message('me', '🤖 Бот успешно запущен на Render!')
            
            await self.client.run_until_disconnected()
            
        except Exception as e:
            logger.error(f"Ошибка запуска: {e}")
            
            # Если ошибка авторизации, удаляем сессию
            if "auth key" in str(e).lower() or "session" in str(e).lower():
                session_file = f'{self.client.session.filename}.session'
                if os.path.exists(session_file):
                    logger.error(f"⚠️ Проблема с сессией. Удаляю: {session_file}")
                    os.remove(session_file)
            
            raise
    
    def get_message_link(self, chat_id, message_id, topic_id=0):
        """Получаем правильную ссылку на сообщение"""
        try:
            # Для приватных супергрупп (chat_id отрицательный)
            if chat_id < 0:
                # Убираем -100 префикс для ссылки
                if str(chat_id).startswith('-100'):
                    channel_id = int(str(chat_id)[4:])  # Убираем -100
                else:
                    channel_id = abs(chat_id)
                
                # Для топиков
                if topic_id and topic_id != 0:
                    # Формат: https://t.me/c/3514324234/4/15382
                    return f"https://t.me/c/{channel_id}/{topic_id}/{message_id}"
                else:
                    # Без топика
                    return f"https://t.me/c/{channel_id}/{message_id}"
            
            # Для публичных чатов с username
            else:
                return f"chat_id: {chat_id}, message_id: {message_id}"
            
        except Exception as e:
            logger.error(f"Ошибка формирования ссылки: {e}")
            return f"Ошибка ссылки: {e}"
    
    def register_handlers(self):
        """Регистрация обработчиков"""
        
        # 1. Обработка номера в избранном
        @self.client.on(events.NewMessage(func=lambda e: e.is_private))
        async def handle_saved_messages(event):
            # Проверяем, что это избранное
            if event.sender_id != self.me.id or event.chat_id != self.me.id:
                return
            
            text = event.message.text or ''
            logger.info(f"Получено в избранном: {text}")
            
            # Ищем номер
            phone_match = re.search(r'(?:\+7|7|8)\d{10}', text)
            
            if phone_match:
                phone = phone_match.group()
                self.current_number = phone
                self.is_waiting_trigger = True
                self.sent_to_chats.clear()
                self.last_sent_info.clear()
                
                logger.info(f"✅ ЗАПОМНИЛ НОМЕР: {phone}")
                await event.reply(f"✅ Номер {phone} принят!\nЖду триггеры...")
        
        # 2. Обработка триггеров в целевых группах
        @self.client.on(events.NewMessage(chats=TARGET_GROUPS))
        async def handle_group_triggers(event):
            if event.sender_id == self.me.id:
                return
            
            if not self.is_waiting_trigger or not self.current_number:
                return
            
            text = (event.message.text or '').lower().strip()
            
            # Проверяем триггер слова
            is_trigger = any(trigger in text for trigger in TRIGGER_WORDS)
            
            if not is_trigger:
                return
            
            # Получаем chat_id и topic_id
            chat_id = event.chat_id
            topic_id = event.message.reply_to_msg_id
            
            if not topic_id:
                topic_id = 0  # General топик
            
            # Создаем уникальный ключ
            chat_key = f"{chat_id}_{topic_id}"
            
            # Если уже отправили в этот топик - пропускаем
            if chat_key in self.sent_to_chats:
                return
            
            logger.info(f"Триггер в чате {chat_id}, топик {topic_id}: '{text}'")
            
            try:
                # Отправляем сообщение
                if topic_id and topic_id != 0:
                    sent_message = await self.client.send_message(
                        entity=chat_id,
                        message=self.current_number,
                        reply_to=topic_id
                    )
                else:
                    sent_message = await self.client.send_message(
                        entity=chat_id,
                        message=self.current_number
                    )
                
                # Получаем ID отправленного сообщения
                sent_message_id = sent_message.id
                
                # Формируем ПРАВИЛЬНУЮ ссылку
                message_link = self.get_message_link(chat_id, sent_message_id, topic_id)
                
                self.sent_to_chats.add(chat_key)
                
                # Сохраняем инфу о последней отправке
                self.last_sent_info = {
                    'chat_id': chat_id,
                    'topic_id': topic_id,
                    'message_id': sent_message_id,
                    'message_link': message_link,
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                }
                
                logger.info(f"Отправил номер {self.current_number} в чат {chat_id}, топик {topic_id}")
                logger.info(f"Ссылка: {message_link}")
                
                # Если отправили хотя бы в один топик
                if len(self.sent_to_chats) >= 1:
                    self.is_waiting_trigger = False
                    
                    # Формируем удобное уведомление
                    notification = f"""✅ НОМЕР ОТПРАВЛЕН!

📱 Номер: {self.current_number}
💬 Чат ID: {chat_id}
🎯 Топик: {topic_id if topic_id != 0 else 'General'}
📨 ID сообщения: {sent_message_id}
🕐 Время: {datetime.now().strftime('%H:%M:%S')}

🔗 Ссылка:
{message_link}

⏳ Жду следующий номер..."""
                    
                    # Уведомляем в избранное
                    await self.client.send_message(
                        self.me.id,
                        notification
                    )
                    
            except Exception as e:
                logger.error(f"Ошибка отправки в {chat_id} (топик {topic_id}): {e}")
        
        # 3. Команды в ЛС
        @self.client.on(events.NewMessage(func=lambda e: e.is_private and e.sender_id != self.me.id))
        async def handle_private_commands(event):
            text = (event.message.text or '').lower().strip()
            
            if text == '/status':
                status_text = ""
                if self.current_number and self.is_waiting_trigger:
                    status_text = f"""📱 ТЕКУЩИЙ СТАТУС:

✅ Номер готов: {self.current_number}
⏱ Ожидает триггеров...
📊 Отправлен в {len(self.sent_to_chats)} топиков"""
                elif self.last_sent_info:
                    status_text = f"""📱 ПОСЛЕДНЯЯ ОТПРАВКА:

📱 Номер: {self.current_number or 'нет'}
💬 Чат ID: {self.last_sent_info.get('chat_id', 'нет')}
🎯 Топик: {self.last_sent_info.get('topic_id', 0) if self.last_sent_info.get('topic_id', 0) != 0 else 'General'}
📨 ID сообщения: {self.last_sent_info.get('message_id', 'нет')}
🕐 Время: {self.last_sent_info.get('timestamp', 'нет')}

🔗 Ссылка:
{self.last_sent_info.get('message_link', 'нет')}"""
                else:
                    status_text = "❌ Нет активного номера\nКинь номер в избранное"
                
                await event.reply(status_text)
            
            elif text == '/reset':
                self.current_number = None
                self.is_waiting_trigger = False
                self.sent_to_chats.clear()
                await event.reply("✅ Сброшено! Жду новый номер")
            
            elif text == '/groups':
                groups_info = "🎯 МОИ ГРУППЫ:\n\n"
                for i, group_id in enumerate(TARGET_GROUPS, 1):
                    groups_info += f"{i}. ID: {group_id}\n"
                await event.reply(groups_info)
            
            elif text == '/triggers':
                triggers_info = "🎯 ТРИГГЕР СЛОВА:\n\n" + "\n".join(TRIGGER_WORDS)
                await event.reply(triggers_info)
            
            elif text == '/last':
                # Показать последнюю отправку
                if self.last_sent_info:
                    last_info = f"""📱 ПОСЛЕДНЯЯ ОТПРАВКА:

📱 Номер: {self.current_number or 'нет'}
💬 Чат ID: {self.last_sent_info.get('chat_id', 'нет')}
🎯 Топик: {self.last_sent_info.get('topic_id', 0)}
📨 ID сообщения: {self.last_sent_info.get('message_id', 'нет')}
🕐 Время: {self.last_sent_info.get('timestamp', 'нет')}

🔗 Ссылка:
{self.last_sent_info.get('message_link', 'нет')}

📋 Кликни по ссылке!"""
                else:
                    last_info = "❌ Нет информации о последней отправке"
                await event.reply(last_info)
            
            elif text.startswith('/номер'):
                parts = text.split()
                if len(parts) == 2:
                    phone = parts[1]
                    if re.match(r'(?:\+7|7|8)\d{10}', phone):
                        self.current_number = phone
                        self.is_waiting_trigger = True
                        self.sent_to_chats.clear()
                        self.last_sent_info.clear()
                        await event.reply(f"✅ Номер {phone} установлен!\nЖду триггеры...")
                    else:
                        await event.reply("❌ Неверный формат номера")
                else:
                    await event.reply("❌ Используй: /номер 79001234567")
            
            elif text == '/testlink':
                # Тестовая команда для проверки ссылок
                if self.last_sent_info:
                    chat_id = self.last_sent_info.get('chat_id')
                    message_id = self.last_sent_info.get('message_id')
                    topic_id = self.last_sent_info.get('topic_id', 0)
                    
                    test_link = self.get_message_link(chat_id, message_id, topic_id)
                    await event.reply(f"🔗 Тестовая ссылка:\n{test_link}")
                else:
                    await event.reply("❌ Нет информации для теста")
            
            elif text == '/debug':
                debug_info = f"""🐛 DEBUG INFO:

ID бота: {self.me.id}
Текущий номер: {self.current_number or 'нет'}
Ожидает триггер: {self.is_waiting_trigger}
Отправлено в: {len(self.sent_to_chats)} топиков

📱 Последняя отправка:"""
                
                if self.last_sent_info:
                    for key, value in self.last_sent_info.items():
                        debug_info += f"\n  {key}: {value}"
                else:
                    debug_info += "\n  Нет информации"
                
                await event.reply(debug_info)
            
            elif text == '/help':
                help_text = """🤖 ТРИГГЕР БОТ СО ССЫЛКАМИ

📱 Как работает:
1. Кидаешь номер в избранное
2. Бот запоминает его
3. Ждет триггеры в группах
4. При триггере → отправляет номер В ТОТ ЖЕ ТОПИК
5. Отправляет тебе ССЫЛКУ на сообщение
6. Один номер = одна отправка

🎯 Команды:
/status - статус бота (со ссылкой)
/last - показать последнюю отправку
/reset - сбросить номер
/groups - список групп
/triggers - список триггеров
/testlink - проверить ссылку
/debug - отладочная информация
/номер 79001234567 - установить номер вручную
/help - эта справка

🔗 Формат ссылок:
Для топиков: https://t.me/c/3514324234/4/15382
Без топика: https://t.me/c/3514324234/15382"""
                await event.reply(help_text)

async def main():
    logger.info("Запуск бота...")
    
    bot = SimpleBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        if "auth key" in str(e).lower() or "session" in str(e).lower():
            logger.error("""
            ⚠️ ПРОБЛЕМА С СЕССИЕЙ!
            Решение:
            1. Убедись что файл session_bot.session есть в проекте
            2. Убедись что сессия актуальна (создана недавно)
            3. Если нужно - создай новую сессию локально и залей на GitHub
            """)
    finally:
        logger.info("Бот остановлен")

if __name__ == "__main__":
    # Проверяем файлы в директории
    logger.info("Содержимое директории:")
    for file in os.listdir('.'):
        logger.info(f"  {file}")
    
    # Запускаем бота
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Программа завершена")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        sys.exit(1)

