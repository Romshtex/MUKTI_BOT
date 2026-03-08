import streamlit as st
import google.generativeai as genai
from datetime import datetime, timedelta, date
import time
import json
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import extra_streamlit_components as stx  # НОВАЯ БИБЛИОТЕКА ДЛЯ COOKIES

# ИМПОРТ МОДУЛЕЙ
import settings
import database as db
import messages as msg_module

# --- НАСТРОЙКИ ---
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"] if "GOOGLE_API_KEY" in st.secrets else "NO_KEY"
YANDEX_EMAIL = st.secrets.get("YANDEX_EMAIL", "")
YANDEX_PASSWORD = st.secrets.get("YANDEX_PASSWORD", "")

genai.configure(api_key=GOOGLE_API_KEY)

try:
    from book import BOOK_SUMMARY
except ImportError:
    BOOK_SUMMARY = "Методика освобождения."

# --- CSS: МАТРИЦА С ТОНИРОВКОЙ ---
st.markdown("""
<style>
    .stApp > header { background-color: transparent !important; }
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
</style>
""", unsafe_allow_html=True)

# --- ИНИЦИАЛИЗАЦИЯ COOKIES ---
@st.cache_resource(experimental_allow_widgets=True)
def get_manager():
    return stx.CookieManager()
cookie_manager = get_manager()

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
        st.session_state.is_vip = (len(row_data) > 7 and row_data[7] == "TRUE")
        
        try: st.session_state.user_profile = json.loads(row_data[5]) if len(row_data)>5 else {}
        except: st.session_state.user_profile = {}
        
        try: st.session_state.messages = json.loads(row_data[6]) if len(row_data)>6 else []
        except: st.session_state.messages = []
        
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
    st.markdown("<p style='text-align: center; color: #A0A0A0;'>Система выхода из матрицы зависимости</p>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["ВХОД", "РЕГИСТРАЦИЯ", "ЗАБЫЛ ПАРОЛЬ"])
    
    with tab1:
        with st.form("login_form"):
            email_in = st.text_input("Email").strip().lower()
            pwd_in = st.text_input("Пароль", type="password").strip()
            if st.form_submit_button("ВОЙТИ"):
                if email_in and pwd_in:
                    row_data, r_num = db.load_user(email_in)
                    if row_data and row_data[2] == pwd_in:
                        # Ставим печать в браузер на 30 дней
                        cookie_manager.set("mukti_user", email_in, expires_at=datetime.now() + timedelta(days=30))
                        load_user_to_session(email_in)
                        time.sleep(0.5) # Ждем прогрузки куки
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

# ==========================================
# ЕЖЕДНЕВНОЕ ПОСЛАНИЕ
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
            db.update_profile(st.session_state.row_num, "msg_day", next_day)
            db.update_profile(st.session_state.row_num, "last_msg_date", get_mukti_date())
            st.session_state.reading_message = False
            st.rerun()
    else:
        st.session_state.reading_message = False
        st.rerun()

# ==========================================
# ОСНОВНОЙ ИНТЕРФЕЙС (ЧАТ ИЛИ ОТДЕЛ ЗАБОТЫ)
# ==========================================
else:
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        msg_day = st.session_state.user_profile.get("msg_day", 0)
        st.markdown(f"**Уровень загрузки:** День {msg_day}/61")
        if st.session_state.is_vip:
            st.markdown("🌟 **Статус: Полный доступ**")
        st.markdown("---")
        
        if st.button("💬 ТЕРМИНАЛ (Чат)"):
            st.session_state.current_view = "chat"
            st.rerun()
            
        if st.button("💌 ОТДЕЛ ЗАБОТЫ"):
            st.session_state.current_view = "care"
            st.rerun()
            
        st.markdown("---")
        if st.button("🚪 ВЫХОД"):
            # Стираем печать при выходе!
            cookie_manager.delete("mukti_user")
            st.session_state.logged_in = False
            time.sleep(0.5)
            st.rerun()

    # ВЬЮ: ОТДЕЛ ЗАБОТЫ
    if st.session_state.current_view == "care":
        st.markdown("<h2 style='text-align: center; color: #00E676;'>ОТДЕЛ ЗАБОТЫ</h2>", unsafe_allow_html=True)
        st.markdown("Здесь ты можешь задать вопрос Архитектору, сообщить об ошибке или запросить **Полный доступ (VIP)**.")
        
        default_text = ""
        msgs_today = int(db.load_user(st.session_state.user_email)[0][3]) if db.load_user(st.session_state.user_email)[0] else 0
        if not st.session_state.is_vip and msgs_today >= 10:
            default_text = "Привет, Архитектор!\n\nЯ прошел первый день калибровки и готов к серьезной работе с МУКТИ. Прошу открыть мне Полный доступ (VIP)."
            
        with st.form("care_form"):
            user_msg = st.text_area("Твое сообщение:", value=default_text, height=150)
            if st.form_submit_button("ОТПРАВИТЬ АРХИТЕКТОРУ"):
                if user_msg.strip():
                    subj = f"МУКТИ: Запрос от {st.session_state.username}"
                    body = f"Аватар: {st.session_state.username}\nEmail: {st.session_state.user_email}\nVIP: {st.session_state.is_vip}\nДень: {msg_day}\n\nСообщение:\n{user_msg}"
                    res = send_email(YANDEX_EMAIL, subj, body)
                    if res == "OK":
                        st.success("Сообщение успешно доставлено! Ответ придет на твою электронную почту.")
                    else:
                        st.error(f"Ошибка отправки: {res}")
                else:
                    st.warning("Напиши текст сообщения.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔙 ВЕРНУТЬСЯ В ТЕРМИНАЛ", use_container_width=True):
            st.session_state.current_view = "chat"
            st.rerun()

    # ВЬЮ: ЧАТ
    else:
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

        is_day_one = (msg_day <= 1)
        if st.session_state.is_vip:
            current_limit = 20
        else:
            current_limit = 10 if is_day_one else 3

        limit_text = f"{msgs_today} / {current_limit}"
        can_send = msgs_today < current_limit

        col1, col2 = st.columns([3, 1])
        with col1: 
            if st.session_state.is_vip: st.markdown("**Режим:** 🌟 Полный доступ")
            else: st.markdown(f"**Режим:** {'🟢 Базовый (День 1)' if is_day_one else '🔵 Базовый'}")
        with col2: 
            st.markdown(f"**Энергия:** {limit_text}")

        for msg in st.session_state.messages:
            if msg["role"] != "system":
                avatar_icon = "🟢" if msg["role"] == "assistant" else "🔵"
                with st.chat_message(msg["role"], avatar=avatar_icon):
                    st.markdown(msg["content"])

        if not can_send:
            if st.session_state.is_vip:
                st.markdown("""
                <div class='limit-alert' style='border-color: #00E676;'>
                    <b>🔋 Нейронная сеть перегружена.</b><br>
                    На сегодня мы проделали отличную работу, но тебе нужен отдых для усвоения данных.<br>
                    Система перейдет в спящий режим до завтра. Подыши и отдохни.
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class='limit-alert' style='border-color: #FF3D00;'>
                    <b>⚠️ Энергия наставника исчерпана на сегодня.</b><br>
                    Сделай паузу. Подыши. Понаблюдай за мыслями.<br>
                    <i>Завтра базовый резерв энергии восстановится, и мы сможем продолжить. Или запроси Полный доступ (VIP), чтобы продолжить работу прямо сейчас.</i>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("💌 НАПИСАТЬ В ОТДЕЛ ЗАБОТЫ", use_container_width=True):
                    st.session_state.current_view = "care"
                    st.rerun()
            
        elif prompt := st.chat_input("Напиши мне..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="🔵"): st.markdown(prompt)

            msgs_today += 1
            db.update_field(st.session_state.row_num, 4, msgs_today)

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
                    
                with st.chat_message("assistant", avatar="🟢"): st.markdown(resp)
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
                    with st.chat_message("assistant", avatar="🟢"): st.markdown(resp)
                    st.session_state.messages.append({"role": "assistant", "content": resp})
                    db.save_history(st.session_state.row_num, st.session_state.messages)

                else:
                    with st.chat_message("assistant", avatar="🟢"):
                        with st.spinner("Оцифровка мыслей..."):
                            sys_prompt = settings.get_system_prompt(
                                st.session_state.username, 
                                st.session_state.user_profile, 
                                BOOK_SUMMARY
                            )
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
                            else: st.error("Сбой связи. Матрица сопротивляется. Попробуй еще раз.")
