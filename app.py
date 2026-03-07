import streamlit as st
import google.generativeai as genai
from datetime import datetime, timedelta, date
import time
import json
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ИМПОРТ МОДУЛЕЙ
import settings
import database as db
import messages as msg_module

# --- НАСТРОЙКИ ---
VIP_CODE = st.secrets.get("VIP_CODE", settings.VIP_CODE_DEFAULT)
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"] if "GOOGLE_API_KEY" in st.secrets else "NO_KEY"
YANDEX_EMAIL = st.secrets.get("YANDEX_EMAIL", "")
YANDEX_PASSWORD = st.secrets.get("YANDEX_PASSWORD", "")

genai.configure(api_key=GOOGLE_API_KEY)

try:
    from book import BOOK_SUMMARY
except ImportError:
    BOOK_SUMMARY = "Методика освобождения."

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

# --- ФУНКЦИИ ---
def send_email(to_email, subject, body):
    if not YANDEX_EMAIL or not YANDEX_PASSWORD:
        return "ОШИБКА: Файл secrets.toml не видит YANDEX_EMAIL или YANDEX_PASSWORD."
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

# ==========================================
# АВТОРИЗАЦИЯ И РЕГИСТРАЦИЯ (EMAIL)
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: #00E676;'>МУКТИ</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #A0A0A0;'>Система выхода из матрицы зависимости</p>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["ВХОД", "РЕГИСТРАЦИЯ", "ЗАБЫЛ ПАРОЛЬ"])
    
    # ВХОД
    with tab1:
        with st.form("login_form"):
            email_in = st.text_input("Email").strip().lower()
            pwd_in = st.text_input("Пароль", type="password").strip()
            if st.form_submit_button("ВОЙТИ"):
                if email_in and pwd_in:
                    row_data, r_num = db.load_user(email_in)
                    if row_data and row_data[2] == pwd_in:
                        st.session_state.logged_in = True
                        st.session_state.user_email = email_in
                        st.session_state.username = row_data[1] 
                        st.session_state.row_num = r_num
                        st.session_state.is_vip = (len(row_data) > 7 and row_data[7] == "TRUE")
                        
                        try: st.session_state.user_profile = json.loads(row_data[5]) if len(row_data)>5 else {}
                        except: st.session_state.user_profile = {}
                        
                        try: st.session_state.messages = json.loads(row_data[6]) if len(row_data)>6 else []
                        except: st.session_state.messages = []
                        
                        # ЕСЛИ ИСТОРИЯ ПУСТАЯ - ЗАПУСКАЕМ ЖИВУЮ КАЛИБРОВКУ
                        if not st.session_state.messages:
                            st.session_state.calibration_step = 1
                            welcome = f"Приветствую, {st.session_state.username}. Я — твой ИИ-наставник МУКТИ. Вижу, ты здесь впервые.\n\nДля настройки алгоритмов защиты мне нужно откалибровать твои параметры. Ответь прямо в этот чат: **ты уже читал книгу «Кто такой Алкоголь»?**"
                            st.session_state.messages = [{"role": "assistant", "content": welcome}]
                            db.save_history(st.session_state.row_num, st.session_state.messages)
                            
                        current_date = get_mukti_date()
                        last_msg_date = st.session_state.user_profile.get("last_msg_date", "")
                        msg_day = int(st.session_state.user_profile.get("msg_day", 0))
                        
                        # Послание выводится, только если калибровка пройдена (step == 0)
                        if last_msg_date != current_date and msg_day < 61 and st.session_state.calibration_step == 0:
                            st.session_state.reading_message = True
                            
                        st.rerun()
                    else: st.error("Ошибка доступа. Неверный Email или Пароль.")
                else: st.warning("Введи данные.")

    # РЕГИСТРАЦИЯ
    with tab2:
        with st.form("reg_form"):
            new_email = st.text_input("Email (Твой ID в системе)").strip().lower()
            new_user = st.text_input("Придумай Имя Аватара").strip()
            new_pwd = st.text_input("Придумай Пароль", type="password").strip()
            vip_in = st.text_input("Код доступа (если есть)").strip()
            
            if st.form_submit_button("СОЗДАТЬ ПРОФИЛЬ"):
                if not new_email or "@" not in new_email:
                    st.error("Введи корректный Email.")
                elif len(new_pwd) < 4:
                    st.error("Пароль должен быть не короче 4 символов.")
                elif new_user:
                    res = db.register_user(new_email, new_user, new_pwd)
                    if res == "OK":
                        if vip_in == VIP_CODE:
                            _, r_num = db.load_user(new_email)
                            db.update_field(r_num, 8, "TRUE")
                        st.success("Профиль создан! Теперь войди в систему на вкладке ВХОД.")
                    elif res == "TAKEN": st.error("Этот Email уже зарегистрирован.")
                    else: st.error("Ошибка БД.")
                else: st.warning("Заполни все поля.")

    # ВОССТАНОВЛЕНИЕ ПАРОЛЯ
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
                        body = f"Приветствую, {row_data[1]}.\n\nТвой пароль для доступа в Матрицу: {pwd}\n\nНе теряй его.\nАрхитектор."
                        res = send_email(rec_email, subject, body)
                        if res == "OK":
                            st.success("Письмо с паролем отправлено! Проверь почту (и папку Спам).")
                        else:
                            st.error(f"Сбой отправки: {res}")
                    else:
                        st.error("Аватар с таким Email не найден.")

