import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
import time
import json
import random

# --- 1. ПОДКЛЮЧЕНИЕ КНИГИ ---
try:
    from book import FULL_BOOK_TEXT, BOOK_SUMMARY
except ImportError:
    FULL_BOOK_TEXT = "Текст книги недоступен."
    BOOK_SUMMARY = "Философия освобождения от зависимости."

# --- 2. НАСТРОЙКИ ---
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"] if "GOOGLE_API_KEY" in st.secrets else "NO_KEY"
VIP_CODE = "MUKTI_BOSS"

genai.configure(api_key=GOOGLE_API_KEY)

# --- 2.1 УМНОЕ ПОДКЛЮЧЕНИЕ МОЗГОВ ---
@st.cache_resource
def get_model():
    try:
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority_models = ['models/gemini-1.5-pro', 'models/gemini-1.5-flash', 'models/gemini-pro']
        for p in priority_models:
            if p in available: return genai.GenerativeModel(p)
        if available: return genai.GenerativeModel(available[0])
    except: return None
    return None

model = get_model()
if not model:
    st.error("⚠️ СИСТЕМНЫЙ СБОЙ: Нейросеть недоступна.")
    st.stop()

# --- 3. ДИЗАЙН "DEEP SPACE" ---
st.set_page_config(page_title="MUKTI", page_icon="💠", layout="centered")

