import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date
import toml
import os
import database as db

# ---------------------------------------------------------------------------
# ПРЯМОЕ ЧТЕНИЕ СЕКРЕТОВ МАТРИЦЫ
# ---------------------------------------------------------------------------
# Путь строится относительно самого файла — работает из любой директории
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_SECRETS_PATH = os.path.join(_BASE_DIR, ".streamlit", "secrets.toml")

try:
    with open(_SECRETS_PATH, "r", encoding="utf-8") as f:
        secrets = toml.load(f)
except FileNotFoundError:
    print(f"Критическая ошибка: файл secrets.toml не найден по пути {_SECRETS_PATH}")
    exit(1)

YANDEX_EMAIL = secrets.get("YANDEX_EMAIL")
YANDEX_PASSWORD = secrets.get("YANDEX_PASSWORD")

if not YANDEX_EMAIL or not YANDEX_PASSWORD:
    print("Критическая ошибка: Учетные данные Яндекса отсутствуют в секретах.")
    exit(1)

# ---------------------------------------------------------------------------
# SMTP КЛИЕНТ
# ---------------------------------------------------------------------------
def send_email(to_email, subject, body):
    msg = MIMEMultipart()
    msg['From'] = YANDEX_EMAIL
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))
    
    try:
        server = smtplib.SMTP_SSL('smtp.yandex.ru', 465)
        server.login(YANDEX_EMAIL, YANDEX_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Ошибка отправки на {to_email}: {e}")
        return False

# ---------------------------------------------------------------------------
# ЯДРО РАССЫЛКИ
# ---------------------------------------------------------------------------
def run_daily_mailing():
    users = db.get_all_users()
    today_str = str(date.today())
    count = 0
    
    for u in users:
        r_num, u_email, u_name, p_json = u
        # Email не передаётся в URL — только непрозрачный токен
        unsub_link = f"https://mukti.pro/?unsubscribe_token={db.make_unsub_token(u_email)}"
        
        subject = f"Твоя практика МУКТИ, {u_name}"
        body = f"""
        <html>
        <body>
            <p>Привет, {u_name}!</p>
            <p>Возвращайся к практике. Матрица ждет.</p>
            <br>
            <a href="https://mukti.pro">Войти в систему</a>
            <br><br><br>
            <small><a href="{unsub_link}">Отписаться от рассылки</a></small>
        </body>
        </html>
        """
        if send_email(u_email, subject, body):
            count += 1
            
    print(f"[{today_str}] Рассылка завершена. Отправлено: {count} писем.")

if __name__ == "__main__":
    run_daily_mailing()