# ==========================================
# ЕЖЕДНЕВНОЕ ПОСЛАНИЕ (БЛОКИРАТОР ЭКРАНА)
# ==========================================
elif st.session_state.reading_message:
    msg_day = int(st.session_state.user_profile.get("msg_day", 0))
    next_day = msg_day + 1
    
    message_text = msg_module.get_message_for_day(next_day)
    
    if message_text:
        st.markdown(f"<div style='border: 2px solid #00E676; padding: 20px; border-radius: 10px; background: rgba(0, 230, 118, 0.05);'>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='color: #00E676;'>📥 ВХОДЯЩАЯ ПЕРЕДАЧА: ДЕНЬ {next_day}</h3>", unsafe_allow_html=True)
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
# ОСНОВНОЙ ТЕРМИНАЛ (ЧАТ И ЖИВАЯ КАЛИБРОВКА)
# ==========================================
else:
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        msg_day = st.session_state.user_profile.get("msg_day", 0)
        st.markdown(f"**Уровень загрузки:** День {msg_day}/61")
        st.markdown("---")
        
        if st.button("🚪 ВЫХОД"):
            st.session_state.logged_in = False
            st.rerun()

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

    is_newbie = msg_day <= 3
    current_limit = settings.LIMIT_NEW_USER if is_newbie else settings.LIMIT_OLD_USER
    
    if st.session_state.is_vip:
        limit_text = "∞ (VIP)"
        can_send = True
    else:
        limit_text = f"{msgs_today} / {current_limit}"
        can_send = msgs_today < current_limit

    col1, col2 = st.columns([3, 1])
    with col1: st.markdown(f"**Статус:** {'🟢 Режим Адаптации' if is_newbie else '🔵 Основной Режим'}")
    with col2: st.markdown(f"**Энергия ИИ:** {limit_text}")

    # ИСТОРИЯ ЧАТА
    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # ЛИМИТЫ
    if not can_send:
        st.markdown(f"""
        <div class='limit-alert'>
            <b>⚠️ Энергия наставника исчерпана на сегодня.</b><br>
            Сделай паузу. Подыши. Понаблюдай за мыслями.<br>
            Возвращайся завтра, система перезагрузится.
        </div>
        """, unsafe_allow_html=True)
        
    # ВВОД ПОЛЬЗОВАТЕЛЯ
    elif prompt := st.chat_input("Напиши мне..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        if not st.session_state.is_vip:
            msgs_today += 1
            db.update_field(st.session_state.row_num, 4, msgs_today)

        # --- ЛОГИКА КАЛИБРОВКИ В ДИАЛОГЕ ---
        if st.session_state.calibration_step > 0:
            step = st.session_state.calibration_step
            resp = ""
            
            if step == 1:
                db.update_profile(st.session_state.row_num, "read_book", prompt)
                st.session_state.user_profile["read_book"] = prompt
                if "нет" in prompt.lower():
                    resp = "Понял. Очень рекомендую прочитать ее в свободное время, это усилит твою защиту. А пока идем дальше.\n\n**Как часто Гость (Алкоголь) обычно перехватывает управление?** (Каждый день, только по выходным, бывают запои?)"
                else:
                    resp = "Отлично, значит мы говорим на одном языке. Идем дальше.\n\n**Как часто Гость (Алкоголь) обычно перехватывает управление?** (Каждый день, только по выходным, бывают запои?)"
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
                resp = "Данные приняты. Профиль Врага оцифрован. Алгоритмы защиты настроены.\nМатрица готова к работе."
                st.session_state.calibration_step = 0
                
            with st.chat_message("assistant"): st.markdown(resp)
            st.session_state.messages.append({"role": "assistant", "content": resp})
            db.save_history(st.session_state.row_num, st.session_state.messages)
            
            # Если калибровка только что закончилась - перезагружаем страницу, чтобы выдать Послание День 1
            if st.session_state.calibration_step == 0:
                st.session_state.reading_message = True
                time.sleep(1.5) # Небольшая пауза для эффекта загрузки
                st.rerun()

        # --- ПАСХАЛКИ И ОБЫЧНЫЙ AI-ОТВЕТ ---
        else:
            easter_eggs = ["хочу выпить", "пиво", "накатить", "срыв"]
            if any(word in prompt.lower() for word in easter_eggs):
                resp = random.choice([
                    "🚨 **ВНИМАНИЕ! ОБНАРУЖЕНА АКТИВНОСТЬ ГОСТЯ.** 🚨\nЭто не твои мысли. Сделай 10 глубоких вдохов. Ты сильнее программы.",
                    "Активирован защитный протокол. Напоминаю: алкоголь забирает у тебя завтрашний день, чтобы дать в долг сегодня под бешеные проценты."
                ])
                with st.chat_message("assistant"): st.markdown(resp)
                st.session_state.messages.append({"role": "assistant", "content": resp})
                db.save_history(st.session_state.row_num, st.session_state.messages)

            else:
                with st.chat_message("assistant"):
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
