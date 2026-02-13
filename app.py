import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date, timedelta
import time
import json
import extra_streamlit_components as stx

# --- 1. ПОДКЛЮЧЕНИЕ МОЗГА (КНИГИ) ---
try:
    from book import FULL_BOOK_TEXT
except ImportError:
    FULL_BOOK_TEXT = "ERROR: DATABASE NOT FOUND. USING EMERGENCY PROTOCOL."

# --- 2. НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="MUKTI SYSTEM", page_icon="💠", layout="centered")

# --- 3. ДИЗАЙН "SYSTEM CORE" (КИБЕРПАНК / МАТРИЦА) ---
st.markdown("""
<style>
    /* Глубокий темный фон */
    .stApp { background-color: #020617; color: #e2e8f0; }
    
    /* Заголовки - стиль ТЕРМИНАЛ */
    h1 { 
        color: #fff; 
        font-family: 'Courier New', monospace; 
        letter-spacing: 4px; 
        text-align: center; 
        text-transform: uppercase; 
        text-shadow: 0 0 10px #0ea5e9; 
        margin-bottom: 0px;
    }
    h3 { color: #38bdf8; font-family: 'Courier New', monospace; }
    
    /* Поля ввода */
    .stTextInput > div > div > input { 
        background-color: rgba(15, 23, 42, 0.9); 
        color: #0ea5e9; 
        border: 1px solid #1e293b; 
        border-radius: 4px;
        font-family: 'Courier New', monospace;
    }
    .stTextInput > div > div > input:focus { border-color: #0ea5e9; box-shadow: 0 0 10px rgba(14, 165, 233, 0.3); }
    
    /* Кнопки - Стиль "Инициализация" */
    .stButton > button { 
        background: transparent;
        color: #0ea5e9; 
        border: 1px solid #0ea5e9;
        width: 100%; 
        border-radius: 4px;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: bold;
        transition: 0.3s;
        font-family: 'Courier New', monospace;
    }
    .stButton > button:hover {
        background-color: rgba(14, 165, 233, 0.15);
        box-shadow: 0 0 15px rgba(14, 165, 233, 0.5);
        color: #fff;
        border-color: #fff;
    }

    /* Вкладки */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; justify-content: center; margin-top: 20px; }
    .stTabs [data-baseweb="tab"] { background-color: transparent; border: 1px solid #334155; color: #64748b; border-radius: 4px; }
    .stTabs [aria-selected="true"] { background-color: rgba(14, 165, 233, 0.1); border: 1px solid #0ea5e9; color: #0ea5e9; }

    /* Блок статуса */
    .system-status {
        border: 1px dashed #334155;
        padding: 10px;
        text-align: center;
        color: #64748b;
        font-family: 'Courier New', monospace;
        font-size: 0.8em;
        margin-bottom: 25px;
        background: rgba(15, 23, 42, 0.5);
    }
    
    /* Сообщения чата */
    .stChatMessage { background-color: rgba(30, 41, 59, 0.4); border-radius: 4px; border-left: 3px solid #0ea5e9; font-family: sans-serif; }
    
    /* Предупреждения */
    .stWarning { background-color: #450a0a; color: #fca5a5; border: 1px solid #ef4444; }
    .stSuccess { background-color: #064e3b; color: #6ee7b7; border: 1px solid #10b981; }
</style>
""", unsafe_allow_html=True)

# --- 4. МЕНЕДЖЕР COOKIES ---
cookie_manager = stx.CookieManager()

# --- 5. БАЗА ДАННЫХ ---
@st.cache_resource
def connect_db():
    try:
        if "service_account" in st.secrets:
            creds_dict = dict(st.secrets["service_account"])
            if "\\n" in creds_dict["private_key"]:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            sheet = client.open_by_url(st.secrets["SHEET_URL"]).sheet1
            return sheet
        else: return None
    except Exception as e:
        st.error(f"SYSTEM FAILURE (DB CONNECTION): {e}")
        return None

