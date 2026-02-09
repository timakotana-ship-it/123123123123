from flask import Flask, render_template_string
import threading
import asyncio
import sys
import os
import time

app = Flask(__name__)

# Переменные для управления ботом
bot_thread = None
bot_running = False
bot_instance = None

# HTML страница для мониторинга (оставляем тот же HTML_TEMPLATE)

def log_message(message):
    """Добавляем сообщение в лог-буфер"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    # Держим только последние 50 сообщений
    if len(log_buffer) > 50:
        log_buffer.pop(0)
    log_buffer.append(log_entry)
    print(log_entry)

# Используем global для log_buffer
log_buffer = []

def run_bot():
    """Функция для запуска бота в отдельном потоке"""
    global bot_running, bot_instance, log_buffer
    
    try:
        log_message("🤖 Запускаю Telegram бота...")
        
        # Импортируем здесь, чтобы избежать циклических импортов
        try:
            # Пытаемся импортировать из текущего файла
            from __main__ import SimpleBot
        except ImportError:
            # Если не работает, создаем модуль динамически
            import importlib.util
            import sys
            
            # Ищем файл с ботом
            bot_files = ['123.py', 'bot.py', 'telegram_bot.py', 'main.py']
            bot_file = None
            for file in bot_files:
                if os.path.exists(file):
                    bot_file = file
                    break
            
            if not bot_file:
                log_message("❌ Не найден файл с ботом!")
                return
            
            # Динамически импортируем модуль
            spec = importlib.util.spec_from_file_location("bot_module", bot_file)
            bot_module = importlib.util.module_from_spec(spec)
            sys.modules["bot_module"] = bot_module
            spec.loader.exec_module(bot_module)
            SimpleBot = bot_module.SimpleBot
        
        # Создаем экземпляр бота
        bot_instance = SimpleBot()
        
        # НОВЫЙ СПОСОБ: Запускаем asyncio в этом потоке
        async def start_bot_async():
            try:
                await bot_instance.start()
            except Exception as e:
                log_message(f"❌ Ошибка в боте: {e}")
            finally:
                global bot_running
                bot_running = False
                log_message("⏹️ Бот остановлен")
        
        # Запускаем asyncio
        bot_running = True
        log_message("✅ Бот запущен успешно")
        
        # Создаем новый event loop для этого потока
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Запускаем бота
        loop.run_until_complete(start_bot_async())
        
    except Exception as e:
        log_message(f"❌ Ошибка запуска бота: {e}")
        bot_running = False

def start_bot_thread():
    """Запускает бота в отдельном потоке"""
    global bot_thread, bot_running
    
    if bot_running:
        log_message("⚠️ Бот уже запущен")
        return False
    
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Ждем немного чтобы убедиться что поток запустился
    time.sleep(2)
    return bot_running

def stop_bot():
    """Останавливает бота"""
    global bot_running, bot_instance
    
    if not bot_running or not bot_instance:
        return False
    
    log_message("🛑 Останавливаю бота...")
    bot_running = False
    
    # Останавливаем клиента Telegram
    try:
        # Нужно вызвать disconnect() у клиента
        # Это нужно сделать в том же потоке, так что просто меняем флаг
        # Бот сам остановится при следующей проверке
        pass
    except:
        pass
    
    return True

# Маршруты Flask (оставляем те же)

@app.route('/')
def index():
    """Главная страница"""
    logs_text = '\n'.join(log_buffer[-20:]) if log_buffer else "Логи пока отсутствуют..."
    
    # HTML_TEMPLATE остается таким же
    HTML_TEMPLATE = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Telegram Bot Monitor</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f5f5f5; }
            .container { background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }
            .status { padding: 15px; border-radius: 5px; margin: 20px 0; font-weight: bold; }
            .running { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .stopped { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .button { display: inline-block; padding: 10px 20px; margin: 10px 5px; background-color: #4CAF50; color: white; 
                     text-decoration: none; border-radius: 5px; border: none; cursor: pointer; font-size: 16px; }
            .button:hover { background-color: #45a049; }
            .button.stop { background-color: #f44336; }
            .button.stop:hover { background-color: #d32f2f; }
            .info { background-color: #e7f3fe; border-left: 6px solid #2196F3; padding: 15px; margin: 20px 0; }
            .logs { background-color: #333; color: #fff; padding: 15px; border-radius: 5px; font-family: monospace; 
                   max-height: 300px; overflow-y: auto; white-space: pre-wrap; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Telegram Trigger Bot Monitor</h1>
            
            <div class="info">
                <h3>Информация:</h3>
                <p>Этот сервер запускает и мониторит Telegram бота.</p>
                <p>Бот слушает триггеры в группах и автоматически отправляет номера.</p>
            </div>
            
            <div class="status {{ 'running' if status == 'running' else 'stopped' }}">
                Статус: {{ status.upper() }}
            </div>
            
            <div>
                {% if status == 'running' %}
                    <a href="/stop" class="button stop">Остановить бота</a>
                {% else %}
                    <a href="/start" class="button">Запустить бота</a>
                {% endif %}
                <a href="/health" class="button">Проверить здоровье</a>
                <a href="/restart" class="button">Перезапустить</a>
            </div>
            
            <h3>Последние логи:</h3>
            <div class="logs">
                {{ logs }}
            </div>
            
            <div style="margin-top: 30px; font-size: 12px; color: #666;">
                <p>Сервер запущен: {{ start_time }}</p>
                <p>Версия Python: {{ python_version }}</p>
                <p>Порт: {{ port }}</p>
            </div>
        </div>
        
        <script>
            // Авто-обновление страницы каждые 30 секунд
            setTimeout(function() {
                window.location.reload();
            }, 30000);
            
            // Обработка кнопок
            document.querySelectorAll('.button').forEach(button => {
                button.addEventListener('click', function(e) {
                    if (this.textContent.includes('Остановить') || this.textContent.includes('Запустить')) {
                        this.textContent = 'Обработка...';
                        this.style.opacity = '0.7';
                    }
                });
            });
        </script>
    </body>
    </html>
    """
    
    return render_template_string(HTML_TEMPLATE,
        status='running' if bot_running else 'stopped',
        logs=logs_text,
        start_time=time.strftime('%Y-%m-%d %H:%M:%S'),
        python_version=sys.version.split()[0],
        port=os.environ.get('PORT', 10000)
    )

