from flask import Flask
import threading
import asyncio
import sys
import os

app = Flask(__name__)

# Импортируем и запускаем бота в отдельном потоке
def start_bot():
    try:
        from main import run_bot
        asyncio.run(run_bot())
    except Exception as e:
        print(f"Бот упал: {e}", file=sys.stderr)
        sys.exit(1)  # Завершаем процесс для перезапуска Render

# Запускаем бот в фоновом потоке при старте Flask
@app.before_first_request
def launch_bot():
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    print("Фоновый поток бота запущен")

@app.route('/')
def home():
    return 'Bot is running'

@app.route('/health')
def health():
    return 'OK', 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
