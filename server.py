from flask import Flask
import subprocess
import threading

app = Flask(__name__)

# Запускаем бота в фоне
def run_bot():
    subprocess.run(['python', '123.py'])

bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

@app.route('/')
def ping():
    return 'Bot is running'

@app.route('/health')
def health():
    return 'OK'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
