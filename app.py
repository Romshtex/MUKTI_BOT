import streamlit as st
from google import genai
from datetime import datetime, timedelta, date
import time
import json
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import extra_streamlit_components as stx  
import hashlib
import secrets
import hmac
import requests
import os

# --- ИКОНКА ДЛЯ ВКЛАДКИ БРАУЗЕРА (FAVICON) ---
st.set_page_config(page_title="МУКТИ | Система выхода", page_icon="logo.png")

# ИМПОРТ МОДУЛЕЙ
import settings
import database as db
import messages as msg_module

# --- НАСТРОЙКИ ---
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"] if "GOOGLE_API_KEY" in st.secrets else "NO_KEY"
YANDEX_EMAIL = st.secrets.get("YANDEX_EMAIL", "mukti.system@yandex.com")
YANDEX_PASSWORD = st.secrets.get("YANDEX_PASSWORD", "")

# Новые ключи безопасности (добавь их в secrets.toml)
SECRET_KEY = st.secrets["SECRET_KEY"]
ADMIN_EMAILS = st.secrets.get("ADMIN_EMAILS", ["mukti.system@yandex.com"])

ai_client = genai.Client(api_key=GOOGLE_API_KEY)

try:
    from book import get_book_summary, get_full_book
except ImportError:
    BOOK_SUMMARY = "Методика освобождения."

# --- ПУТИ К АКТИВАМ ---
def load_avatar(path: str, fallback: str):
    """
    Надежный аватар:
    - читаем файл в bytes
    - проверяем, что PIL реально распознаёт изображение
    - если нет -> fallback emoji (приложение не падает)
    """
    try:
        if not (path and os.path.isfile(path)):
            return fallback

        with open(path, "rb") as f:
            data = f.read()

        # Валидация, что это реальная картинка
        from PIL import Image
        import io
        Image.open(io.BytesIO(data)).verify()

        return data
    except Exception:
        return fallback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOT_PATH = os.path.join(BASE_DIR, "assets", "mukti_avatar.png")
USER_PATH = os.path.join(BASE_DIR, "assets", "user_avatar.png")

BOT_AVATAR = load_avatar(BOT_PATH, "👁️")
USER_AVATAR = load_avatar(USER_PATH, "⚡")

# --- ПРИМЕНЕНИЕ ПРЕМИУМ-СТИЛЕЙ ---
settings.inject_custom_css()

# --- ИНИЦИАЛИЗАЦИЯ COOKIES И КРИПТОГРАФИИ ---
cookie_manager = stx.CookieManager(key="mukti_cookies")

def generate_temp_password(length=8):
    return secrets.token_urlsafe(length)[:length]

def make_session_token(email: str) -> str:
    """Создаёт подписанный токен для cookie: base64(email|ts)|подпись"""
    import base64
    ts = str(int(time.time()))
    payload = base64.b64encode(f"{email}|{ts}".encode()).decode()
    sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"

def verify_session_token(token: str) -> str | None:
    """Проверяет токен. Возвращает email если всё ок, иначе None."""
    import base64
    try:
        payload, sig = token.rsplit(".", 1)
        expected_sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, sig):
            return None
        decoded = base64.b64decode(payload.encode()).decode()
        email, ts = decoded.rsplit("|", 1)
        # Токен живёт максимум 30 дней
        if time.time() - int(ts) > 30 * 24 * 3600:
            return None
        return email
    except Exception:
        return None


def get_unsubscribe_token(email):
    return hmac.new(SECRET_KEY.encode(), email.encode(), hashlib.sha256).hexdigest()

def get_verify_token(email):
    return hmac.new(SECRET_KEY.encode(), (email + "_verify").encode(), hashlib.sha256).hexdigest()

# --- ПРОВЕРКА СОГЛАСИЯ НА COOKIES ---
if "cookies_accepted_session" not in st.session_state:
    st.session_state.cookies_accepted_session = False

if not st.session_state.cookies_accepted_session and cookie_manager.get(cookie="cookies_accepted") != "true":
    st.markdown("""
    <div style='background-color: rgba(30,30,30,0.9); border: 1px solid #B8973A; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 15px;'>
        <span style='color: #FAFAFA; font-size: 14px;'>
            Система МУКТИ использует файлы cookie, чтобы сохранять твою сессию и обеспечивать безопасность. 
            Продолжая использовать терминал, ты даешь согласие на их обработку.
        </span>
    </div>
    """, unsafe_allow_html=True)
    if st.button("ПРИНЯТЬ И СКРЫТЬ", key="accept_cookies_btn", use_container_width=True):
        cookie_manager.set("cookies_accepted", "true", expires_at=datetime.now() + timedelta(days=365))
        st.session_state.cookies_accepted_session = True
        time.sleep(0.5) # Даем браузеру долю секунды на запись файла
        st.rerun()