@app.route('/start')
def start():
    """Запуск бота"""
    if start_bot_thread():
        return '''
        <script>
            alert("Бот запускается...");
            window.location.href = "/";
        </script>
        '''
    else:
        return '''
        <script>
            alert("Бот уже запущен или ошибка запуска");
            window.location.href = "/";
        </script>
        '''

@app.route('/stop')
def stop():
    """Остановка бота"""
    if stop_bot():
        return '''
        <script>
            alert("Бот останавливается...");
            window.location.href = "/";
        </script>
        '''
    else:
        return '''
        <script>
            alert("Бот не был запущен");
            window.location.href = "/";
        </script>
        '''

@app.route('/restart')
def restart():
    """Перезапуск бота"""
    stop_bot()
    time.sleep(3)
    start_bot_thread()
    return '''
    <script>
        alert("Бот перезапускается...");
        window.location.href = "/";
    </script>
    '''

@app.route('/health')
def health():
    """Проверка здоровья сервера"""
    return {
        'status': 'healthy' if bot_running else 'degraded',
        'bot_running': bot_running,
        'server_time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'log_count': len(log_buffer)
    }

@app.route('/ping')
def ping():
    """Простая проверка работы сервера"""
    return 'pong'

# Запускаем бота автоматически при старте сервера
@app.before_request
def initialize():
    """Инициализация при первом запросе"""
    global bot_thread
    
    if not hasattr(app, 'bot_initialized'):
        app.bot_initialized = True
        log_message(f"🚀 Сервер запущен на порту {os.environ.get('PORT', 10000)}")
        
        # Автоматически запускаем бота при старте
        log_message("⏳ Автоматический запуск бота...")
        start_bot_thread()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    log_message(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