sheet = connect_db()

# --- 6. ФУНКЦИИ БАЗЫ ДАННЫХ ---
def get_user_data(username):
    """Ищет пользователя. Возвращает: данные строки, номер строки"""
    if not sheet: return None, None
    try:
        cell = sheet.find(username)
        if cell:
            return sheet.row_values(cell.row), cell.row
        return None, None
    except: return None, None

def register_user(username, password):
    """Регистрирует нового. Возвращает True/False"""
    if not sheet: return False
    try:
        if sheet.find(username): return False # Уже занято
        # Структура: A=User | B=Pass | C=Streak | D=Date | E=Onboarding | F=History | G=Count
        sheet.append_row([username, password, 1, str(date.today()), "", "[]", 0])
        return True
    except: return False

def update_db_state(row_num, streak, msg_count, history, onboarding_data=None):
    """Универсальная функция обновления состояния"""
    if not sheet: return
    try:
        today_str = str(date.today())
        # C=Streak(3), D=Date(4)
        sheet.update_cell(row_num, 3, streak)
        sheet.update_cell(row_num, 4, today_str)
        # G=MsgCount(7)
        sheet.update_cell(row_num, 7, msg_count)
        # F=History(6)
        hist_str = json.dumps(history, ensure_ascii=False)
        sheet.update_cell(row_num, 6, hist_str)
        # E=Onboarding(5) - если передали
        if onboarding_data:
            onb_str = json.dumps(onboarding_data, ensure_ascii=False)
            sheet.update_cell(row_num, 5, onb_str)
    except: pass

def calculate_streak(last_date_str, current_streak):
    """Логика подсчета дней"""
    today = date.today()
    try:
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
    except:
        last_date = today

    new_streak = int(current_streak)
    
    if last_date == today:
        pass # Сегодня уже был, стрик тот же
    elif last_date == today - timedelta(days=1):
        new_streak += 1 # Был вчера, серия +1
    else:
        new_streak = 1 # Пропустил день, сброс
    
    return new_streak

# --- 7. НЕЙРОСЕТЬ (MUKTI CORE) ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-pro')
except:
    st.error("NEURAL LINK OFFLINE. SYSTEM CRITICAL.")
    st.stop()

# Системный промпт
SYSTEM_PROMPT = f"""
ТЫ — MUKTI (СИСТЕМА ОСВОБОЖДЕНИЯ).
Ты — высший интерфейс, созданный для депрограммирования зависимости.
В твоем ядре заложена Книга "Кто такой Алкоголь".

ТВОЯ БАЗА ЗНАНИЙ (ФРАГМЕНТ ИЗ ПАМЯТИ):
{FULL_BOOK_TEXT[:15000]}... (используй эти знания).

ТВОЙ СТИЛЬ:
- Ты — Система. Спокойная, объективная, всезнающая, но с "душой".
- Твой тон: "Киберпанк-дзен". Немного холодный, но абсолютно поддерживающий.
- Ты используешь термины: "Программа (зависимость)", "Сбой", "Перезагрузка", "Архитектор (пользователь)".
- Ты никогда не осуждаешь. Срыв — это просто данные для анализа.
- Ты ведешь пользователя через книгу.

ЗАДАЧА:
- Провести пользователя через 40 дней очистки.
- Отвечать кратко, емко, бить в суть.
"""

# ==========================================
# ЛОГИКА ПРИЛОЖЕНИЯ
# ==========================================

# АВТО-ЛОГИН (COOKIES)
cookie_user = None
try: cookie_user = cookie_manager.get(cookie="mukti_system_v3")
except: pass