# --- ПЕРЕХВАТЧИК ОТПИСКИ ОТ РАССЫЛКИ ---
if "unsubscribe_token" in st.query_params:
    token = st.query_params["unsubscribe_token"]
    # Ищем пользователя по совпадению токена — email в URL не передаём
    found = False
    all_users = db.get_all_users()
    for r_num, u_email, u_name, p_json in all_users:
        if hmac.compare_digest(token, get_unsubscribe_token(u_email)):
            try:
                profile = json.loads(p_json) if p_json else {}
            except:
                profile = {}
            profile["unsubscribed"] = True
            db.update_field(r_num, 6, json.dumps(profile))
            st.success("Связь прервана. Напоминания навсегда отключены.")
            found = True
            break
    if not found:
        st.error("Недействительная ссылка отписки.")
    st.query_params.clear()

# --- ПЕРЕХВАТЧИК ВЕРИФИКАЦИИ EMAIL ---
if "verify" in st.query_params and "token" in st.query_params:
    ver_email = st.query_params["verify"]
    token = st.query_params["token"]
    
    if token == get_verify_token(ver_email):
        row_data, r_num = db.load_user(ver_email)
        if row_data:
            try: profile = json.loads(row_data[5]) if len(row_data)>5 else {}
            except: profile = {}
            
            profile["email_verified"] = True
            db.update_field(r_num, 6, json.dumps(profile)) 
            st.success(f"Сектор доступа подтвержден! Email {ver_email} закреплен за тобой.")
            st.query_params.clear()
    else:
        st.error("Ошибка верификации. Токен устарел или поврежден.")
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

# --- СОСТОЯНИЕ ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "calibration_step" not in st.session_state: st.session_state.calibration_step = 0
if "reading_message" not in st.session_state: st.session_state.reading_message = False
if "current_view" not in st.session_state: st.session_state.current_view = "chat"
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None
if "login_attempts" not in st.session_state: st.session_state.login_attempts = 0
if "login_blocked_until" not in st.session_state: st.session_state.login_blocked_until = None

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
        
        # МАГИЯ ЗДЕСЬ: Используем открытый порт 587 и команду starttls()
        server = smtplib.SMTP('smtp.yandex.ru', 587, timeout=10)
        server.starttls() # Включаем шифрование канала
        server.login(YANDEX_EMAIL, YANDEX_PASSWORD)
        server.send_message(msg)
        server.quit()
        return "OK"
    except Exception as e: 
        return f"ОТКАЗ ЯНДЕКСА (Порт 587): {str(e)}"

def clip(text: str, max_chars: int = 1200) -> str:
    text = text or ""
    return text if len(text) <= max_chars else (text[:max_chars] + "…")

def build_history_text(messages, last_n: int = 6, max_chars_per_msg: int = 1200) -> str:
    last_msgs = [m for m in messages if m.get("role") != "system"][-last_n:]
    return "\n".join(
        f"{m['role'].capitalize()}: {clip(m.get('content', ''), max_chars_per_msg)}"
        for m in last_msgs
    )

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
        
        if email in ADMIN_EMAILS:
            st.session_state.current_view = "admin"
            st.session_state.reading_message = False
            return True

        # --- СЧЕТЧИК ПОСЕЩЕНИЙ VIP ---
        today_str = str(date.today())
        last_active_str = st.session_state.user_profile.get("last_active", "")
        
        # Если юзер VIP и зашел в НОВЫЙ день (а не просто обновил страницу)
        if st.session_state.is_vip and last_active_str != today_str:
            if "vip_days_remaining" in st.session_state.user_profile:
                st.session_state.user_profile["vip_days_remaining"] -= 1
                
                # Если лимит посещений исчерпан -> отключаем VIP
                if st.session_state.user_profile["vip_days_remaining"] <= 0:
                    st.session_state.is_vip = False
                    st.session_state.user_profile["is_vip"] = False
                    db.update_field(r_num, 8, "FALSE") # Снимаем флаг в БД
        
        # Обновляем дату последнего захода и сохраняем весь профиль со счетчиком
        st.session_state.user_profile["last_active"] = today_str
        db.update_field(r_num, 6, json.dumps(st.session_state.user_profile))

        if not st.session_state.messages:
            st.session_state.calibration_step = 1
            welcome = f"{st.session_state.username}, Вижу, ты здесь впервые.\n\nДля настройки алгоритмов защиты мне нужно откалибровать твои параметры. Ответь прямо в этот чат: **ты уже читал книгу «Кто такой Алкоголь»?**"
            st.session_state.messages = [{"role": "assistant", "content": welcome}]
            db.save_history(st.session_state.row_num, st.session_state.messages)
        else:
            # --- ВОССТАНОВЛЕНИЕ ШАГА КАЛИБРОВКИ ---
            m_len = len(st.session_state.messages)
            if m_len == 1: st.session_state.calibration_step = 1
            elif m_len == 3: st.session_state.calibration_step = 2
            elif m_len == 5: st.session_state.calibration_step = 3
            elif m_len == 7: st.session_state.calibration_step = 4
            elif m_len == 9: st.session_state.calibration_step = 5
            else: st.session_state.calibration_step = 0
            
        current_date = get_mukti_date()
        last_msg_date = st.session_state.user_profile.get("last_msg_date", "")
        msg_day = int(st.session_state.user_profile.get("msg_day", 0))
        
        if last_msg_date != current_date and msg_day < 61 and st.session_state.calibration_step == 0:
            st.session_state.reading_message = True
            
        st.session_state.current_view = "chat"
        return True
    return False
    
