import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
import time
import json
import base64
import os

# --- 1. КОНСТАНТЫ И НАСТРОЙКИ ---
LIMIT_NEW_USER = 7
LIMIT_OLD_USER = 3
HISTORY_DEPTH = 30
SOS_BREATH_CYCLES = 5
SOS_SQUATS = 20
VIP_CODE = st.secrets.get("VIP_CODE", "MUKTI_BOSS")

try:
    from book import FULL_BOOK_TEXT, BOOK_SUMMARY
except ImportError:
    FULL_BOOK_TEXT = "Текст книги недоступен."
    BOOK_SUMMARY = "Философия освобождения от зависимости."

GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"] if "GOOGLE_API_KEY" in st.secrets else "NO_KEY"
genai.configure(api_key=GOOGLE_API_KEY)

# --- 2. МОЗГИ (УМНЫЙ ПОИСК) ---
@st.cache_resource
def get_model():
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority_list = ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']
        
        for p in priority_list:
            if p in available_models:
                return genai.GenerativeModel(p)
        
        if available_models:
            return genai.GenerativeModel(available_models[0])
            
    except Exception as e:
        return None
    return None

model = get_model()

# --- 3. ДИЗАЙН: MATRIX PREMIUM ---
st.set_page_config(page_title="MUKTI MATRIX", page_icon="🧩", layout="centered")

def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return None

bg_file = "matrix_bg.jpg"
if not os.path.exists(bg_file):
    bg_file = "matrix_bg.png"
if not os.path.exists(bg_file):
    bg_file = "background.jpg" 

bin_str = get_base64_of_bin_file(bg_file)