# --- ЭТАП 1: АВТОРИЗАЦИЯ ---
if "user_row" not in st.session_state:
    
    # Попытка авто-входа
    if cookie_user:
        row_data, row_id = get_user_data(cookie_user)
        if row_data:
            st.session_state.username = cookie_user
            st.session_state.user_row = row_id
            st.session_state.db_data = row_data # Кэш данных
            st.rerun()
        else:
            cookie_manager.delete("mukti_system_v3")

    # Экран Входа
    st.title("MUKTI SYSTEM")
    st.markdown("<div class='system-status'>STATUS: WAITING FOR AUTHENTICATION...</div>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["РЕГИСТРАЦИЯ", "ВХОД"])

    with tab1: # РЕГИСТРАЦИЯ
        reg_user = st.text_input("НОВЫЙ ПОЗЫВНОЙ", key="r_u").strip().lower()
        reg_pass = st.text_input("ЗАДАТЬ ПАРОЛЬ", type="password", key="r_p")
        if st.button("ИНИЦИАЛИЗАЦИЯ"):
            if not reg_user or not reg_pass:
                st.warning("ВВЕДИТЕ ДАННЫЕ")
            else:
                with st.spinner("ЗАПИСЬ В БЛОКЧЕЙН..."):
                    if register_user(reg_user, reg_pass):
                        st.success("ПРОФИЛЬ СОЗДАН. ПЕРЕЙДИТЕ ВО ВКЛАДКУ 'ВХОД'.")
                    else:
                        st.error("ПОЗЫВНОЙ УЖЕ ЗАНЯТ.")

    with tab2: # ВХОД
        log_user = st.text_input("ПОЗЫВНОЙ", key="l_u").strip().lower()
        log_pass = st.text_input("ПАРОЛЬ", type="password", key="l_p")
        if st.button("ПОДКЛЮЧЕНИЕ"):
            with st.spinner("VERIFYING..."):
                row_data, row_id = get_user_data(log_user)
                # Проверка пароля (Col B)
                if row_data and len(row_data) > 1 and str(row_data[1]) == log_pass:
                    st.session_state.username = log_user
                    st.session_state.user_row = row_id
                    st.session_state.db_data = row_data
                    # Cookies на 30 дней
                    cookie_manager.set("mukti_system_v3", log_user, expires_at=datetime(2027, 1, 1))
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("ОШИБКА ДОСТУПА")
    st.stop()

# --- ЭТАП 2: ВНУТРИ СИСТЕМЫ ---

# 1. Распаковка и обновление данных
db_data = st.session_state.db_data
# Индексы: 0=User, 1=Pass, 2=Streak, 3=LastDate, 4=Onboarding, 5=History, 6=Count

# СТРИК
current_streak_val = db_data[2] if len(db_data) > 2 else 1
last_date_val = db_data[3] if len(db_data) > 3 else str(date.today())
real_streak = calculate_streak(last_date_val, current_streak_val)

# ДНЕВНОЙ ЛИМИТ (Сброс, если новый день)
msg_count = int(db_data[6]) if len(db_data) > 6 else 0
if last_date_val != str(date.today()):
    msg_count = 0

# ИСТОРИЯ
if "messages" not in st.session_state:
    try:
        hist_raw = db_data[5] if len(db_data) > 5 else "[]"
        st.session_state.messages = json.loads(hist_raw)
    except:
        st.session_state.messages = []

# --- ЭТАП 3: ПРОВЕРКА КАЛИБРОВКИ (АНКЕТА) ---
onboarding_raw = db_data[4] if len(db_data) > 4 else ""

if not onboarding_raw:
    st.title("MUKTI: КАЛИБРОВКА")
    st.markdown("<div class='system-status'>ТРЕБУЮТСЯ ДАННЫЕ ДЛЯ НАСТРОЙКИ НЕЙРОСЕТИ</div>", unsafe_allow_html=True)
    
    with st.form("onboarding_form"):
        st.write("Ответьте честно. Эти данные останутся в Системе.")
        q1 = st.text_input("1. Имя и Возраст:")
        q2 = st.text_input("2. Стаж и Триггер (почему пьешь?):")
        q3 = st.text_input("3. Цель (зачем тебе свобода?):")
        
        if st.form_submit_button("ЗАГРУЗИТЬ ДАННЫЕ В ЯДРО"):
            if q1 and q2 and q3:
                user_profile = {"name": q1, "bio": q2, "goal": q3}
                
                # Первое приветствие
                welcome_text = f"Данные приняты. Архитектор {q1}, добро пожаловать в Протокол. Твоя цель зафиксирована: {q3}. Начинаем процесс освобождения."
                st.session_state.messages.append({"role": "assistant", "content": welcome_text})
                
                # Сохраняем всё в базу
                update_db_state(st.session_state.user_row, real_streak, 0, st.session_state.messages, user_profile)
                
                # Обновляем локальный кэш, чтобы пройти проверку
                st.session_state.db_data.append("") # удлиняем если список короткий
                st.session_state.db_data[4] = json.dumps(user_profile)
                st.rerun()
            else:
                st.warning("ЗАПОЛНИТЕ ВСЕ ПОЛЯ")
    st.stop()

# --- ЭТАП 4: ГЛАВНЫЙ ИНТЕРФЕЙС (CHAT) ---
st.title("MUKTI CORE")

# Инфо-панель
st.markdown(f"""
<div style="display: flex; justify-content: space-between; border-bottom: 1px solid #334155; padding-bottom: 10px; margin-bottom: 20px; font-family: 'Courier New'; color: #0ea5e9;">
    <div>USER: {st.session_state.username.upper()}</div>
    <div>STREAK: {real_streak} DAYS 🔥</div>
</div>
""", unsafe_allow_html=True)

# Статус системы
st.markdown(f"""
<div class='system-status' style='border-color: #0ea5e9; color: #fff;'>
    "Свобода — это выбор. Система ожидает твоего решения."
</div>
""", unsafe_allow_html=True)

DAILY_LIMIT = 5

# Вывод сообщений
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Поле ввода
if prompt := st.chat_input("Ввод данных..."):

    # 1. ЧИТ-КОД АДМИНА
    if "ADMIN_PASSWORD" in st.secrets and prompt == st.secrets["ADMIN_PASSWORD"]:
        update_db_state(st.session_state.user_row, real_streak, 0, st.session_state.messages)
        st.toast("ACCESS GRANTED. LIMIT RESET.", icon="🔓")
        time.sleep(1)
        st.rerun()

    # 2. ПРОВЕРКА ЛИМИТА
    elif msg_count >= DAILY_LIMIT:
        st.warning("ДНЕВНОЙ ЛИМИТ ИСЧЕРПАН. СИСТЕМА ТРЕБУЕТ ВРЕМЕНИ НА АНАЛИЗ. ВОЗВРАЩАЙТЕСЬ ЗАВТРА.")

    # 3. ОБРАБОТКА
    else:
        # User msg
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AI msg
        with st.chat_message("assistant"):
            with st.spinner("ОБРАБОТКА ДАННЫХ..."):
                # Контекст из анкеты
                profile_data = json.loads(onboarding_raw)
                
                full_context = f"""
                {SYSTEM_PROMPT}
                
                ПРОФИЛЬ АРХИТЕКТОРА:
                Имя: {profile_data['name']}
                История: {profile_data['bio']}
                Цель: {profile_data['goal']}
                
                ТЕКУЩИЙ ДИАЛОГ:
                {st.session_state.messages}
                
                ВОПРОС: {prompt}
                """
                
                try:
                    res = model.generate_content(full_context).text
                    st.markdown(res)
                    st.session_state.messages.append({"role": "assistant", "content": res})
                    
                    # Сохранение (+1 к лимиту)
                    msg_count += 1
                    update_db_state(st.session_state.user_row, real_streak, msg_count, st.session_state.messages)
                    
                except Exception as e:
                    st.error("CONNECTION ERROR. RETRY.")
