import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
import time
import json
import extra_streamlit_components as stx

# --- НАСТРОЙКИ ---
st.set_page_config(page_title="MUKTI", page_icon="🔥", layout="centered")
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #fff; }
    h1 { color: #facc15; }
    .stTextInput > div > div > input { background-color: #1f2937; color: #fff; }
    .stButton > button { background-color: #facc15; color: #000000; font-weight: bold; border: none; width: 100%; }
    .stWarning { background-color: #374151; color: #ffffff; border: 1px solid #facc15; }
    .quote-box {
        background-color: #1f2937; 
        padding: 15px; 
        border-radius: 8px; 
        border-left: 4px solid #facc15;
        margin-bottom: 20px;
        font-style: italic;
        color: #e5e7eb;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #1f2937; border-radius: 5px; color: #fff; }
    .stTabs [aria-selected="true"] { background-color: #facc15; color: #000; }
</style>
""", unsafe_allow_html=True)

# --- 1. ЦИТАТЫ ---
MUKTI_QUOTES = [
    "Свобода — это не когда тебе разрешили. Свобода — это когда ты не спрашиваешь.",
    "Паразит питается твоими эмоциями. Оставь его голодным сегодня.",
    "Трезвость — это не отказ. Это приобретение себя.",
    "Каждый раз, когда ты говоришь 'нет', ты становишься сильнее.",
    "Твоя энергия — это самая дорогая валюта в мире. Не трать её на яд.",
    "Боль — это просто слабость, покидающая тело. Терпи.",
    "40 дней тишины. Просто дай мозгу время вспомнить, как вырабатывать радость.",
    "Ты не бросаешь друга. Ты изгоняешь врага.",
    "Сегодня лучший день, чтобы быть свободным.",
    "Не верь мыслям 'всего один бокал'. Это голос Паразита.",
    "Сила воли — это мышца. Качай её сегодня.",
    "Посмотри в зеркало. Там стоит человек, который может всё.",
    "Алкоголь берет счастье завтрашнего дня в кредит под огромный процент.",
    "Будь холоден к соблазнам. Будь горяч к жизни.",
    "Твой мозг исцеляется прямо сейчас, пока ты читаешь это.",
]

def get_daily_quote():
    day_of_year = datetime.now().timetuple().tm_yday
    quote_index = day_of_year % len(MUKTI_QUOTES)
    return MUKTI_QUOTES[quote_index]

# --- 2. COOKIES ---
cookie_manager = stx.CookieManager()

# --- 3. БАЗА ДАННЫХ ---
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
        st.error(f"Ошибка подключения к БД: {e}")
        return None

sheet = connect_db()

# --- 4. ФУНКЦИИ ---
def get_user_data(username):
    if not sheet: return None, None
    try:
        cell = sheet.find(username)
        if cell:
            return sheet.row_values(cell.row), cell.row
        return None, None
    except: return None, None

def check_username_taken(username):
    if not sheet: return False
    try:
        cell = sheet.find(username)
        return True if cell else False
    except: return False

def update_db(row_num, count):
    if not sheet: return
    try:
        sheet.update_cell(row_num, 2, count)
        sheet.update_cell(row_num, 3, str(date.today()))
    except: pass

def create_user_strict(username):
    if not sheet: return False
    try:
        if check_username_taken(username):
            return False
        sheet.append_row([username, 0, str(date.today()), ""])
        return True
    except: return False

# --- 5. AI (MUKTI) ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except:
    st.error("Ошибка API ключа.")
    st.stop()

@st.cache_resource
def get_model():
    try:
        priority_models = ['models/gemini-1.5-pro', 'models/gemini-1.5-flash', 'models/gemini-pro']
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for p in priority_models:
            if p in available: return genai.GenerativeModel(p)
        return genai.GenerativeModel(available[0])
    except: return None

model = get_model()
if not model:
    st.error("Сервис AI перегружен. Попробуй позже.")
    st.stop()

SYSTEM_PROMPT = """
ТЫ — MUKTI. Ментор по книге "Кто такой Алкоголь".
Твои принципы:
1. Алкоголь — Паразит.
2. Безопасных доз нет.
3. Дофаминовая яма требует 40 дней.
4. Стиль: Жесткий, но любящий брат.
"""

# ==========================================
# 6. ЛОГИКА ВХОДА
# ==========================================

try: cookie_user = cookie_manager.get(cookie="mukti_user_id")
except: cookie_user = None

if "user_row" not in st.session_state:
    
    if cookie_user:
        with st.spinner(f"Вход как {cookie_user}..."):
            row_data, row_id = get_user_data(cookie_user)
            if row_data:
                st.session_state.username = cookie_user
                st.session_state.user_row = row_id
                if len(row_data) > 2 and row_data[2] != str(date.today()):
                    st.session_state.msg_count = 0 
                else:
                    st.session_state.msg_count = int(row_data[1]) if len(row_data) > 1 else 0
                st.session_state.messages = [{"role": "assistant", "content": f"⚡ С возвращением, {cookie_user}."}]
                st.rerun()
            else:
                try: cookie_manager.delete("mukti_user_id")
                except: pass

    st.title("🔥 MUKTI")
    st.write("Добро пожаловать в систему освобождения.")

    tab1, tab2 = st.tabs(["Я новенький", "У меня есть аккаунт"])

    with tab1:
        new_username = st.text_input("Придумай позывной (Ник):", key="new_user").strip().lower()
        if st.button("Начать путь"):
            if not new_username:
                st.warning("Введите имя.")
            else:
                with st.spinner("Проверка имени..."):
                    if check_username_taken(new_username):
                        st.error(f"🛑 Позывной '{new_username}' уже занят! Выбери другой.")
                    else:
                        success = create_user_strict(new_username)
                        if success:
                            st.session_state.username = new_username
                            st.session_state.msg_count = 0
                            st.session_state.user_row = len(sheet.get_all_values())
                            st.session_state.messages = [{"role": "assistant", "content": "Добро пожаловать. Я тебя запомнил."}]
                            cookie_manager.set("mukti_user_id", new_username, expires_at=datetime(2027, 1, 1))
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Ошибка базы данных.")

    with tab2:
        old_username = st.text_input("Твой позывной:", key="old_user").strip().lower()
        if st.button("Войти"):
            if not old_username:
                st.warning("Введите имя.")
            else:
                with st.spinner("Поиск..."):
                    row_data, row_id = get_user_data(old_username)
                    if row_data:
                        st.session_state.username = old_username
                        st.session_state.user_row = row_id
                        if len(row_data) > 2 and row_data[2] != str(date.today()):
                            st.session_state.msg_count = 0 
                        else:
                            st.session_state.msg_count = int(row_data[1]) if len(row_data) > 1 else 0
                        st.session_state.messages = [{"role": "assistant", "content": f"Рад видеть, {old_username}."}]
                        cookie_manager.set("mukti_user_id", old_username, expires_at=datetime(2027, 1, 1))
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Такого позывного нет.")
    st.stop()

# ==========================================
# 7. ЧАТ И ЛОГИКА "ЧИТ-КОДА"
# ==========================================

st.title(f"🔥 MUKTI | {st.session_state.username.upper()}")

daily_quote = get_daily_quote()
st.markdown(f"""
<div class="quote-box">
    💡 <b>Мысль дня:</b><br>
    "{daily_quote}"
</div>
""", unsafe_allow_html=True)

DAILY_LIMIT = 5

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- ПОЛЕ ВВОДА ВСЕГДА АКТИВНО ---
if prompt := st.chat_input("Сообщение..."):

    # 1. ПРОВЕРЯЕМ НА ЧИТ-КОД (СБРОС ЛИМИТА)
    if "ADMIN_PASSWORD" in st.secrets and prompt == st.secrets["ADMIN_PASSWORD"]:
        st.session_state.msg_count = 0
        update_db(st.session_state.user_row, 0)
        st.toast("🔓 РЕЖИМ БОГА: Лимит сброшен!", icon="😎")
        time.sleep(1)
        st.rerun()
    
    # 2. ЕСЛИ НЕ ЧИТ-КОД, ПРОВЕРЯЕМ ЛИМИТ
    elif st.session_state.msg_count >= DAILY_LIMIT:
        st.warning(f"🛑 Лимит ({DAILY_LIMIT}) исчерпан. Паразит любит пустые разговоры. Действуй. Возвращайся завтра.")
    
    # 3. ОБЫЧНОЕ ОБЩЕНИЕ
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("..."):
                full_prompt = f"{SYSTEM_PROMPT}\nИстория:\n{st.session_state.messages}\nЮзер: {prompt}"
                try:
                    res = model.generate_content(full_prompt).text
                    st.markdown(res)
                    st.session_state.messages.append({"role": "assistant", "content": res})
                    
                    st.session_state.msg_count += 1
                    update_db(st.session_state.user_row, st.session_state.msg_count)
                except Exception as e:
                    st.error("Сбой связи.")
