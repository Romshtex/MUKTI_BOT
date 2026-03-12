import streamlit as st
import google.generativeai as genai
from datetime import datetime, timedelta, date
import time
import json
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import extra_streamlit_components as stx  
import pandas as pd

# ИМПОРТ МОДУЛЕЙ
import settings
import database as db
import messages as msg_module

# --- НАСТРОЙКИ ---
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"] if "GOOGLE_API_KEY" in st.secrets else "NO_KEY"
YANDEX_EMAIL = st.secrets.get("YANDEX_EMAIL", "mukti.system@yandex.com")
YANDEX_PASSWORD = st.secrets.get("YANDEX_PASSWORD", "")

genai.configure(api_key=GOOGLE_API_KEY)

try:
    from book import BOOK_SUMMARY
except ImportError:
    BOOK_SUMMARY = "Методика освобождения."

# --- КАСТОМНЫЕ ВЕКТОРНЫЕ АВАТАРЫ (SVG) ---
USER_AVATAR = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%232196F3' d='M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z'/%3E%3C/svg%3E"
BOT_AVATAR = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%2300E676' d='M20 9V7c0-1.1-.9-2-2-2h-3c0-1.66-1.34-3-3-3S9 3.34 9 5H6c-1.1 0-2 .9-2 2v2c-1.66 0-3 1.34-3 3s1.34 3 3 3v4c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2v-4c1.66 0 3-1.34 3-3s-1.34-3-3-3zm-6 0h2v2h-2V9zm-6 0h2v2H8V9z'/%3E%3C/svg%3E"

