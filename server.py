from flask import Flask, render_template_string, jsonify
import threading
import asyncio
import sys
import os
import time
import subprocess
import signal

app = Flask(__name__)

# Переменные для управления ботом
bot_process = None
bot_running = False
log_buffer = []
server_start_time = time.strftime('%Y-%m-%d %H:%M:%S')

def log_message(message):
    """Добавляем сообщение в лог-буфер"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    # Держим только последние 50 сообщений
    if len(log_buffer) > 50:
        log_buffer.pop(0)
    log_buffer.append(log_entry)
    print(log_entry)

def run_bot_subprocess():
    """Запускает бота как отдельный процесс (самый надежный способ)"""
    global bot_process, bot_running
    
    try:
        log_message("🤖 Запускаю Telegram бота как отдельный процесс...")
        
        # Определяем файл с ботом
        bot_files = ['123.py', 'bot.py', 'telegram_bot.py', 'main.py']
        bot_file = None
        for file in bot_files:
            if os.path.exists(file):
                bot_file = file
                break
        
        if not bot_file:
            log_message("❌ Не найден файл с ботом!")
            return
        
        # Запускаем процесс
        bot_process = subprocess.Popen(
            [sys.executable, bot_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        bot_running = True
        log_message(f"✅ Бот запущен (PID: {bot_process.pid})")
        
        # Читаем вывод в реальном времени
        def read_output():
            while True:
                line = bot_process.stdout.readline()
                if not line:
                    break
                log_message(f"🤖 Бот: {line.strip()}")
        
        # Запускаем чтение в отдельном потоке
        output_thread = threading.Thread(target=read_output, daemon=True)
        output_thread.start()
        
        # Ждем завершения процесса
        bot_process.wait()
        
    except Exception as e:
        log_message(f"❌ Ошибка запуска бота: {e}")
    finally:
        bot_running = False
        bot_process = None
        log_message("⏹️ Бот остановлен")

def run_bot_threaded():
    """Альтернативный способ: запуск в отдельном потоке с asyncio"""
    global bot_running
    
    try:
        log_message("🤖 Запускаю Telegram бота в отдельном потоке...")
        
        # Импортируем бота динамически
        import importlib.util
        import sys
        
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
        
        # Получаем класс SimpleBot и функцию main
        SimpleBot = bot_module.SimpleBot
        
        # Функция для запуска в отдельном потоке
        def run_in_thread():
            try:
                # Создаем новый event loop для этого потока
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Запускаем бота
                bot = SimpleBot()
                loop.run_until_complete(bot.start())
                
            except Exception as e:
                log_message(f"❌ Ошибка в боте: {e}")
            finally:
                global bot_running
                bot_running = False
                log_message("⏹️ Бот остановлен")
        
        # Запускаем в отдельном потоке
        bot_running = True
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        log_message("✅ Бот запущен в отдельном потоке")
        
    except Exception as e:
        log_message(f"❌ Ошибка запуска бота: {e}")
        bot_running = False

def start_bot(method='subprocess'):
    """Запускает бота выбранным способом"""
    global bot_running
    
    if bot_running:
        log_message("⚠️ Бот уже запущен")
        return False
    
    if method == 'subprocess':
        # Запускаем в отдельном потоке, чтобы не блокировать Flask
        thread = threading.Thread(target=run_bot_subprocess, daemon=True)
        thread.start()
    else:
        run_bot_threaded()
    
    # Ждем немного чтобы убедиться что бот запустился
    time.sleep(3)
    return bot_running

def stop_bot():
    """Останавливает бота"""
    global bot_process, bot_running
    
    if not bot_running:
        return False
    
    log_message("🛑 Останавливаю бота...")
    
    if bot_process:
        try:
            # Отправляем сигнал завершения
            bot_process.terminate()
            # Ждем завершения
            bot_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            # Принудительно завершаем
            bot_process.kill()
            bot_process.wait()
        except Exception as e:
            log_message(f"⚠️ Ошибка при остановке: {e}")
    
    bot_running = False
    bot_process = None
    log_message("✅ Бот остановлен")
    return True

# HTML страница для мониторинга
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Telegram Bot Monitor</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        .status {
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            font-weight: bold;
        }
        .running {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .stopped {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .button {
            display: inline-block;
            padding: 10px 20px;
            margin: 10px 5px;
            background-color: #4CAF50;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            border: none;
            cursor: pointer;
            font-size: 16px;
        }
        .button:hover {
            background-color: #45a049;
        }
        .button.stop {
            background-color: #f44336;
        }
        .button.stop:hover {
            background-color: #d32f2f;
        }
        .info {
            background-color: #e7f3fe;
            border-left: 6px solid #2196F3;
            padding: 15px;
            margin: 20px 0;
        }
        .logs {
            background-color: #333;
            color: #fff;
            padding: 15px;
            border-radius: 5px;
            font-family: monospace;
            max-height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
            margin-top: 20px;
        }
        .method-selector {
            margin: 15px 0;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
        }
        .method-selector label {
            margin-right: 15px;
        }
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
        
        <div class="method-selector">
            <strong>Способ запуска:</strong>
            <label>
                <input type="radio" name="method" value="subprocess" checked onclick="setMethod('subprocess')">
                Subprocess (рекомендуется)
            </label>
            <label>
                <input type="radio" name="method" value="threaded" onclick="setMethod('threaded')">
                Threaded
            </label>
        </div>
        
        <div>
            {% if status == 'running' %}
                <a href="/stop" class="button stop">Остановить бота</a>
            {% else %}
                <a href="/start/subprocess" class="button" id="startBtn">Запустить бота</a>
            {% endif %}
            <a href="/health" class="button">Проверить здоровье</a>
            <a href="/restart" class="button">Перезапустить</a>
            <a href="/logs" class="button">Показать логи</a>
        </div>
        
        <h3>Последние логи:</h3>
        <div class="logs" id="logContainer">
            {{ logs }}
        </div>
        
        <div style="margin-top: 30px; font-size: 12px; color: #666;">
            <p>Сервер запущен: {{ start_time }}</p>
            <p>Версия Python: {{ python_version }}</p>
            <p>Порт: {{ port }}</p>
            <p>PID: {{ pid }}</p>
        </div>
    </div>
    
    <script>
        let selectedMethod = 'subprocess';
        
        function setMethod(method) {
            selectedMethod = method;
            const startBtn = document.getElementById('startBtn');
            startBtn.href = '/start/' + method;
        }
        
        // Авто-обновление страницы каждые 30 секунд
        setTimeout(function() {
            window.location.reload();
        }, 30000);
        
        // Авто-обновление логов каждые 5 секунд
        function updateLogs() {
            fetch('/logs/raw')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('logContainer').textContent = data.logs;
                })
                .catch(error => console.error('Error updating logs:', error));
        }
        
        // Обновляем логи каждые 5 секунд если бот запущен
        {% if status == 'running' %}
        setInterval(updateLogs, 5000);
        {% endif %}
        
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

# Маршруты Flask
@app.route('/')
def index():
    """Главная страница"""
    logs_text = '\n'.join(log_buffer[-20:]) if log_buffer else "Логи пока отсутствуют..."
    
    return render_template_string(HTML_TEMPLATE,
        status='running' if bot_running else 'stopped',
        logs=logs_text,
        start_time=server_start_time,
        python_version=sys.version.split()[0],
        port=os.environ.get('PORT', 10000),
        pid=os.getpid()
    )

@app.route('/start/<method>')
def start(method):
    """Запуск бота выбранным способом"""
    if start_bot(method):
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

@app.route('/start')
def start_default():
    """Запуск бота по умолчанию"""
    return start('subprocess')

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
    start_bot('subprocess')
    return '''
    <script>
        alert("Бот перезапускается...");
        window.location.href = "/";
    </script>
    '''

@app.route('/health')
def health():
    """Проверка здоровья сервера"""
    return jsonify({
        'status': 'healthy' if bot_running else 'degraded',
        'bot_running': bot_running,
        'server_time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'uptime': time.time() - os.path.getctime(__file__),
        'log_count': len(log_buffer),
        'pid': os.getpid()
    })

@app.route('/logs')
def show_logs():
    """Страница с логами"""
    logs_text = '\n'.join(log_buffer) if log_buffer else "Логи отсутствуют"
    return f"<pre style='background:#333;color:#fff;padding:20px;'>{logs_text}</pre>"

@app.route('/logs/raw')
def get_logs_raw():
    """Получить логи в JSON формате"""
    logs_text = '\n'.join(log_buffer[-50:]) if log_buffer else "Логи отсутствуют"
    return jsonify({'logs': logs_text})

@app.route('/ping')
def ping():
    """Простая проверка работы сервера"""
    return 'pong'

# Запускаем бота автоматически при старте сервера
@app.before_request
def initialize():
    """Инициализация при первом запросе"""
    if not hasattr(app, 'bot_initialized'):
        app.bot_initialized = True
        log_message(f"🚀 Сервер запущен на порту {os.environ.get('PORT', 10000)}")
        log_message(f"📁 Рабочая директория: {os.getcwd()}")
        log_message(f"📄 Файлы в директории: {', '.join(os.listdir('.'))}")
        
        # Автоматически запускаем бота при старте
        log_message("⏳ Автоматический запуск бота...")
        start_bot('subprocess')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    log_message(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