# АВТОЛОГИН ЧЕРЕЗ COOKIES

if not st.session_state.logged_in:
    saved_cookie = cookie_manager.get(cookie="mukti_user")
    if saved_cookie:
        verified_email = verify_session_token(saved_cookie)
        if verified_email and load_user_to_session(verified_email):
            st.rerun()
        elif not verified_email:
            # Токен невалиден или устарел — удаляем
            try:
                cookie_manager.delete("mukti_user")
            except Exception:
                pass

# ==========================================
# АВТОРИЗАЦИЯ И РЕГИСТРАЦИЯ
# ==========================================
if not st.session_state.logged_in:
    st.markdown('<div class="login-geo-bg">', unsafe_allow_html=True)
    st.image("logo_1.png", use_container_width=True)
    st.markdown(
    """
    **Привет!** Я - **МУКТИ**, твой персональный AI‑проводник в пространстве освобождения от зависимостей

    Моя главная задача - бережно провести тебя через следующие **61 день**, превратив знания из книги в твой реальный опыт.
    Здесь нет осуждения - только **100% анонимность** и поддержка **24/7**

    **Пройди быструю регистрацию, и мы начнем твой путь к настоящей свободе**
    """
    )
    
    tab1, tab2, tab3 = st.tabs(["ВХОД", "РЕГИСТРАЦИЯ", "ЗАБЫЛ ПАРОЛЬ"])
    
    with tab1:
        # Проверяем блокировку
        blocked = False
        if st.session_state.login_blocked_until:
            if datetime.now() < st.session_state.login_blocked_until:
                remaining = int((st.session_state.login_blocked_until - datetime.now()).total_seconds() / 60) + 1
                st.error(f"Слишком много попыток. Попробуй через {remaining} мин.")
                blocked = True
            else:
                # Блокировка истекла — сбрасываем
                st.session_state.login_attempts = 0
                st.session_state.login_blocked_until = None

        if not blocked:
            with st.form("login_form"):
                email_in = st.text_input("Email").strip().lower()
                pwd_in = st.text_input("Пароль", type="password").strip()
                if st.form_submit_button("ВОЙТИ"):
                    if email_in and pwd_in:
                        row_data, r_num = db.load_user(email_in)
                        # Единое сообщение — не раскрываем существование аккаунта
                        auth_ok = False
                        if row_data:
                            db_pwd = row_data[2]
                            if db.check_password(pwd_in, db_pwd):
                                auth_ok = True
                                # Миграция: если пароль хранился открытым текстом
                                if db_pwd == pwd_in:
                                    db.update_field(r_num, 3, db.hash_password(pwd_in))

                        if auth_ok:
                            st.session_state.login_attempts = 0
                            st.session_state.login_blocked_until = None
                            cookie_manager.set("mukti_user", make_session_token(email_in), expires_at=datetime.now() + timedelta(days=30))
                            load_user_to_session(email_in)
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.session_state.login_attempts += 1
                            time.sleep(0.7)  # замедляем перебор
                            if st.session_state.login_attempts >= 5:
                                st.session_state.login_blocked_until = datetime.now() + timedelta(minutes=10)
                                st.error("Слишком много попыт��к. Доступ заблокирован на 10 минут.")
                            else:
                                attempts_left = 5 - st.session_state.login_attempts
                                st.error(f"Неверный Email или Пароль. Осталось попыток: {attempts_left}")
                    else:
                        st.warning("Введи данные.")

    with tab2:
        with st.form("reg_form"):
            new_email = st.text_input("Email (Твой ID в системе)").strip().lower()
            new_user = st.text_input("Придумай Имя Аватара").strip()
            new_pwd = st.text_input("Придумай Пароль", type="password").strip()
            
            if st.form_submit_button("СОЗДАТЬ ПРОФИЛЬ"):
                if not new_email or "@" not in new_email:
                    st.error("Введи корректный Email.")
                elif len(new_pwd) < 8: # Усиление безопасности: минимум 8 символов
                    st.error("Пароль должен быть не короче 8 символов.")
                elif new_user:
                    # Убрали hash_password(). База данных сама захеширует чистый пароль.
                    res = db.register_user(new_email, new_user, new_pwd)
                    if res == "OK":
                        # --- НОВЫЙ БЛОК: Отправка письма верификации ---
                        v_token = get_verify_token(new_email)
                        v_url = f"https://mukti.pro/?verify={new_email}&token={v_token}"
                        subj = "Добро пожаловать в МУКТИ! Подтверди доступ"
                        body = f"{new_user}, твой профиль в системе МУКТИ успешно создан.\n\nЧтобы закрепить терминал за собой и иметь возможность получить Полный доступ (VIP), подтверди свой Email, перейдя по ссылке:\n{v_url}\n\nАрхитектор."
                        send_email(new_email, subj, body)
                        # ------------------------------------------------
                        
                        cookie_manager.set("mukti_user", make_session_token(new_email), expires_at=datetime.now() + timedelta(days=30))
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
                    row_data, r_num = db.load_user(rec_email)
                    if row_data:
                        new_temp_pwd = generate_temp_password()
                        db.update_field(r_num, 3, db.hash_password(new_temp_pwd))
                        
                        subject = "МУКТИ: Доступ к системе"
                        body = f"Приветствую, {row_data[1]}.\n\nТвой новый временный пароль для доступа в систему: {new_temp_pwd}\n\nСразу после входа рекомендую сохранить его в надежном месте.\nАрхитектор."
                        res = send_email(rec_email, subject, body)
                        if res == "OK": st.success("Письмо с паролем отправлено! Проверь почту (и папку Спам).")
                        else: st.error(f"Сбой отправки: {res}")
                    else: st.success("Если этот Email зарегистрирован — письмо отправлено. Проверь почту.")
                    
    # ЮРИДИЧЕСКИЕ ССЫЛКИ
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 13px; color: #888; margin-top: 15px;'>Продолжая, ты соглашаешься с <br><a href='https://disk.yandex.ru/i/dWaWRwOfdVFtFQ' target='_blank' style='color: #B8973A; text-decoration: none;'>Политикой конфиденциальности</a> и <a href='https://disk.yandex.ru/i/RBnom-qhT8KVhA' target='_blank' style='color: #B8973A; text-decoration: none;'>Публичной офертой</a>.</p>", unsafe_allow_html=True)

