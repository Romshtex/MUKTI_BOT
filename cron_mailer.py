import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date
import json
import time
import hashlib
import hmac

# Импортируем нашу готовую базу
import database as db

# --- НАСТРОЙКИ ---
YANDEX_EMAIL = st.secrets.get("YANDEX_EMAIL", "")
YANDEX_PASSWORD = st.secrets.get("YANDEX_PASSWORD", "")
SECRET_KEY = st.secrets.get("SECRET_KEY", "mukti_super_secret_matrix_key_2026")
ADMIN_EMAILS = st.secrets.get("ADMIN_EMAILS", ["mukti.system@yandex.com"])

def get_unsubscribe_token(email):
    return hmac.new(SECRET_KEY.encode(), email.encode(), hashlib.sha256).hexdigest()

def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = YANDEX_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP_SSL('smtp.yandex.ru', 465)
        server.login(YANDEX_EMAIL, YANDEX_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Ошибка отправки на {to_email}: {e}")
        return False

def run_auto_mailer():
    print(f"[{datetime.now()}] ЗАПУСК АВТОМАТИЧЕСКОГО ПРОТОКОЛА РАССЫЛКИ...")
    all_users = db.get_all_users()
    if not all_users:
        print("База пуста. Отбой.")
        return

    today_date = date.today()
    sent_count = 0

    for u in all_users:
        r_num, u_email, u_name, p_json = u
        
        # Пропускаем админов
        if u_email in ADMIN_EMAILS or u_email == YANDEX_EMAIL: 
            continue
        
        try: prof = json.loads(p_json) if p_json else {}
        except: prof = {}
        
        if prof.get("unsubscribed") == True: 
            continue
            
        last_active_str = prof.get("last_active") or prof.get("last_msg_date")
        if not last_active_str: 
            continue
        
        try: last_active_date = datetime.strptime(last_active_str, "%Y-%m-%d").date()
        except: continue
        
        days_inactive = (today_date - last_active_date).days
        reminders_sent = prof.get("reminders_sent", [])
        
        subj = ""
        body = ""
        rem_type = 0
        
        unsub_token = get_unsubscribe_token(u_email)
        unsub_url = f"https://mukti-app.streamlit.app/?unsubscribe={u_email}&token={unsub_token}"
        
        if days_inactive >= 14 and 14 not in reminders_sent:
            rem_type = 14
            subj = "Перевод профиля в спящий режим"
            body = f"Привет, {u_name}. Две недели без связи.\n\nЯ понимаю, что не каждый готов выйти из Матрицы с первой попытки. Иногда нужно время, чтобы устать от старого сценария настолько, чтобы захотеть реальных перемен. И это нормально - это твой путь.\n\nСегодня я перевожу твой профиль в спящий режим. Я больше не буду присылать тебе системные уведомления.\n\nНо помни одно: твое место в терминале навсегда закреплено за тобой. Если через месяц или через год ты проснешься с мыслью, что пора окончательно удалить вредоносный код из своей жизни - просто перейди по ссылке, введи свой пароль, и Наставник продолжит работу с того же места.\n\nДо связи. Архитектор.\nhttps://mukti-app.streamlit.app/\n\n---\nОтключить напоминания от Архитектора: {unsub_url}"
        
        elif days_inactive >= 7 and 7 not in reminders_sent and 14 not in reminders_sent:
            rem_type = 7
            subj = "Кто сейчас управляет твоим временем?"
            body = f"Привет, {u_name}. Прошла ровно неделя тишины.\n\nЕсли ты сейчас справляешься сам и Гость молчит - я искренне рад. Но чаще всего недельная пауза означает другое: старые привычки пытаются вернуть себе контроль.\n\nЕсли произошел срыв - не вини себя. Чувство вины - это любимое топливо зависимости. Система МУКТИ создана не для того, чтобы тебя ругать, а для того, чтобы хладнокровно разобрать ошибку в коде и сделать тебя сильнее.\n\nНе нужно начинать всё сначала. Просто вернись в чат и честно скажи Наставнику, что произошло. Мы просто обнулим этот сбой и пойдем дальше.\n\nТерминал открыт: https://mukti-app.streamlit.app/\n\n---\nОтключить напоминания от Архитектора: {unsub_url}"
        
        elif days_inactive >= 3 and 3 not in reminders_sent and 7 not in reminders_sent and 14 not in reminders_sent:
            rem_type = 3
            subj = "Терминал МУКТИ ожидает отклика..."
            body = f"Приветствую, {u_name}. На связи Архитектор.\n\nЯ заметил, что ты не заходил в терминал МУКТИ уже 3 дня. Всё в порядке?\n\nЗнаешь, на старте это абсолютно нормальная реакция. Когда мы начинаем переписывать нейронные связи, старая программа («Гость») чувствует угрозу и начинает саботировать процесс. Она шепчет: «Давай потом», «У тебя нет времени», «Это всё ерунда».\n\nНе поддавайся. Тебе не обязательно писать длинные тексты. Просто зайди в систему прямо сейчас и напиши Наставнику одну фразу: как прошел твой сегодняшний день.\n\nТвой прогресс сохранен. Жду тебя внутри: https://mukti-app.streamlit.app/\n\n---\nОтключить напоминания от Архитектора: {unsub_url}"
        
        if rem_type > 0:
            if send_email(u_email, subj, body):
                reminders_sent.append(rem_type)
                # Пакетное обновление профиля, чтобы зафиксировать отправку
                db.update_profile_batch(r_num, {"reminders_sent": reminders_sent})
                sent_count += 1
                print(f"Письмо (День {rem_type}) отправлено для {u_email}")
                time.sleep(2) # Пауза, чтобы Яндекс не счел нас за спамеров
                
    print(f"[{datetime.now()}] РАССЫЛКА ЗАВЕРШЕНА. Отправлено писем: {sent_count}")

if __name__ == "__main__":
    run_auto_mailer()