# --- CSS: МАТРИЦА С ТОНИРОВКОЙ ---
st.markdown("""
<style>
    .stApp > header { 
        background-color: rgba(20, 20, 20, 0.95) !important; 
        border-bottom: 1px solid rgba(0, 230, 118, 0.3) !important;
    }
    .stApp > header * {
        color: #00E676 !important;
        fill: #00E676 !important;
    }
    .main {
        background-color: rgba(14, 17, 23, 0.85) !important; 
        border-radius: 15px;
    }
    p, div, span, h1, h2, h3, h4, h5, h6, label, li {
        color: #FAFAFA !important;
    }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: rgba(30, 30, 30, 0.9) !important;
        color: #00E676 !important;
        border: 1px solid #333 !important;
    }
    .stChatMessage {
        background-color: rgba(30, 30, 30, 0.8) !important;
        color: #FAFAFA !important;
        border: 1px solid rgba(0, 230, 118, 0.2) !important;
    }
    h1, h2, h3 { color: #00E676 !important; }
    div[data-testid="stMetricValue"] { color: #00E676 !important; }
    
    /* Стили для выпадающего меню (expander) */
    [data-testid="stExpander"] {
        border-color: #00E676 !important;
        background-color: rgba(20, 20, 20, 0.8) !important;
        border-radius: 10px !important;
    }
    [data-testid="stExpander"] summary {
        color: #00E676 !important;
    }
    [data-testid="stExpander"] summary svg {
        fill: #00E676 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- ИНИЦИАЛИЗАЦИЯ COOKIES ---
cookie_manager = stx.CookieManager(key="mukti_cookies")

# --- ПЕРЕХВАТЧИК ОТПИСКИ ОТ РАССЫЛКИ ---
if "unsubscribe" in st.query_params:
    unsub_email = st.query_params["unsubscribe"]
    row_data, r_num = db.load_user(unsub_email)
    if row_data:
        try:
            profile = json.loads(row_data[5]) if len(row_data)>5 else {}
        except:
            profile = {}
        profile["unsubscribed"] = True
        db.update_field(r_num, 5, json.dumps(profile))
        st.success(f"Связь прервана. Напоминания для {unsub_email} навсегда отключены.")
        st.query_params.clear()

# --- МОДЕЛЬ ---
@st.cache_resource
def get_model():
    try:
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority = ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']
        for p in priority:
            if p in available: return genai.GenerativeModel(p)
        return genai.GenerativeModel(available[0]) if available else None
    except: return None

model = get_model()
settings.load_css() 

# --- СОСТОЯНИЕ ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "calibration_step" not in st.session_state: st.session_state.calibration_step = 0
if "reading_message" not in st.session_state: st.session_state.reading_message = False
if "current_view" not in st.session_state: st.session_state.current_view = "chat"

# --- ФУНКЦИИ ---
def send_email(to_email, subject, body):
    if not YANDEX_EMAIL or not YANDEX_PASSWORD:
        return "ОШИБКА: Файл secrets.toml не видит ключи Яндекс."
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
        return "OK"
    except Exception as e: 
        return f"ОТКАЗ ЯНДЕКСА: {str(e)}"

def get_mukti_date():
    now = datetime.now()
    if now.hour < 3:
        return str((now - timedelta(days=1)).date())
    return str(now.date())

def load_user_to_session(email):
    row_data, r_num = db.load_user(email)
    if row_data:
        st.session_state.logged_in = True
        st.session_state.user_email = email
        st.session_state.username = row_data[1] 
        st.session_state.row_num = r_num
        
        try: st.session_state.user_profile = json.loads(row_data[5]) if len(row_data)>5 else {}
        except: st.session_state.user_profile = {}
        
        is_vip_db = (len(row_data) > 7 and row_data[7] == "TRUE")
        is_vip_json = st.session_state.user_profile.get("is_vip", False)
        st.session_state.is_vip = is_vip_db or is_vip_json
        
        try: st.session_state.messages = json.loads(row_data[6]) if len(row_data)>6 else []
        except: st.session_state.messages = []
        
        if email == "mukti.system@yandex.com":
            st.session_state.current_view = "admin"
            st.session_state.reading_message = False
            return True

        st.session_state.user_profile["last_active"] = str(date.today())
        db.update_profile(st.session_state.row_num, "last_active", str(date.today()))
        
        if not st.session_state.messages:
            st.session_state.calibration_step = 1
            welcome = f"Приветствую, {st.session_state.username}. Я — твой ИИ-наставник МУКТИ. Вижу, ты здесь впервые.\n\nДля настройки алгоритмов защиты мне нужно откалибровать твои параметры. Ответь прямо в этот чат: **ты уже читал книгу «Кто такой Алкоголь»?**"
            st.session_state.messages = [{"role": "assistant", "content": welcome}]
            db.save_history(st.session_state.row_num, st.session_state.messages)
            
        current_date = get_mukti_date()
        last_msg_date = st.session_state.user_profile.get("last_msg_date", "")
        msg_day = int(st.session_state.user_profile.get("msg_day", 0))
        
        if last_msg_date != current_date and msg_day < 61 and st.session_state.calibration_step == 0:
            st.session_state.reading_message = True
            
        st.session_state.current_view = "chat"
        return True
    return False

# ==========================================
# АВТОЛОГИН ЧЕРЕЗ COOKIES
# ==========================================
if not st.session_state.logged_in:
    saved_cookie = cookie_manager.get(cookie="mukti_user")
    if saved_cookie:
        if load_user_to_session(saved_cookie):
            st.rerun()

# ==========================================
# АВТОРИЗАЦИЯ И РЕГИСТРАЦИЯ
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: #00E676;'>МУКТИ</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #A0A0A0;'>Система выхода из матрицы алкогольной зависимости</p>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["ВХОД", "РЕГИСТРАЦИЯ", "ЗАБЫЛ ПАРОЛЬ"])
    
    with tab1:
        with st.form("login_form"):
            email_in = st.text_input("Email").strip().lower()
            pwd_in = st.text_input("Пароль", type="password").strip()
            if st.form_submit_button("ВОЙТИ"):
                if email_in and pwd_in:
                    row_data, r_num = db.load_user(email_in)
                    if row_data and row_data[2] == pwd_in:
                        cookie_manager.set("mukti_user", email_in, expires_at=datetime.now() + timedelta(days=30))
                        load_user_to_session(email_in)
                        time.sleep(0.5) 
                        st.rerun()
                    else: st.error("Ошибка доступа. Неверный Email или Пароль.")
                else: st.warning("Введи данные.")

    with tab2:
        with st.form("reg_form"):
            new_email = st.text_input("Email (Твой ID в системе)").strip().lower()
            new_user = st.text_input("Придумай Имя Аватара").strip()
            new_pwd = st.text_input("Придумай Пароль", type="password").strip()
            
            if st.form_submit_button("СОЗДАТЬ ПРОФИЛЬ"):
                if not new_email or "@" not in new_email:
                    st.error("Введи корректный Email.")
                elif len(new_pwd) < 4:
                    st.error("Пароль должен быть не короче 4 символов.")
                elif new_user:
                    res = db.register_user(new_email, new_user, new_pwd)
                    if res == "OK":
                        cookie_manager.set("mukti_user", new_email, expires_at=datetime.now() + timedelta(days=30))
                        load_user_to_session(new_email)
                        time.sleep(0.5)
                        st.rerun()
                    elif res == "TAKEN": st.error("Этот Email уже зарегистрирован.")
                    else: st.error("Ошибка БД.")
                else: st.warning("Заполни все поля.")

    with tab3:
        st.markdown("Забыл пароль? Мы пришлем его на твою почту.")
        with st.form("recovery_form"):
            rec_email = st.text_input("Введи свой Email").strip().lower()
            if st.form_submit_button("ВОССТАНОВИТЬ"):
                if rec_email:
                    row_data, _ = db.load_user(rec_email)
                    if row_data:
                        pwd = row_data[2]
                        subject = "МУКТИ: Доступ к системе"
                        body = f"Приветствую, {row_data[1]}.\n\nТвой пароль для доступа в систему: {pwd}\n\nНе теряй его.\nАрхитектор."
                        res = send_email(rec_email, subject, body)
                        if res == "OK": st.success("Письмо с паролем отправлено! Проверь почту (и папку Спам).")
                        else: st.error(f"Сбой отправки: {res}")
                    else: st.error("Аватар с таким Email не найден.")
                    
    # ЮРИДИЧЕСКИЕ ССЫЛКИ
    st.markdown("<p style='text-align: center; font-size: 13px; color: #888; margin-top: 15px;'>Продолжая, ты соглашаешься с <br><a href='https://disk.yandex.ru/i/dWaWRwOfdVFtFQ' target='_blank' style='color: #00E676; text-decoration: none;'>Политикой конфиденциальности</a> и <a href='https://disk.yandex.ru/i/RBnom-qhT8KVhA' target='_blank' style='color: #00E676; text-decoration: none;'>Публичной офертой</a>.</p>", unsafe_allow_html=True)

# ==========================================
# ПАНЕЛЬ АРХИТЕКТОРА (ЭКСКЛЮЗИВ ДЛЯ АДМИНА)
# ==========================================
elif st.session_state.user_email == "mukti.system@yandex.com":
    st.markdown("<h2 style='text-align: center; color: #00E676;'>🛠 СЕКРЕТНЫЙ ТЕРМИНАЛ АРХИТЕКТОРА</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    all_users = db.get_all_users()
    
    total_users = 0
    vip_users = 0
    active_3_days = 0
    table_data = []
    
    today_date = date.today()
    
    for u in all_users:
        r_num, u_email, u_name, p_json = u
        if u_email == "mukti.system@yandex.com" or u_email == YANDEX_EMAIL: continue 
        
        total_users += 1
        try: prof = json.loads(p_json) if p_json else {}
        except: prof = {}
        
        is_vip = prof.get("is_vip", False)
        row_full, _ = db.load_user(u_email)
        if row_full and len(row_full) > 7 and row_full[7] == "TRUE":
            is_vip = True
            
        if is_vip: vip_users += 1
            
        last_active_str = prof.get("last_active") or prof.get("last_msg_date")
        days_inactive = 999
        if last_active_str:
            try:
                last_active_date = datetime.strptime(last_active_str, "%Y-%m-%d").date()
                days_inactive = (today_date - last_active_date).days
                if days_inactive <= 3: active_3_days += 1
            except: pass
            
        msg_day = prof.get("msg_day", 0)
        
        table_data.append({
            "Email": u_email,
            "Имя": u_name,
            "День": msg_day,
            "VIP": "Да" if is_vip else "Нет",
            "Был в сети": last_active_str if last_active_str else "Никогда",
            "Отписан": "Да" if prof.get("unsubscribed") else "Нет"
        })
        
    col1, col2, col3 = st.columns(3)
    col1.metric("Всего Аватаров", total_users)
    col2.metric("VIP Пользователи", vip_users)
    col3.metric("Активны (3 дня)", active_3_days)
    
    st.markdown("---")
    
    col_vip, col_mail = st.columns(2)
    
    with col_vip:
        st.markdown("### 👑 Выдача VIP-доступа")
        with st.form("vip_form"):
            target_email = st.text_input("Введи Email для активации VIP").strip().lower()
            if st.form_submit_button("АКТИВИРОВАТЬ VIP"):
                row, r_num = db.load_user(target_email)
                if row:
                    try:
                        db.update_field(r_num, 7, "TRUE")
                        prof = json.loads(row[5]) if len(row)>5 and row[5] else {}
                        prof["is_vip"] = True
                        db.update_field(r_num, 5, json.dumps(prof))
                        st.success(f"Доступ VIP активирован для {target_email}!")
                    except Exception as e:
                        st.error(f"Ошибка БД: {e}")
                else:
                    st.error("Аватар с таким Email не найден.")

    with col_mail:
        st.markdown("### 🚀 Протокол рассылки")
        st.markdown("Автоматическая проверка базы и отправка писем (3, 7, 14 дней).")
        if st.button("ЗАПУСТИТЬ РАССЫЛКУ", type="primary", use_container_width=True):
            with st.spinner("Сбор данных и отправка писем..."):
                sent_count = 0
                for u in all_users:
                    r_num, u_email, u_name, p_json = u
                    if u_email == "mukti.system@yandex.com" or u_email == YANDEX_EMAIL: continue
                    
                    try: prof = json.loads(p_json) if p_json else {}
                    except: prof = {}
                    
                    if prof.get("unsubscribed") == True: continue
                        
                    last_active_str = prof.get("last_active") or prof.get("last_msg_date")
                    if not last_active_str: continue
                    
                    try: last_active_date = datetime.strptime(last_active_str, "%Y-%m-%d").date()
                    except: continue
                    
                    days_inactive = (today_date - last_active_date).days
                    reminders_sent = prof.get("reminders_sent", [])
                    
                    subj = ""
                    body = ""
                    rem_type = 0
                    
                    if days_inactive >= 14 and 14 not in reminders_sent:
                        rem_type = 14
                        subj = "Перевод профиля в спящий режим"
                        body = f"Привет, {u_name}. Две недели без связи.\n\nЯ понимаю, что не каждый готов выйти из Матрицы с первой попытки. Иногда нужно время, чтобы устать от старого сценария настолько, чтобы захотеть реальных перемен. И это нормально - это твой путь.\n\nСегодня я перевожу твой профиль в спящий режим. Я больше не буду присылать тебе системные уведомления.\n\nНо помни одно: твое место в терминале навсегда закреплено за тобой. Если через месяц или через год ты проснешься с мыслью, что пора окончательно удалить вредоносный код из своей жизни - просто перейди по ссылке, введи свой пароль, и Наставник продолжит работу с того же места.\n\nДо связи. Архитектор.\nhttps://mukti-app.streamlit.app/\n\n---\nОтключить напоминания от Архитектора: https://mukti-app.streamlit.app/?unsubscribe={u_email}"
                    
                    elif days_inactive >= 7 and 7 not in reminders_sent and 14 not in reminders_sent:
                        rem_type = 7
                        subj = "Кто сейчас управляет твоим временем?"
                        body = f"Привет, {u_name}. Прошла ровно неделя тишины.\n\nЕсли ты сейчас справляешься сам и Гость молчит - я искренне рад. Но чаще всего недельная пауза означает другое: старые привычки пытаются вернуть себе контроль.\n\nЕсли произошел срыв - не вини себя. Чувство вины - это любимое топливо зависимости. Система МУКТИ создана не для того, чтобы тебя ругать, а для того, чтобы хладнокровно разобрать ошибку в коде и сделать тебя сильнее.\n\nНе нужно начинать всё сначала. Просто вернись в чат и честно скажи Наставнику, что произошло. Мы просто обнулим этот сбой и пойдем дальше.\n\nТерминал открыт: https://mukti-app.streamlit.app/\n\n---\nОтключить напоминания от Архитектора: https://mukti-app.streamlit.app/?unsubscribe={u_email}"
                    
                    elif days_inactive >= 3 and 3 not in reminders_sent and 7 not in reminders_sent and 14 not in reminders_sent:
                        rem_type = 3
                        subj = "Терминал МУКТИ ожидает отклика..."
                        body = f"Приветствую, {u_name}. На связи Архитектор.\n\nЯ заметил, что ты не заходил в терминал МУКТИ уже 3 дня. Всё в порядке?\n\nЗнаешь, на старте это абсолютно нормальная реакция. Когда мы начинаем переписывать нейронные связи, старая программа («Гость») чувствует угрозу и начинает саботировать процесс. Она шепчет: «Давай потом», «У тебя нет времени», «Это всё ерунда».\n\nНе поддавайся. Тебе не обязательно писать длинные тексты. Просто зайди в систему прямо сейчас и напиши Наставнику одну фразу: как прошел твой сегодняшний день.\n\nТвой прогресс сохранен. Жду тебя внутри: https://mukti-app.streamlit.app/\n\n---\nОтключить напоминания от Архитектора: https://mukti-app.streamlit.app/?unsubscribe={u_email}"
                    
                    if rem_type > 0:
                        res = send_email(u_email, subj, body)
                        if res == "OK":
                            reminders_sent.append(rem_type)
                            prof["reminders_sent"] = reminders_sent
                            db.update_field(r_num, 5, json.dumps(prof))
                            sent_count += 1
                            time.sleep(1) 
                            
                st.success(f"✅ Рассылка завершена. Писем отправлено: {sent_count}")

    st.markdown("---")
    st.markdown("### 👥 База Аватаров (CRM)")
    if table_data:
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Матрица пока пуста. Ожидаем первых Аватаров.")
        
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚪 ВЫЙТИ ИЗ ТЕРМИНАЛА АРХИТЕКТОРА", use_container_width=True):
        try: cookie_manager.delete("mukti_user")
        except: pass
        st.session_state.logged_in = False
        time.sleep(0.5)
        st.rerun()

# ==========================================
# ЕЖЕДНЕВНОЕ ПОСЛАНИЕ (ДЛЯ АВАТАРОВ)
# ==========================================
elif st.session_state.reading_message:
    msg_day = int(st.session_state.user_profile.get("msg_day", 0))
    next_day = msg_day + 1
    message_text = msg_module.get_message_for_day(next_day)
    
    if message_text:
        st.markdown(f"<div style='border: 2px solid #00E676; padding: 20px; border-radius: 10px; background: rgba(0, 230, 118, 0.05);'>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='color: #00E676;'>ПОСЛАНИЕ НА ДЕНЬ</h3>", unsafe_allow_html=True)
        st.markdown(message_text)
        st.markdown("</div><br>", unsafe_allow_html=True)
        
        if st.button("✅ ДАННЫЕ ОСОЗНАЛ (ОТКРЫТЬ ТЕРМИНАЛ)", use_container_width=True):
            st.session_state.user_profile["msg_day"] = next_day
            st.session_state.user_profile["last_msg_date"] = get_mukti_date()
            st.session_state.user_profile["last_active"] = str(date.today())
            db.update_profile(st.session_state.row_num, "msg_day", next_day)
            db.update_profile(st.session_state.row_num, "last_msg_date", get_mukti_date())
            db.update_profile(st.session_state.row_num, "last_active", str(date.today()))
            st.session_state.reading_message = False
            st.rerun()
    else:
        st.session_state.reading_message = False
        st.rerun()

# ==========================================
# ОСНОВНОЙ ИНТЕРФЕЙС (ЧАТ / ЗАБОТА)
# ==========================================
else:
    # --- РАСЧЕТ ЭНЕРГИИ ---
    msgs_today = 0
    today_str = str(date.today())
    
    row_data, _ = db.load_user(st.session_state.user_email)
    if row_data:
        last_date = row_data[4] if len(row_data) > 4 else today_str
        msgs_today = int(row_data[3]) if len(row_data) > 3 and str(row_data[3]).isdigit() else 0
        if last_date != today_str:
            msgs_today = 0
            db.update_field(st.session_state.row_num, 5, today_str) 
            db.update_field(st.session_state.row_num, 4, msgs_today) 

    msg_day = int(st.session_state.user_profile.get("msg_day", 0))
    is_day_one = (msg_day <= 1)
    current_limit = 20 if st.session_state.is_vip else (10 if is_day_one else 3)
    limit_text = f"{msgs_today} / {current_limit}"
    can_send = msgs_today < current_limit
    status_text = "🌟 VIP" if st.session_state.is_vip else ("🟢 Базовый (День 1)" if is_day_one else "🔵 Базовый")

    # --- ВАРИАНТ 3: ВЫПАДАЮЩЕЕ МЕНЮ (EXPANDER) ---
    with st.expander(f"⚙️ ПАНЕЛЬ УПРАВЛЕНИЯ: {st.session_state.username}", expanded=False):
        st.markdown(f"**Уровень загрузки:** День {msg_day}/61")
        st.markdown(f"**Энергия:** {limit_text}")
        st.markdown(f"**Режим:** {status_text}")
        
        st.markdown("---")
        col_nav1, col_nav2, col_nav3 = st.columns(3)
        with col_nav1:
            if st.button("💬 ТЕРМИНАЛ", use_container_width=True):
                st.session_state.current_view = "chat"
                st.rerun()
        with col_nav2:
            if st.button("💌 ОТДЕЛ ЗАБОТЫ", use_container_width=True):
                st.session_state.current_view = "care"
                st.rerun()
        with col_nav3:
            if st.button("🚪 ВЫХОД", use_container_width=True):
                try: cookie_manager.delete("mukti_user")
                except: pass
                st.session_state.logged_in = False
                time.sleep(0.5)
                st.rerun()

    # ВЬЮ: ОТДЕЛ ЗАБОТЫ
    if st.session_state.current_view == "care":
        st.markdown("<h2 style='text-align: center; color: #00E676;'>ОТДЕЛ ЗАБОТЫ</h2>", unsafe_allow_html=True)
        st.markdown("Здесь ты можешь задать вопрос Архитектору, сообщить об ошибке или запросить **Полный доступ (VIP)**.")
        
        default_text = ""
        if not st.session_state.is_vip:
            default_text = "Привет, Архитектор!\n\nПрошу открыть мне Полный доступ (VIP) к системе МУКТИ. Готов к работе."
            
        with st.form("care_form"):
            user_msg = st.text_area("Твое сообщение:", value=default_text, height=150)
            if st.form_submit_button("ОТПРАВИТЬ АРХИТЕКТОРУ"):
                if user_msg.strip():
                    subj_admin = f"МУКТИ: Запрос от {st.session_state.username}"
                    body_admin = f"Аватар: {st.session_state.username}\nEmail: {st.session_state.user_email}\nVIP: {st.session_state.is_vip}\nДень: {msg_day}\n\nСообщение:\n{user_msg}"
                    res_admin = send_email(YANDEX_EMAIL, subj_admin, body_admin)
                    
                    msg_upper = user_msg.upper()
                    if "VIP" in msg_upper or "ПОЛНЫЙ ДОСТУП" in msg_upper:
                        subj_user = "МУКТИ: Активация Полного доступа (VIP)"
                        body_user = f"""Приветствую, {st.session_state.username}! На связи Роман - Архитектор проекта МУКТИ.

В данный момент система МУКТИ находится в стадии закрытого бета-тестирования (MVP), поэтому шлюзы оплаты еще не автоматизированы, и я активирую профили пользователей вручную.

Что ты получишь, перейдя в режим VIP (Полный доступ):
🟢 Расширенный резерв энергии: до 20 глубоких диалогов с ИИ-наставником каждый день. Этого хватит для полноценной проработки любых триггеров и стрессов.
🟢 Персональная аналитика: Матрица будет лучше запоминать твои слабости и превентивно блокировать атаки Гостя.
🟢 Непрерывность: Полный доступ ровно на 61 день - именно столько нужно для глубокой перепрошивки нейронных связей и прохождения всей программы.
🟢 Прямая поддержка: Приоритетная связь со мной (Архитектором) через Отдел Заботы.

Стоимость и оплата:
Полная стоимость подписки составляет 2990 рублей. Но так как ты являешься ранним участником (бета-тестером), для тебя действует специальная цена - всего 1220 рублей (это ровно 20 рублей в день за твою свободу).

Как активировать доступ прямо сейчас:

Сделай перевод 1220 рублей по номеру: +7 (905) 294-52-45 (Сбербанк, Роман В).

Пришли скриншот чека ответным письмом на это сообщение.

В течение нескольких часов (обычно быстрее) я вручную переведу твой аккаунт в статус VIP, и система снимет все ограничения.

Готов выйти из Матрицы? Жду подтверждения.

С уважением Роман, Архитектор проекта МУКТИ"""
                        send_email(st.session_state.user_email, subj_user, body_user)
                    if res_admin == "OK": 
                        st.success("Сообщение успешно доставлено! Ответ (или инструкция по VIP) придет на твою почту. Обязательно проверь папку «Спам»!")
                    else: 
                        st.error(f"Ошибка: {res_admin}")
                else: st.warning("Напиши текст сообщения.")

    # ВЬЮ: ЧАТ
    else:
        for msg in st.session_state.messages:
            if msg["role"] != "system":
                av = BOT_AVATAR if msg["role"] == "assistant" else USER_AVATAR
                with st.chat_message(msg["role"], avatar=av):
                    st.markdown(msg["content"])

        if not can_send:
            if st.session_state.is_vip:
                st.markdown("<div class='limit-alert' style='border-color: #00E676;'><b>🔋 Нейронная сеть перегружена.</b><br>Система перейдет в спящий режим до завтра.</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='limit-alert' style='border-color: #FF3D00;'><b>⚠️ Энергия наставника исчерпана на сегодня.</b><br><i>Запроси Полный доступ (VIP), чтобы продолжить работу прямо сейчас.</i></div>", unsafe_allow_html=True)
            
        elif prompt := st.chat_input("Напиши мне..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar=USER_AVATAR): st.markdown(prompt)

            msgs_today += 1
            db.update_field(st.session_state.row_num, 4, msgs_today)
            st.session_state.user_profile["last_active"] = str(date.today())
            db.update_profile(st.session_state.row_num, "last_active", str(date.today()))

            if st.session_state.calibration_step > 0:
                step = st.session_state.calibration_step
                resp = ""
                if step == 1:
                    db.update_profile(st.session_state.row_num, "read_book", prompt)
                    st.session_state.user_profile["read_book"] = prompt
                    book_link = "[по этой ссылке](https://www.litres.ru/book/roman-vybornov/pochemu-ya-nikogo-ne-em-72075331/)"
                    if "нет" in prompt.lower():
                        resp = f"Понял. Очень рекомендую прочитать ее в свободное время {book_link}, это усилит твою защиту. А пока идем дальше.\n\n**Как часто Гость (Алкоголь) обычно перехватывает управление?** (Каждый день, только по выходным, бывают запои?)"
                    else:
                        resp = f"Отлично, значит мы говорим на одном языке. Если захочешь освежить знания, книга лежит {book_link}.\n\n**Как часто Гость (Алкоголь) обычно перехватывает управление?** (Каждый день, только по выходным, бывают запои?)"
                    st.session_state.calibration_step = 2
                elif step == 2:
                    db.update_profile(st.session_state.row_num, "frequency", prompt)
                    st.session_state.user_profile["frequency"] = prompt
                    resp = "Записал. **В какие именно моменты его шепот звучит громче всего? Что служит триггером?** (Сильный стресс на работе, скука дома, компании друзей?)"
                    st.session_state.calibration_step = 3
                elif step == 3:
                    db.update_profile(st.session_state.row_num, "triggers", prompt)
                    st.session_state.user_profile["triggers"] = prompt
                    resp = "Понял. **Какой у тебя опыт сопротивления?** (Это твоя первая осознанная попытка или ты уже пробовал выходить из системы?)"
                    st.session_state.calibration_step = 4
                elif step == 4:
                    db.update_profile(st.session_state.row_num, "history", prompt)
                    st.session_state.user_profile["history"] = prompt
                    resp = "И последнее, но очень важное. **Что ты чувствуешь прямо сейчас?** (Страх, решимость, сомнения, или Гость уже пытается с тобой торговаться?)"
                    st.session_state.calibration_step = 5
                elif step == 5:
                    db.update_profile(st.session_state.row_num, "state", prompt)
                    st.session_state.user_profile["state"] = prompt
                    resp = "Данные приняты. Профиль оцифрован, алгоритмы защиты настроены.\n\n**Расскажи, как прошел твой день сегодня? Пытался ли Гость выйти на связь, или пока всё тихо?**"
                    st.session_state.calibration_step = 0
                    
                with st.chat_message("assistant", avatar=BOT_AVATAR): st.markdown(resp)
                st.session_state.messages.append({"role": "assistant", "content": resp})
                db.save_history(st.session_state.row_num, st.session_state.messages)
                
                if st.session_state.calibration_step == 0:
                    st.session_state.reading_message = True
                    time.sleep(1.5) 
                    st.rerun()
            else:
                easter_eggs = ["хочу выпить", "пиво", "накатить", "срыв"]
                if any(word in prompt.lower() for word in easter_eggs):
                    resp = random.choice([
                        "🚨 **ВНИМАНИЕ! ОБНАРУЖЕНА АКТИВНОСТЬ ГОСТЯ.** 🚨\nЭто не твои мысли. Сделай 10 глубоких вдохов. Ты сильнее программы.",
                        "Активирован защитный протокол. Напоминаю: алкоголь забирает у тебя завтрашний день, чтобы дать в долг сегодня под бешеные проценты."
                    ])
                    with st.chat_message("assistant", avatar=BOT_AVATAR): st.markdown(resp)
                    st.session_state.messages.append({"role": "assistant", "content": resp})
                    db.save_history(st.session_state.row_num, st.session_state.messages)
                else:
                    with st.chat_message("assistant", avatar=BOT_AVATAR):
                        with st.spinner("Оцифровка мыслей..."):
                            sys_prompt = settings.get_system_prompt(st.session_state.username, st.session_state.user_profile, BOOK_SUMMARY)
                            full_p = f"{sys_prompt}\nИстория:\n{st.session_state.messages[-5:]}\nUser: {prompt}"
                            txt = None
                            for i in range(3):
                                if model:
                                    try:
                                        txt = model.generate_content(full_p).text
                                        break
                                    except: time.sleep(1)
                            if txt:
                                st.markdown(txt)
                                st.session_state.messages.append({"role": "assistant", "content": txt})
                                db.save_history(st.session_state.row_num, st.session_state.messages)
                            else: st.error("Сбой связи. Попробуй еще раз.")