css_code = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Orbitron:wght@400;500;700&display=swap');

    /* 1. БАЗА */
    .stApp {{
        background-image: url("data:image/jpg;base64,{bin_str}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-color: #000000;
        color: #EAEAEA;
        font-family: 'Inter', sans-serif;
    }}
    
    header {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    /* 2. GLASSMORPHISM (DARK) */
    .glass-container {{
        background: rgba(15, 15, 15, 0.85);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 24px;
        padding: 30px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.9);
        margin-bottom: 25px;
    }}

    /* 3. ЗАГОЛОВОК С ЭФФЕКТОМ */
    h1 {{
        font-family: 'Orbitron', sans-serif;
        color: #EAEAEA;
        text-transform: uppercase;
        letter-spacing: 4px;
        text-align: center;
        transition: all 0.4s ease;
        cursor: default;
    }}
    
    h1:hover {{
        color: #FFFFFF;
        text-shadow: 0 0 15px rgba(0, 230, 118, 0.8), 0 0 30px rgba(0, 230, 118, 0.4);
    }}

    h2, h3 {{
        font-family: 'Orbitron', sans-serif;
        color: #EAEAEA;
    }}
    
    p, div, label {{
        color: #CCCCCC;
        font-weight: 300;
    }}

    /* 4. ПОЛЯ ВВОДА */
    .stTextInput > div > div > input {{
        background: rgba(10, 10, 10, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        color: #00E676 !important;
        border-radius: 12px;
        height: 50px;
        font-family: 'Inter', sans-serif;
        font-size: 16px;
        transition: all 0.3s ease;
    }}
    .stTextInput > div > div > input:focus {{
        border-color: #00E676 !important;
        box-shadow: 0 0 15px rgba(0, 230, 118, 0.2);
        background: rgba(0, 0, 0, 0.9) !important;
    }}

    /* 5. КНОПКИ (НЕОНОВАЯ ОБВОДКА) */
    .stButton > button {{
        background-color: transparent !important;
        border: 1px solid #00E676 !important;
        color: #00E676 !important;
        border-radius: 12px;
        height: 50px;
        font-family: 'Orbitron', sans-serif;
        font-weight: 600;
        font-size: 14px;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        transition: all 0.3s ease;
    }}
    
    .stButton > button:hover {{
        background-color: rgba(0, 230, 118, 0.05) !important;
        color: #FFFFFF !important;
        border-color: #00E676 !important;
        box-shadow: 0 0 15px rgba(0, 230, 118, 0.5);
        transform: translateY(-1px);
    }}
    
    .stButton > button:disabled {{
        border-color: #333 !important;
        color: #555 !important;
        background: transparent !important;
        box-shadow: none !important;
    }}

    /* 6. КНОПКА SOS (RED) */
    div[data-testid="column"]:nth-of-type(3) .stButton > button {{
        border-color: #FF3D00 !important;
        color: #FF3D00 !important;
    }}
    div[data-testid="column"]:nth-of-type(3) .stButton > button:hover {{
        background-color: rgba(255, 61, 0, 0.1) !important;
        color: #FFFFFF !important;
        box-shadow: 0 0 20px rgba(255, 61, 0, 0.6);
    }}

    /* 7. ЧАТ */
    .stChatMessage {{
        background: rgba(30, 30, 30, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        margin-bottom: 12px;
    }}
    .stChatMessage .stChatMessageAvatar {{
        background: #000;
        border: 1px solid #00E676;
    }}
    
    /* 8. ТАБЫ */
    .stTabs [data-baseweb="tab-list"] {{
        background-color: transparent;
        border-bottom: 1px solid rgba(255,255,255,0.1);
    }}
    .stTabs [data-baseweb="tab"] {{
        color: #888;
        font-family: 'Orbitron', sans-serif;
    }}
    .stTabs [aria-selected="true"] {{
        color: #00E676 !important;
        border-bottom: 2px solid #00E676;
    }}
    
    a {{ color: #00E676; text-decoration: none; transition: 0.3s; }}
    a:hover {{ text-shadow: 0 0 10px #00E676; }}

</style>
"""
if not bin_str:
    css_code = css_code.replace('background-image: url("data:image/jpg;base64,None");', 'background-color: #000000;')

st.markdown(css_code, unsafe_allow_html=True)

# --- 4. БАЗА ДАННЫХ ---
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
        if "private_key" in st.secrets:
            creds_dict = {k: st.secrets.get(k) for k in ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id", "auth_uri", "token_uri", "auth_provider_x509_cert_url", "client_x509_cert_url"]}

    if not creds_dict: return None

    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open("MUKTI_DB").sheet1
        return sheet
    except: return None

def load_user(username):
    sheet = get_db()
    if not sheet: return None, None
    try:
        cell = sheet.find(username)
        if cell: return sheet.row_values(cell.row), cell.row
    except: pass
    return None, None

def register_user(username, pin):
    sheet = get_db()
    if not sheet: return "ERROR"
    try:
        if sheet.find(username): return "TAKEN"
    except: pass
    
    today_str = str(date.today())
    row = [username, pin, 0, today_str, today_str, "{}", "[]", "FALSE"]
    sheet.append_row(row)
    return "OK"

def update_db_field(row_num, col_num, value):
    sheet = get_db()
    if sheet: sheet.update_cell(row_num, col_num, value)

def save_history(row_num, messages):
    try:
        history_str = json.dumps(messages[-HISTORY_DEPTH:]) 
        update_db_field(row_num, 7, history_str)
    except: pass

def update_onboarding_data(row_num, key, value):
    sheet = get_db()
    if sheet:
        try:
            current_json = sheet.cell(row_num, 6).value
            data = json.loads(current_json) if current_json else {}
            data[key] = value
            sheet.update_cell(row_num, 6, json.dumps(data))
            return data
        except: return {}

# --- 5. ЛОГИКА ИНТЕРФЕЙСА ---

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "onboarding_step" not in st.session_state:
    st.session_state.onboarding_step = -1

# === ЭКРАН ВХОДА ===
if not st.session_state.logged_in:
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1>MUKTI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888; font-size: 14px; letter-spacing: 2px;'>PORTAL ACCESS</p>", unsafe_allow_html=True)
    
    st.markdown('<div class="glass-container">', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["ВХОД", "РЕГИСТРАЦИЯ"])
    
    with tab1: # ВХОД
        st.write("")
        l_user = st.text_input("ИМЯ", key="l_u")
        l_pin = st.text_input("PIN (4 цифры)", type="password", key="l_p", max_chars=4)
        
        if st.button("ВОЙТИ", use_container_width=True):
            with st.spinner("Синхронизация..."):
                user_data, row_num = load_user(l_user)
                if user_data and str(user_data[1]) == str(l_pin):
                    st.session_state.logged_in = True
                    st.session_state.username = l_user
                    st.session_state.row_num = row_num
                    st.session_state.streak = int(user_data[2]) if len(user_data) > 2 else 0
                    
                    today = date.today()
                    try: 
                        st.session_state.last_active = user_data[3] if len(user_data) > 3 else str(today)
                        st.session_state.reg_date = user_data[4] if len(user_data) > 4 else str(today)
                        datetime.strptime(st.session_state.last_active, "%Y-%m-%d")
                    except ValueError:
                        st.session_state.last_active = str(today)
                        st.session_state.reg_date = str(today)
                        
                    st.session_state.vip = (str(user_data[7]).upper() == "TRUE") if len(user_data) > 7 else False
                    
                    try: st.session_state.messages = json.loads(user_data[6]) if len(user_data) > 6 else []
                    except: st.session_state.messages = []

                    try:
                        ob_data = json.loads(user_data[5])
                        st.session_state.stop_factor = ob_data.get("stop_factor", "Свобода")
                        if "goal" in ob_data and "stop_factor" in ob_data:
                            st.session_state.onboarding_step = -1
                        else:
                            st.session_state.onboarding_step = 0
                    except:
                        st.session_state.onboarding_step = 0
                        st.session_state.stop_factor = "Свобода"
                    
                    st.rerun()
                else:
                    st.error("Неверное Имя или PIN.")

    with tab2: # РЕГИСТРАЦИЯ
        st.write("")
        st.info("Придумай Имя и PIN. Система запомнит тебя.")
        r_user = st.text_input("НОВОЕ ИМЯ", key="r_u")
        r_pin = st.text_input("НОВЫЙ PIN", type="password", key="r_p", max_chars=4)
        
        if st.button("СОЗДАТЬ ПРОФИЛЬ", use_container_width=True):
            if r_user and len(r_pin) == 4:
                res = register_user(r_user, r_pin)
                if res == "OK":
                    with st.spinner("Создание нейросвязей..."):
                        time.sleep(1)
                        user_data, row_num = load_user(r_user)
                        
                        if user_data:
                            st.session_state.logged_in = True
                            st.session_state.username = r_user
                            st.session_state.row_num = row_num
                            st.session_state.streak = 0
                            st.session_state.last_active = str(date.today())
                            st.session_state.reg_date = str(date.today())
                            st.session_state.vip = False
                            st.session_state.messages = []
                            st.session_state.stop_factor = "Свобода"
                            st.session_state.onboarding_step = 0 
                            
                            st.success("Профиль создан! Входим...")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Ошибка авто-входа.")
                elif res == "TAKEN":
                    st.error("Это Имя уже занято.")
                else:
                    st.error("Ошибка соединения.")
            else:
                st.warning("Введи Имя и 4 цифры PIN.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# === ВНУТРИ СИСТЕМЫ ===
else:
    # --- ЭТАП ОНБОРДИНГА ---
    if st.session_state.onboarding_step >= 0:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align:center;'>ЗНАКОМСТВО</h2>", unsafe_allow_html=True)
        
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)

        if st.session_state.onboarding_step == 0:
            st.write(f"👋 **Привет, {st.session_state.username}.**")
            st.write("Я MUKTI - модератор этого пространства, где ты обретаешь свободу от зависимости.")
            st.write("Скажи: ты уже читал книгу **'Кто такой Алкоголь'**?")
            
            c1, c2 = st.columns(2)
            if c1.button("ДА, ЧИТАЛ", use_container_width=True):
                update_onboarding_data(st.session_state.row_num, "read_book", True)
                st.session_state.onboarding_step = 1
                st.rerun()
            if c2.button("НЕТ, НЕ ЧИТАЛ", use_container_width=True):
                st.info("Советую прочитать, чтобы мы понимали друг друга.")
                st.markdown("👉 [**Скачать книгу на LitRes**](https://www.litres.ru/book/roman-vybornov/pochemu-ya-nikogo-ne-em-72075331/)")
                if st.button("ПРОПУСТИТЬ И ПРОДОЛЖИТЬ", use_container_width=True):
                    update_onboarding_data(st.session_state.row_num, "read_book", False)
                    st.session_state.onboarding_step = 1
                    st.rerun()
                    
        elif st.session_state.onboarding_step == 1:
            st.write("🎯 **Цель.**")
            st.write("Напиши мне: **Ради чего ты здесь?** (Семья, Деньги, Здоровье, просто надоело...)")
            
            if goal_input := st.chat_input("Моя цель..."):
                update_onboarding_data(st.session_state.row_num, "goal", goal_input)
                st.session_state.onboarding_step = 2
                st.rerun()
                
        elif st.session_state.onboarding_step == 2:
            st.write("⚓️ **Стоп-кран.**")
            st.write("Что может тебя остановить, если вдруг захочется выпить?")
            
            if trigger_input := st.chat_input("Меня остановит..."):
                data = update_onboarding_data(st.session_state.row_num, "stop_factor", trigger_input)
                st.session_state.stop_factor = trigger_input
                
                # Финал онбординга
                st.session_state.onboarding_step = -1
                
                welcome_msg = "Профиль настроен. Я включил защиту.\nНажми кнопку **'СЕГОДНЯ ЧИСТ'** наверху, чтобы запустить счетчик свободы."
                st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
                save_history(st.session_state.row_num, st.session_state.messages)
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

    # --- ОСНОВНОЙ РАБОЧИЙ СТОЛ ---
    else:
        # SOS LOGIC
        if "sos_mode" not in st.session_state: st.session_state.sos_mode = False

        if st.session_state.sos_mode:
            st.markdown(f"""
            <div style="background: rgba(40, 0, 0, 0.8); border: 1px solid #FF3D00; padding: 25px; border-radius: 20px; text-align: center; margin-bottom: 25px; backdrop-filter: blur(20px);">
                <h2 style="color: #FF3D00; margin:0; letter-spacing: 5px; font-size: 2rem;">⚠️ АТАКА ПАРАЗИТА</h2>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"<div style='text-align:center; margin-bottom:20px;'>Твой якорь:<br><strong style='font-size:28px; color:#EAEAEA; letter-spacing:1px;'>{st.session_state.stop_factor}</strong></div>", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            c1.info(f"💨 **ДЫХАНИЕ**\n\n4 сек Вдох - 4 сек Пауза - 4 сек Выдох.\n\nПовтори {SOS_BREATH_CYCLES} раз.")
            c2.warning(f"⚡️ **ДЕЙСТВИЕ**\n\n{SOS_SQUATS} приседаний.\n\nПрямо сейчас. Сжги адреналин.")
            
            if st.button("КОНТРОЛЬ ВОССТАНОВЛЕН", use_container_width=True):
                st.session_state.sos_mode = False
                
                follow_up = "Сигнал принят. Ты справился. Горжусь.\n\nРасскажи, что именно случилось? Откуда пришла тяга?"
                st.session_state.messages.append({"role": "assistant", "content": follow_up})
                save_history(st.session_state.row_num, st.session_state.messages)
                st.rerun()

        else:
            # HEADER
            st.markdown(f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;'><div style='font-family: Orbitron; font-weight:800; font-size:24px; color:#EAEAEA; letter-spacing:2px;'>MUKTI <span style='color:#00E676; font-size:16px;'>// ONLINE</span></div><div style='text-align:right; font-size:12px; color:#888;'>АГЕНТ<br><span style='color:#00E676; font-family:Orbitron;'>{st.session_state.username}</span></div></div>", unsafe_allow_html=True)
            
            # DASHBOARD
            st.markdown('<div class="glass-container" style="padding: 20px; margin-bottom: 25px;">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 1.5, 1])
            
            with col1:
                 st.markdown(f"<div style='text-align:center;'><div style='font-size: 10px; color: #888; letter-spacing: 2px; text-transform:uppercase;'>Свобода</div><div style='font-family: Orbitron; font-size: 42px; font-weight:800; color: #fff; text-shadow: 0 0 20px rgba(0, 230, 118, 0.4);'>{st.session_state.streak}</div></div>", unsafe_allow_html=True)
            
            with col2:
                today = date.today()
                try: 
                    last_active = datetime.strptime(st.session_state.last_active, "%Y-%m-%d").date()
                except ValueError:
                    last_active = today
                    
                delta = (today - last_active).days
                
                if delta == 0 and st.session_state.streak > 0:
                    st.button("✅ ЗАЧТЕНО", disabled=True, use_container_width=True)
                else:
                    if st.button("✨ СЕГОДНЯ ЧИСТ", use_container_width=True):
                        # === ВОТ ЗДЕСЬ ИЗМЕНЕНИЯ (АКТИВНЫЙ ДИАЛОГ) ===
                        if delta > 1 and st.session_state.streak > 0:
                             new_streak = 1
                             st.toast("Счетчик перезапущен.", icon="🔄")
                             # Сообщение при срыве
                             msg = "Счетчик перезапущен. Не кори себя. Срыв — это часть пути, если сделать выводы.\n\nЧто стало причиной? Давай разберем это прямо сейчас."
                        else:
                             new_streak = st.session_state.streak + 1
                             st.toast("Синхронизация успешна.", icon="🔋")
                             # Сообщение при успехе
                             if new_streak == 1:
                                 msg = "Отсчет пошел. Это твой фундамент.\n\nРасскажи, что ты чувствуешь прямо сейчас? Есть ли тревога или ты полон решимости?"
                             else:
                                 msg = f"День {new_streak} зафиксирован. Ты становишься сильнее.\n\nКак прошло твое время? Были ли моменты, когда Паразит пытался атаковать?"
                             
                        update_db_field(st.session_state.row_num, 3, new_streak)
                        update_db_field(st.session_state.row_num, 4, str(today))
                        st.session_state.streak = new_streak
                        st.session_state.last_active = str(today)
                        
                        # Добавляем сообщение бота в чат и сохраняем
                        st.session_state.messages.append({"role": "assistant", "content": msg})
                        save_history(st.session_state.row_num, st.session_state.messages)
                        
                        st.rerun()
            
            with col3:
                if st.button("🚨 SOS", use_container_width=True):
                    st.session_state.sos_mode = True
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)

            # CHAT AREA
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            
            # LIMITS CHECK
            locked = False
            if not st.session_state.vip:
                 try: reg_d = datetime.strptime(st.session_state.reg_date, "%Y-%m-%d").date()
                 except: reg_d = date.today()
                 
                 limit = LIMIT_NEW_USER if (date.today() - reg_d).days == 0 else LIMIT_OLD_USER
                 
                 msgs_today = sum(1 for m in st.session_state.messages if m["role"] == "user")
                 if msgs_today >= limit: locked = True

            if locked:
                st.markdown("""
                <div class="glass-container" style="text-align:center;">
                    <h3 style='color: #888; margin:0; font-size: 16px;'>🔒 Лимит энергии исчерпан</h3>
                    <p style='color: #CCCCCC; font-size: 14px; margin-top: 10px;'>
                        Напиши слово <b>MUKTI</b> Роману, чтобы продолжить общение без ограничений.
                    </p>
                    <a href="https://t.me/Vybornov_Roman" target="_blank" class="vip-link">👉 НАПИСАТЬ РОМАНУ</a>
                    <br><br>
                </div>
                """, unsafe_allow_html=True)
                
                code = st.text_input("Введи код доступа сюда:")
                if st.button("АКТИВИРОВАТЬ КОД", use_container_width=True):
                    if code == VIP_CODE:
                        update_db_field(st.session_state.row_num, 8, "TRUE")
                        st.session_state.vip = True
                        st.success("Доступ открыт!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Неверный код.")
            else:
                if prompt := st.chat_input("Ввод данных..."):
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.markdown(prompt)
                    
                    with st.chat_message("assistant"):
                        with st.spinner("Анализ..."):
                            system_prompt = f"""
                            Ты - MUKTI. Пользователь: {st.session_state.username}.
                            Твоя роль: Модератор пространства свободы. Друг, наставник.
                            
                            СТИЛЬ ОБЩЕНИЯ:
                            1. Простой, понятный, человеческий язык. Без "зауми".
                            2. НЕ используй слова: "протокол", "аватар", "модификация", "компенсация".
                            3. Вместо этого говори: "привычка", "ты", "действия", "изменения".
                            4. Алкоголь называй "Паразит".
                            5. Используй обычное короткое тире (-) вместо длинного.
                            6. Ответы краткие (3-4 предложения).
                            7. Задавай вопросы, чтобы поддержать разговор.
                            
                            БАЗА ЗНАНИЙ: {BOOK_SUMMARY}
                            МОТИВАЦИЯ ЮЗЕРА: {st.session_state.get('stop_factor')}
                            """
                            full_prompt = f"{system_prompt}\nИстория:\n{st.session_state.messages[-5:]}\nUser: {prompt}"
                            
                            try:
                                # RETRY LOGIC (надежная, без хардкода имен)
                                response_text = None
                                for attempt in range(3):
                                    try:
                                        # Используем ту модель, которую нашли при старте (model)
                                        if model:
                                            response_text = model.generate_content(full_prompt).text
                                            break
                                        else:
                                            raise Exception("Модель не инициализирована")
                                    except:
                                        time.sleep(1)
                                        continue
                                
                                if response_text:
                                    st.markdown(response_text)
                                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                                    save_history(st.session_state.row_num, st.session_state.messages)
                                else:
                                    st.error("Сигнал потерян. Нажми Enter еще раз.")
                            except Exception as e:
                                st.error(f"Ошибка системы: {e}")

        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.sidebar.button("ВЫХОД ИЗ СИСТЕМЫ"):
             st.session_state.logged_in = False
             st.rerun()