# ==========================================
# ПАНЕЛЬ АРХИТЕКТОРА (ЭКСКЛЮЗИВ ДЛЯ АДМИНА)
# ==========================================
elif st.session_state.user_email in ADMIN_EMAILS:
    st.markdown("<h2 style='text-align: center; color: #B8973A;'>🛠 ТЕРМИНАЛ АРХИТЕКТОРА</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    with st.spinner("Загрузка данных Матрицы..."):
        all_users = db.get_all_users()
    
    total_users = 0
    vip_users = 0
    active_3_days = 0
    table_data = []
    
    today_date = date.today()
    
    for u in all_users:
        r_num, u_email, u_name, p_json = u
        if u_email in ADMIN_EMAILS or u_email == YANDEX_EMAIL: continue 
        
        total_users += 1
        try: prof = json.loads(p_json) if p_json else {}
        except: prof = {}
        
        # --- ИСПРАВЛЕНИЕ: Берем VIP сразу из профиля, БЕЗ дополнительных запросов к БД ---
        is_vip = prof.get("is_vip", False)
            
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
    
# Мы убрали col_mail, так как рассылку из UI делать нельзя (она теперь работает в фоне)
    st.markdown("### Выдача VIP-доступа")
    with st.form("vip_form"):
        target_email = st.text_input("Введи Email для активации VIP").strip().lower()
        if st.form_submit_button("АКТИВИРОВАТЬ VIP"):
            row, r_num = db.load_user(target_email)
            if row:
                try:
                    db.update_field(r_num, 8, "TRUE") 
                    prof = json.loads(row[5]) if len(row)>5 and row[5] else {}
                    prof["is_vip"] = True
                    
                    # Устанавливаем счетчик ровно на 61 визит (активный день)
                    prof["vip_days_remaining"] = 61
                    
                    db.update_field(r_num, 6, json.dumps(prof)) 
                    
                    # --- ОТПРАВКА ПИСЬМА АВАТАРУ ---
                    user_name = row[1]
                    subj_vip = "МУКТИ: Полный доступ (VIP) успешно активирован 🟢"
                    body_vip = f"""Приветствую, {user_name}! На связи Архитектор.

Твой перевод подтвержден. Я вручную снял базовые ограничения с твоего профиля. Полный доступ (VIP) успешно активирован.

Что изменилось в твоем терминале прямо сейчас:
🟢 Резерв энергии увеличен: теперь тебе доступно до 20 сообщений в день. Этого хватит для самых глубоких разборов с ИИ-Наставником.
🟢 Непрерывность: ты можешь проходить программу каждый день без искусственных пауз. Впереди 61 активный день — таймер тикает только тогда, когда ты заходишь в систему.
🟢 Твой статус в Панели Управления изменился на «🌟 VIP».

Матрица обновлена и готова к работе. Твой Наставник уже ждет тебя в чате. Не теряй времени — заходи и продолжай перепрошивку.

Терминал: https://mukti.pro

До связи. 
Архитектор проекта МУКТИ."""
                    
                    # Посылаем сигнал через открытый порт 587
                    res_mail = send_email(target_email, subj_vip, body_vip)
                    
                    if res_mail == "OK":
                        st.success(f"Доступ VIP активирован для {target_email}! Письмо успешно отправлено.")
                    else:
                        st.warning(f"Доступ выдан, но письмо не ушло. Ошибка: {res_mail}")
                        
                except Exception as e:
                    st.error(f"Ошибка БД: {e}")
            else:
                st.error("Аватар с таким Email не найден.")

    st.markdown("### Протокол рассылки")
    st.markdown("Автоматическая проверка базы и отправка писем (3, 7, 14 дней).")
    if st.button("ЗАПУСТИТЬ РАССЫЛКУ", type="primary", use_container_width=True):
        with st.spinner("Сбор данных и отправка писем..."):
            sent_count = 0
            for u in all_users:
                r_num, u_email, u_name, p_json = u
                if u_email in ADMIN_EMAILS or u_email == YANDEX_EMAIL: continue
                
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
                
                unsub_token = get_unsubscribe_token(u_email)
                unsub_url = f"https://mukti.pro/?unsubscribe_token={unsub_token}"
                
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
                    res = send_email(u_email, subj, body)
                    if res == "OK":
                        reminders_sent.append(rem_type)
                        prof["reminders_sent"] = reminders_sent
                        db.update_field(r_num, 6, json.dumps(prof)) 
                        sent_count += 1
                        time.sleep(1) 
                        
            st.success(f"Рассылка завершена. Писем отправлено: {sent_count}")

    st.markdown("---")
    st.markdown("### 👥 База Аватаров (CRM)")
    if table_data:
        st.dataframe(table_data, use_container_width=True)
    else:
        st.info("Матрица пока пуста. Ожидаем первых Аватаров.")
        
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("ВЫЙТИ ИЗ ТЕРМИНАЛА АРХИТЕКТОРА", use_container_width=True):
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
        st.markdown(f"<div style='border: 2px solid #B8973A; padding: 20px; border-radius: 10px; background: rgba(184, 151, 58, 0.05);'>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='color: #B8973A;'>ПОСЛАНИЕ НА ДЕНЬ</h3>", unsafe_allow_html=True)
        st.markdown(message_text)
        st.markdown("</div><br>", unsafe_allow_html=True)
        
        if st.button("ДАННЫЕ ОСОЗНАЛ (ОТКРЫТЬ ТЕРМИНАЛ)", use_container_width=True):
            st.session_state.user_profile["msg_day"] = next_day
            st.session_state.user_profile["last_msg_date"] = get_mukti_date()
            st.session_state.user_profile["last_active"] = str(date.today())
            
            # --- ИСПОЛЬЗУЕМ ПАКЕТНОЕ СОХРАНЕНИЕ ---
            if hasattr(db, "update_profile_batch"):
                db.update_profile_batch(st.session_state.row_num, {
                    "msg_day": next_day,
                    "last_msg_date": get_mukti_date(),
                    "last_active": str(date.today())
                })
            else:
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
    if st.session_state.is_vip:
        # Показываем остаток дней, по умолчанию 61
        v_left = st.session_state.user_profile.get("vip_days_remaining", 61)
        status_text = f"🌟 VIP (Осталось визитов: {v_left})"
    else:
        status_text = "🟢 Базовый (День 1)" if is_day_one else "🔵 Базовый"
    
    # --- ПОСТОЯННАЯ ПАНЕЛЬ УПРАВЛЕНИЯ ---
    energy_pct = int((msgs_today / current_limit) * 100) if current_limit > 0 else 0
    vip_html = '<span class="vip-badge">VIP</span>' if st.session_state.is_vip else ''
    status_short = "Активен" if st.session_state.is_vip else ("День 1" if is_day_one else "Базовый")

    st.markdown(f"""
<div class="control-bar">
<div class="control-bar-header">
<span style="color:#B8973A; font-size:10px;">●</span>
<span class="cb-username">{st.session_state.username}</span>
{vip_html}
</div>
<div class="cb-stats">
<div><div class="cb-stat-label">День пути</div><div class="cb-stat-value">{msg_day}<span> / 61</span></div></div>
<div><div class="cb-stat-label">Энергия</div><div class="cb-stat-value">{msgs_today}<span> / {current_limit}</span></div></div>
<div><div class="cb-stat-label">Статус</div><div class="cb-stat-status">{status_short}</div></div>
</div>
<div class="energy-bar-wrap">
<div class="energy-bar-header"><span>Резерв на сегодня</span><span>{msgs_today} из {current_limit} использовано</span></div>
<div class="energy-bar-track"><div class="energy-bar-fill" style="width:{energy_pct}%"></div></div>
</div>
</div>
""", unsafe_allow_html=True)

    col_nav1, col_nav2, col_nav3 = st.columns(3)
    with col_nav1:
        if st.button("ТЕРМИНАЛ", use_container_width=True):
            st.session_state.current_view = "chat"
            st.rerun()
    with col_nav2:
        if st.button("ЗАБОТА", use_container_width=True):
            st.session_state.current_view = "care"
            st.rerun()
    with col_nav3:
        if st.button("ВЫХОД", use_container_width=True):
            try: cookie_manager.delete("mukti_user")
            except: pass
            st.session_state.logged_in = False
            time.sleep(0.5)
            st.rerun()

# ВЬЮ: ОТДЕЛ ЗАБОТЫ
    if st.session_state.current_view == "care":
        st.markdown("<h2 style='text-align: center; color: #B8973A;'>ОТДЕЛ ЗАБОТЫ</h2>", unsafe_allow_html=True)
        
        is_verified = st.session_state.user_profile.get("email_verified", False)
        
        # Если почта НЕ подтверждена - блокируем форму и даем кнопку повторной отправки
        if not is_verified:
            st.warning("Для связи с Архитектором и запроса Полного доступа (VIP) необходимо подтвердить Email.")
            if st.button("Отправить письмо подтверждения еще раз"):
                with st.spinner("Формируем канал связи..."):
                    v_token = get_verify_token(st.session_state.user_email)
                    v_url = f"https://mukti.pro/?verify={st.session_state.user_email}&token={v_token}"
                    subj = "МУКТИ: Повторная отправка ссылки"
                    body = f"Приветствую, {st.session_state.username}.\n\nСсылка для подтверждения твоего терминала:\n{v_url}\n\nАрхитектор."
                    res_m = send_email(st.session_state.user_email, subj, body)
                    if res_m == "OK": st.success("Письмо отправлено! Проверь почту (и папку Спам).")
                    else: st.error("Ошибка отправки почты.")
        
        # Если почта подтверждена - показываем стандартную форму
        else:
            st.markdown("Здесь ты можешь задать вопрос Архитектору, сообщить об ошибке или запросить **Полный доступ (VIP)**.")
            
            default_text = ""
            if not st.session_state.is_vip:
                default_text = "Привет, Архитектор!\n\nЯ прошел(а) первый день калибровки и готов(а) двигаться дальше.\n\nПрошу открыть мне Полный доступ (VIP)."
                
            with st.form("care_form"):
                user_msg = st.text_area("Твое сообщение:", value=default_text, height=150)
                submit_care = st.form_submit_button("ОТПРАВИТЬ АРХИТЕКТОРУ")
                
                if submit_care:
                    if user_msg.strip():
                        # Добавляем индикатор загрузки, чтобы кнопка не казалась "мертвой"
                        with st.spinner("Установка защищенного канала связи и передача данных..."):
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
Полная стоимость подписки составляет 1990 рублей. Но так как ты являешься ранним участником (бета-тестером), для тебя действует специальная цена - всего 1220 рублей (это ровно 20 рублей в день за твою свободу).

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
                                st.error(f"Сбой связи: {res_admin}")
                    else: 
                        st.warning("Напиши текст сообщения.")

# ВЬЮ: ЧАТ
    else:
        # --- 1) РЕНДЕРИМ ТОЛЬКО ПОСЛЕДНИЕ N СООБЩЕНИЙ ---
        MAX_RENDERED = 40  # поменяй на 30 или 50 при желании
        msgs_to_render = st.session_state.messages[-MAX_RENDERED:]

        for msg in msgs_to_render:
            if msg.get("role") != "system":
                av = BOT_AVATAR if msg["role"] == "assistant" else USER_AVATAR
                with st.chat_message(msg["role"], avatar=av):
                    st.markdown(msg.get("content", ""))

    # --- 2) ЕСЛИ ЕСТЬ ОЖИДАЮЩИЙ ПРОМПТ -> ГЕНЕРИМ ОТВЕТ В ОТДЕЛЬНОМ ПРОГОНЕ ---
    if st.session_state.pending_prompt:
        pending = st.session_state.pending_prompt

        with st.chat_message("assistant", avatar=BOT_AVATAR):
            placeholder = st.empty()
            placeholder.markdown("_Оцифровка мыслей…_")

            try:
                sys_prompt = settings.get_system_prompt(
                    st.session_state.username,
                    st.session_state.user_profile,
                    get_book_summary()
                )

                history_text = build_history_text(st.session_state.messages, last_n=6, max_chars_per_msg=1200)
                full_p = f"{sys_prompt}\n\nИстория последних сообщений:\n{history_text}\n\nUser: {pending}"

                response = ai_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=full_p,
                    config={"thinking_config": {"thinking_budget": 0}}
                )

                txt = (response.text or "").strip()
                if not txt:
                    txt = "Похоже, ответ пришёл пустым. Попробуй повторить запрос."

                placeholder.markdown(txt)

                st.session_state.messages.append({"role": "assistant", "content": txt})
                db.save_history(st.session_state.row_num, st.session_state.messages)

            except Exception as e:
                placeholder.markdown("**Сервер перегружен или временно недоступен.** Попробуй ещё раз через 10–20 секунд.")
                print(f"GenAI Error (pending): {e}")

            finally:
                st.session_state.pending_prompt = None

        st.rerun()

    # --- 3) ЛИМИТЫ (если энергии нет) ---
    if not can_send:
        if st.session_state.is_vip:
            st.markdown(
                "<div class='limit-alert' style='border-color: #B8973A;'><b>Нейронная сеть перегружена.</b><br>Система перейдет в спящий режим до завтра.</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                "<div class='limit-alert' style='border-color: #FF3D00;'><b>Энергия наставника исчерпана на сегодня.</b><br><i>Запроси Полный доступ (VIP), чтобы продолжить работу прямо сейчас.</i></div>",
                unsafe_allow_html=True
            )

            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("Написать в Отдел заботы (Запросить VIP)"):
                is_verified_chat = st.session_state.user_profile.get("email_verified", False)

                if not is_verified_chat:
                    st.warning("Для запроса Полного доступа необходимо подтвердить Email.")
                    if st.button("Отправить письмо подтверждения еще раз", key="resend_email_chat"):
                        with st.spinner("Формируем канал связи..."):
                            v_token = get_verify_token(st.session_state.user_email)
                            v_url = f"https://mukti.pro/?verify={st.session_state.user_email}&token={v_token}"
                            subj = "МУКТИ: Повторная отправка ссылки"
                            body = f"Приветствую, {st.session_state.username}.\n\nСсылка для подтверждения твоего терминала:\n{v_url}\n\nАрхитектор."
                            res_m = send_email(st.session_state.user_email, subj, body)
                            if res_m == "OK":
                                st.success("Письмо отправлено! Проверь почту (и папку Спам).")
                            else:
                                st.error("Ошибка отправки почты.")
                else:
                    st.write("Запроси полный доступ, чтобы снять лимиты сообщений и продолжить работу прямо сейчас.")

                    vip_template = (
                        "Привет, Архитектор!\n\n"
                        "Я прошел(а) первый день калибровки и готов(а) двигаться дальше.\n\n"
                        "Прошу открыть мне Полный доступ (VIP)."
                    )

                    with st.form("vip_request_form_chat"):
                        user_comment = st.text_area(
                            "Комментарий для Архитектора (по желанию):",
                            value=vip_template,
                            height=150
                        )

                        submit_vip = st.form_submit_button("Отправить запрос")

                        if submit_vip:
                            if user_comment.strip():
                                user_email = st.session_state.user_email
                                subj_admin = f"НОВЫЙ ЗАПРОС НА VIP от {user_email}"
                                body_admin = f"Пользователь: {user_email}\nЗапрашивает VIP-доступ.\n\nКомментарий:\n{user_comment}"

                                res = send_email(YANDEX_EMAIL, subj_admin, body_admin)

                                if res == "OK":
                                    subj_user = "МУКТИ: Активация Полного доступа (VIP)"
                                    body_user = f"""Приветствую, {st.session_state.username}! На связи Роман - Архитектор проекта МУКТИ.

В данный момент система МУКТИ находится в стадии закрытого бета-тестирования (MVP), поэтому шлюзы оплаты еще не автоматизированы, и я активирую профили пользователей вручную.

Что ты получишь, перейдя в режим VIP (Полный доступ):
🟢 Расширенный резерв энергии: до 20 глубоких диалогов с ИИ-наставником каждый день.
🟢 Персональная аналитика: Матрица будет лучше запоминать твои слабости и превентивно блокировать атаки Гостя.
🟢 Непрерывность: Полный доступ ровно на 61 день - именно столько нужно для глубокой перепрошивки нейронных связей.
🟢 Прямая поддержка: Приоритетная связь со мной (Архитектором) через Отдел Заботы.

Стоимость и оплата:
Полная стоимость подписки составляет 1990 рублей. Но так как ты являешься ранним участником (бета-тестером), для тебя действует специальная цена - всего 1220 рублей.

Как активировать доступ прямо сейчас:
1. Сделай перевод 1220 рублей по номеру: +7 (905) 294-52-45 (Сбербанк, Роман В).
2. Пришли скриншот чека ответным письмом на это сообщение.

В течение нескольких часов я вручную активирую твой VIP-статус.

С уважением Роман, Архитектор проекта МУКТИ"""
                                    send_email(user_email, subj_user, body_user)

                                    st.success("Запрос отправлен! Проверь свою почту (и папку Спам) — туда ушла инструкция по активации.")
                                else:
                                    st.error(f"Сбой связи с сервером. Ошибка: {res}")
                            else:
                                st.warning("Текст сообщения не может быть пустым.")

        # --- 4) ВВОД СООБЩЕНИЯ ---
    if can_send and not st.session_state.pending_prompt:
        prompt = st.chat_input("Написать наставнику...")

        if prompt:
            msgs_today += 1
            db.update_field(st.session_state.row_num, 4, msgs_today)

            with st.chat_message("user", avatar=USER_AVATAR):
                st.markdown(prompt)

            st.session_state.messages.append({"role": "user", "content": prompt})

            step = st.session_state.calibration_step

            # === РЕЖИМ КАЛИБРОВКИ (без AI, ответы заготовлены) ===
            if step > 0:
                sober_words = ["не пью", "бросил", "завязал", "трезв", "не употребляю", "давно свободен"]
                if any(word in prompt.lower() for word in sober_words):
                    db.update_profile(st.session_state.row_num, "history", "Уже не пьет: " + prompt)
                    st.session_state.user_profile["history"] = "Уже не пьет: " + prompt
                    resp = "Понял тебя. Ты уже вышел из системы — это отличный результат. В таком случае моя задача меняется: я буду помогать тебе отслеживать скрытые (фоновые) триггеры, защищать от откатов и развивать осознанность.\n\nПрофиль обновлен. Калибровка завершена.\n\n**Расскажи, как прошел твой день сегодня?**"
                    st.session_state.calibration_step = 0
                else:
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

                with st.chat_message("assistant", avatar=BOT_AVATAR):
                    st.markdown(resp)
                st.session_state.messages.append({"role": "assistant", "content": resp})
                db.save_history(st.session_state.row_num, st.session_state.messages)

                if st.session_state.calibration_step == 0:
                    st.session_state.reading_message = True
                    time.sleep(1.5)
                    st.rerun()

            # === СТАНДАРТНЫЙ РЕЖИМ — через pending_prompt (AI) ===
            else:
                easter_eggs = ["хочу выпить", "пиво", "накатить", "срыв"]
                if any(word in prompt.lower() for word in easter_eggs):
                    resp = random.choice([
                        "**ВНИМАНИЕ! ОБНАРУЖЕНА АКТИВНОСТЬ ГОСТЯ.** \nЭто не твои мысли. Сделай 10 глубоких вдохов. Ты сильнее программы.",
                        "Активирован защитный протокол. Напоминаю: алкоголь забирает у тебя завтрашний день, чтобы дать в долг сегодня под бешеные проценты."
                    ])
                    with st.chat_message("assistant", avatar=BOT_AVATAR):
                        st.markdown(resp)
                    st.session_state.messages.append({"role": "assistant", "content": resp})
                    db.save_history(st.session_state.row_num, st.session_state.messages)
                else:
                    # Отправляем в AI через pending_prompt
                    db.save_history(st.session_state.row_num, st.session_state.messages)
                    st.session_state.pending_prompt = prompt
                    st.rerun()