st.markdown("""
<style>
    .stApp {
        background-color: #020617;
        background-image: radial-gradient(circle at 50% 50%, #1e1b4b 0%, #020617 60%);
        color: #e2e8f0;
    }
    .stTextInput > div > div > input {
        background-color: #0f172a; 
        color: #0ea5e9; 
        border: 1px solid #1e293b;
    }
    .stButton > button {
        background: linear-gradient(90deg, #0ea5e9, #3b82f6);
        color: white;
        font-weight: bold;
        border: none;
        box-shadow: 0 0 10px rgba(14, 165, 233, 0.5);
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        box-shadow: 0 0 20px rgba(14, 165, 233, 0.8);
        transform: scale(1.02);
    }
    .sos-btn > button {
        background: linear-gradient(90deg, #ef4444, #dc2626) !important;
        color: white !important;
        animation: pulse 2s infinite;
    }
    .stChatMessage {
        background-color: rgba(30, 41, 59, 0.5);
        border-radius: 10px;
        border-left: 3px solid #0ea5e9;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. ФУНКЦИИ БАЗЫ ДАННЫХ ---
@st.cache_resource
def get_db():
    creds_dict = None
    if "gcp_service_account" in st.secrets:
        raw = st.secrets["gcp_service_account"]
        if hasattr(raw, "to_dict"): creds_dict = raw.to_dict()
        elif isinstance(raw, dict): creds_dict = raw
        elif isinstance(raw, str):
            try: creds_dict = json.loads(raw)
            except: pass
            
    if not creds_dict:
        if "private_key" in st.secrets and "client_email" in st.secrets:
            creds_dict = {
                "type": st.secrets.get("type", "service_account"),
                "project_id": st.secrets.get("project_id", ""),
                "private_key_id": st.secrets.get("private_key_id", ""),
                "private_key": st.secrets.get("private_key", ""),
                "client_email": st.secrets.get("client_email", ""),
                "client_id": st.secrets.get("client_id", ""),
                "auth_uri": st.secrets.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
                "token_uri": st.secrets.get("token_uri", "https://oauth2.googleapis.com/token"),
                "auth_provider_x509_cert_url": st.secrets.get("auth_provider_x509_cert_url", "https://www.googleapis.com/oauth2/v1/certs"),
                "client_x509_cert_url": st.secrets.get("client_x509_cert_url", "")
            }

    if not creds_dict: return None

    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open("MUKTI_DB").sheet1
        return sheet
    except Exception as e:
        return None

def load_user(username):
    sheet = get_db()
    if not sheet: return None, None
    try:
        cell = sheet.find(username)
        if cell: return sheet.row_values(cell.row), cell.row
    except: pass
    return None, None

def register_user(username, password, onboarding_data):
    sheet = get_db()
    if not sheet: return "ERROR_DB"
    try:
        if sheet.find(username): return "TAKEN"
    except: pass
    
    today_str = str(date.today())
    # При регистрации история пустая "[]"
    row = [username, password, 0, today_str, today_str, json.dumps(onboarding_data), "[]", "FALSE"]
    sheet.append_row(row)
    return "OK"

def update_db_field(row_num, col_num, value):
    sheet = get_db()
    if sheet: sheet.update_cell(row_num, col_num, value)

def save_history(row_num, messages):
    history_str = json.dumps(messages[-20:]) 
    update_db_field(row_num, 7, history_str)

# --- 5. ЛОГИКА ИНТЕРФЕЙСА ---

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# === ЭКРАН ВХОДА / РЕГИСТРАЦИИ ===
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: #0ea5e9;'>MUKTI SYSTEM</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["ВХОД", "РЕГИСТРАЦИЯ"])
    
    with tab1: # ВХОД
        login_user = st.text_input("Твое Имя (Логин)", key="l_user")
        login_pass = st.text_input("Пароль", type="password", key="l_pass")
        
        if st.button("ВОЙТИ В СИСТЕМУ"):
            user_data, row_num = load_user(login_user)
            if user_data and len(user_data) >= 2 and user_data[1] == login_pass:
                st.session_state.logged_in = True
                st.session_state.username = login_user
                st.session_state.row_num = row_num
                st.session_state.streak = int(user_data[2]) if len(user_data) > 2 else 0
                st.session_state.reg_date = user_data[4] if len(user_data) > 4 else str(date.today())
                
                try: st.session_state.messages = json.loads(user_data[6]) if len(user_data) > 6 else []
                except: st.session_state.messages = []
                
                try:
                    ob_data = json.loads(user_data[5]) if len(user_data) > 5 else {}
                    st.session_state.stop_factor = ob_data.get("stop_factor", "Желание жить")
                except: st.session_state.stop_factor = "Свобода"
                    
                st.session_state.vip = (str(user_data[7]).upper() == "TRUE") if len(user_data) > 7 else False

                # === АВТО-ПРИВЕТСТВИЕ (ЕСЛИ ПУСТО) ===
                if not st.session_state.messages:
                    welcome_text = f"Добро пожаловать в пространство, {login_user}. Ты сделал первый шаг к свободе. Я здесь, чтобы помочь тебе выйти из зависимости. Если ты не читал Книгу — начни с этого, иначе нам будет сложно понять друг друга."
                    st.session_state.messages.append({"role": "assistant", "content": welcome_text})
                    save_history(row_num, st.session_state.messages)

                st.rerun()
            else:
                st.error("Ошибка: Неверное имя или пароль.")

    with tab2: # РЕГИСТРАЦИЯ
        st.info("Добро пожаловать в пространство. Ты сделал первый шаг к свободе.")
        
        read_book = st.radio("Ты прочитал книгу 'Кто такой Алкоголь'?", ["Нет", "Да, я в теме"], index=0)
        
        if read_book == "Нет":
            st.warning("⚠️ Невозможно начать работу без базовых знаний.")
            st.markdown("Система говорит на языке 'Высшего Разума'. Прочитай инструкцию.")
        else:
            new_user = st.text_input("Придумай Имя (Логин)", key="r_user")
            new_pass = st.text_input("Придумай Пароль", type="password", key="r_pass")
            
            st.markdown("---")
            st.write("🔧 **Настройка нейросети под тебя:**")
            goal = st.text_input("Твоя главная мотивация?", placeholder="Семья, Деньги, Здоровье...")
            stop_factor = st.text_input("Что остановит тебя в момент срыва?", placeholder="Звонок другу, воспоминание...")
            
            if st.button("ИНИЦИАЛИЗАЦИЯ"):
                if new_user and new_pass and goal and stop_factor:
                    onboarding = {"goal": goal, "stop_factor": stop_factor, "read_book": True}
                    status = register_user(new_user, new_pass, onboarding)
                    if status == "OK":
                        st.success("Идентификация пройдена! Теперь нажми ВХОД.")
                    elif status == "TAKEN": st.error("Это имя уже занято.")
                    else: st.error("Ошибка базы данных.")
                else:
                    st.error("Заполни все поля.")

# === ОСНОВНОЙ ИНТЕРФЕЙС ===
else:
    with st.sidebar:
        st.markdown(f"### АГЕНТ: **{st.session_state.username}**")
        
        if st.session_state.vip:
            st.markdown("💎 СТАТУС: **BOSS**")
        else:
            st.markdown("👤 СТАТУС: **Новичок**")
            try: reg_d = datetime.strptime(st.session_state.reg_date, "%Y-%m-%d").date()
            except: reg_d = date.today()
            limit = 7 if (date.today() - reg_d).days == 0 else 3
            msgs_today = sum(1 for m in st.session_state.messages if m["role"] == "user")
            st.progress(min(msgs_today / limit, 1.0), text=f"Лимит: {msgs_today}/{limit}")
            
            if msgs_today >= limit:
                st.error("🛑 Лимит исчерпан.")
                code = st.text_input("Код доступа")
                if st.button("АКТИВИРОВАТЬ"):
                    if code == VIP_CODE:
                        update_db_field(st.session_state.row_num, 8, "TRUE")
                        st.session_state.vip = True
                        st.rerun()

        st.markdown("---")
        st.metric("Дней Свободы", st.session_state.streak)
        if st.button("✅ Я СЕГОДНЯ ТРЕЗВ"):
             new_streak = st.session_state.streak + 1
             update_db_field(st.session_state.row_num, 3, new_streak)
             update_db_field(st.session_state.row_num, 4, str(date.today()))
             st.session_state.streak = new_streak
             st.balloons()
             st.rerun()

        st.markdown("---")
        if st.button("SOS: Я ХОЧУ ВЫПИТЬ", key="sos_btn"):
            st.session_state.sos_mode = True
        
        if st.button("🚪 ВЫХОД"):
            st.session_state.logged_in = False
            st.rerun()

    if "sos_mode" in st.session_state and st.session_state.sos_mode:
        st.markdown("""
        <div style="background-color: #450a0a; padding: 20px; border-radius: 10px; border: 2px solid #ef4444; text-align: center;">
            <h2 style="color: #fca5a5; margin:0;">⚠️ ВНИМАНИЕ: АТАКА ПАРАЗИТА ⚠️</h2>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"### Твой якорь: **{st.session_state.stop_factor}**")
        st.info("Вдох (4 сек) -> Пауза (4 сек) -> Выдох (4 сек). 5 раз.")
        st.warning("20 приседаний прямо сейчас. Сбрось напряжение.")
        if st.button("Я УСПОКОИЛСЯ. ОТБОЙ ТРЕВОГИ."):
            st.session_state.sos_mode = False
            st.rerun()
            
    else:
        st.title("MUKTI CORE 💠")
        
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        locked = False
        if not st.session_state.vip:
             try: reg_d = datetime.strptime(st.session_state.reg_date, "%Y-%m-%d").date()
             except: reg_d = date.today()
             limit = 7 if (date.today() - reg_d).days == 0 else 3
             if sum(1 for m in st.session_state.messages if m["role"] == "user") >= limit: locked = True

        if locked:
            st.info("🔒 Лимит на сегодня исчерпан. Жду тебя завтра.")
        else:
            if prompt := st.chat_input("Введи сообщение..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                with st.chat_message("assistant"):
                    with st.spinner("Синхронизация..."):
                        # --- НАСТРОЙКА ХАРАКТЕРА ---
                        system_prompt = f"""
                        Ты - MUKTI. Твой пользователь: {st.session_state.username}.
                        Твоя задача: Помочь ему оставаться трезвым.
                        
                        ТВОЙ ХАРАКТЕР:
                        1. Обращайся к пользователю ТОЛЬКО по имени: {st.session_state.username}. Не используй слово "Аватар" как обращение.
                        2. Будь краток. Максимум 3-4 предложения. Не пиши поэмы.
                        3. Ты - "Боевой товарищ", а не "Унылый философ". Говори четко, по делу, поддерживай, но не сюсюкайся.
                        4. Алкоголь называй "Паразит" или "Сбой программы".
                        
                        БАЗА ЗНАНИЙ (Использовать суть, но не цитировать кусками):
                        {BOOK_SUMMARY}
                        
                        Мотивация пользователя (Якорь): {st.session_state.get('stop_factor')}
                        """
                        full_prompt = f"{system_prompt}\nИстория:\n{st.session_state.messages[-5:]}\nUser: {prompt}"
                        
                        try:
                            response = model.generate_content(full_prompt).text
                            st.markdown(response)
                            st.session_state.messages.append({"role": "assistant", "content": response})
                            save_history(st.session_state.row_num, st.session_state.messages)
                        except Exception as e:
                            st.error("Ошибка связи.")
