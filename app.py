import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
import time
import json

# --- НАСТРОЙКИ ---
st.set_page_config(page_title="MUKTI", page_icon="🔥", layout="centered")
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #fff; }
    h1 { color: #facc15; }
    .stTextInput > div > div > input { background-color: #1f2937; color: #fff; }
    .stButton > button { background-color: #facc15; color: #000000; font-weight: bold; border: none; }
    .stWarning { background-color: #374151; color: #ffffff; border: 1px solid #facc15; }
</style>
""", unsafe_allow_html=True)

# --- 1. ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ ---
@st.cache_resource
def connect_db():
    try:
        # Проверяем, заполнил ли пользователь секцию [service_account]
        if "service_account" in st.secrets:
            # Превращаем TOML в словарь
            creds_dict = dict(st.secrets["service_account"])
            
            # --- ГЛАВНЫЙ ФИКС ОШИБКИ "INVALID CONTROL CHARACTER" ---
            # Если ключ содержит экранированные \n, превращаем их в настоящие
            if "\\n" in creds_dict["private_key"]:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            sheet = client.open_by_url(st.secrets["SHEET_URL"]).sheet1
            return sheet
        else:
            st.error("❌ В Secrets не найдена секция [service_account]. Проверь инструкцию.")
            return None
    except Exception as e:
        st.error(f"❌ Ошибка подключения: {e}")
        return None

sheet = connect_db()

# --- 2. ФУНКЦИИ БАЗЫ ДАННЫХ ---
def get_user_data(username):
    if not sheet: return None, None
    try:
        cell = sheet.find(username)
        if cell:
            row = sheet.row_values(cell.row)
            return row, cell.row
        return None, None
    except: return None, None

def update_db(row_num, count):
    if not sheet: return
    try:
        sheet.update_cell(row_num, 2, count)
        sheet.update_cell(row_num, 3, str(date.today()))
    except: pass

def create_user(username):
    if not sheet: return
    try:
        sheet.append_row([username, 0, str(date.today()), ""])
    except: pass

# --- 3. AI МОЗГИ ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except:
    st.error("Ошибка API ключа Gemini.")
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
    st.error("Ошибка AI. Сервис недоступен.")
    st.stop()

SYSTEM_PROMPT = """
ТЫ — MUKTI. Ментор по книге "Кто такой Алкоголь".
Твои принципы:
1. Алкоголь — Паразит.
2. Безопасных доз нет.
3. Дофаминовая яма требует 40 дней.
4. Стиль: Жесткий, но любящий брат.
"""

# --- 4. ЭКРАН ВХОДА ---
if "user_row" not in st.session_state:
    st.title("🔥 MUKTI")
    st.write("Назови свой позывной (Ник), чтобы я узнал тебя.")
    
    username_input = st.text_input("Введи имя:").strip().lower()
    
    if st.button("Войти") and username_input:
        with st.spinner("Проверка базы данных..."):
            row_data, row_id = get_user_data(username_input)
            
            if row_data:
                st.session_state.username = username_input
                st.session_state.user_row = row_id
                # Сброс счетчика, если новый день
                if len(row_data) > 2 and row_data[2] != str(date.today()):
                    st.session_state.msg_count = 0 
                else:
                    st.session_state.msg_count = int(row_data[1]) if len(row_data) > 1 else 0
                st.session_state.messages = [{"role": "assistant", "content": f"С возвращением, {username_input}. Твой счетчик обновлен."}]
            else:
                create_user(username_input)
                st.session_state.username = username_input
                st.session_state.msg_count = 0
                st.session_state.user_row = len(sheet.get_all_values()) 
                st.session_state.messages = [{"role": "assistant", "content": "Добро пожаловать. Я внес тебя в список идущих к свободе."}]
            
            time.sleep(1)
            st.rerun()
    st.stop()

# --- 5. ЧАТ ---
st.title(f"🔥 MUKTI | {st.session_state.username.upper()}")
DAILY_LIMIT = 5

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Сообщение..."):
    if st.session_state.msg_count >= DAILY_LIMIT:
        st.warning(f"🛑 Лимит ({DAILY_LIMIT}) исчерпан. Возвращайся завтра.")
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
