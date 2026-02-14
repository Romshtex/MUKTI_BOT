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

# --- 2. МОЗГИ ---
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

# --- 3. ДИЗАЙН: MATRIX PREMIUM ---
st.set_page_config(page_title="MUKTI MATRIX", page_icon="🧩", layout="centered")

def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return None

# Ищем фон (приоритет jpg, потом png)
bg_file = "matrix_bg.jpg"
if not os.path.exists(bg_file):
    bg_file = "matrix_bg.png"
if not os.path.exists(bg_file):
    bg_file = "background.jpg" # На случай если забыл переименовать

bin_str = get_base64_of_bin_file(bg_file)

css_code = f"""
<style>
    /* ПОДКЛЮЧЕНИЕ ШРИФТОВ: Orbitron (Заголовки) + Inter (Текст) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Orbitron:wght@400;500;700&display=swap');

    /* 1. БАЗА */
    .stApp {{
        background-image: url("data:image/jpg;base64,{bin_str}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-color: #000000; /* Fallback */
        color: #EAEAEA;
        font-family: 'Inter', sans-serif;
    }}
    
    header {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    /* 2. GLASSMORPHISM (PREMIUM DARK) */
    .glass-container {{
        background: rgba(20, 20, 20, 0.7);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 24px;
        padding: 30px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.9);
        margin-bottom: 25px;
    }}

    /* 3. ТИПОГРАФИКА */
    h1, h2, h3 {{
        font-family: 'Orbitron', sans-serif;
        color: #EAEAEA;
        text-transform: uppercase;
        letter-spacing: 2px;
        text-shadow: 0 0 10px rgba(0, 230, 118, 0.2); /* Легкое зеленое свечение */
    }}
    
    p, div, label {{
        color: #CCCCCC;
        font-weight: 300;
    }}

    /* 4. ПОЛЯ ВВОДА */
    .stTextInput > div > div > input {{
        background: rgba(10, 10, 10, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        color: #00E676 !important; /* Matrix Green Text */
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

    /* 5. КНОПКИ (DIGITAL ZEN) */
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
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    
    .stButton > button:hover {{
        background-color: #00E676 !important;
        color: #000000 !important;
        box-shadow: 0 0 20px rgba(0, 255, 150, 0.4);
        transform: translateY(-2px);
        border-color: #00E676 !important;
    }}
    
    /* Отключенная кнопка */
    .stButton > button:disabled {{
        border-color: #333 !important;
        color: #555 !important;
        background: transparent !important;
        box-shadow: none !important;
    }}

    /* 6. КНОПКА SOS (SYSTEM ERROR RED) */
    div[data-testid="column"]:nth-of-type(3) .stButton > button {{
        border-color: #FF3D00 !important;
        color: #FF3D00 !important;
    }}
    div[data-testid="column"]:nth-of-type(3) .stButton > button:hover {{
        background-color: #FF3D00 !important;
        color: #000000 !important;
        box-shadow: 0 0 25px rgba(255, 61, 0, 0.5);
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
    
    /* ССЫЛКИ */
    a {{ color: #00E676; text-decoration: none; transition: 0.3s; }}
    a:hover {{ text-shadow: 0 0 10px #00E676; }}

</style>
"""

# Если картинки нет, ставим черный фон
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

# === ЭКРАН ВХОДА (ПОРТАЛ) ===
if not st.session_state.logged_in:
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1>MUKTI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; letter-spacing: 2px; font-size: 14px; opacity: 0.7;'>SYSTEM ACCESS // PORTAL</p>", unsafe_allow_html=True)
    
    st.markdown('<div class="glass-container">', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["ВХОД", "РЕГИСТРАЦИЯ"])
    
    with tab1: # ВХОД
        st.write("")
        l_user = st.text_input("ИМЯ / CODENAME", key="l_u")
        l_pin = st.text_input("PIN ACCESS", type="password", key="l_p", max_chars=4)
        
        if st.button("CONNECT", use_container_width=True):
            with st.spinner("INITIATING HANDSHAKE..."):
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
                    st.error("ACCESS DENIED")

    with tab2: # РЕГИСТРАЦИЯ
        st.write("")
        st.info("Создай свою цифровую проекцию.")
        r_user = st.text_input("НОВОЕ ИМЯ", key="r_u")
        r_pin = st.text_input("НОВЫЙ PIN", type="password", key="r_p", max_chars=4)
        
        if st.button("INITIALIZE PROFILE", use_container_width=True):
            if r_user and len(r_pin) == 4:
                res = register_user(r_user, r_pin)
                if res == "OK":
                    with st.spinner("GENERATING CODE..."):
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
                            
                            st.success("SUCCESS. LOGGING IN...")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("SYSTEM ERROR")
                elif res == "TAKEN":
                    st.error("NAME TAKEN")
                else:
                    st.error("CONNECTION ERROR")
            else:
                st.warning("ENTER DATA")
    
    st.markdown('</div>', unsafe_allow_html=True)

# === ВНУТРИ СИСТЕМЫ ===
else:
    # --- ЭТАП ОНБОРДИНГА ---
    if st.session_state.onboarding_step >= 0:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align:center;'>INITIALIZATION</h2>", unsafe_allow_html=True)
        
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)

        if st.session_state.onboarding_step == 0:
            st.write(f"👋 **Здравствуй, {st.session_state.username}.**")
            st.write("Я MUKTI. Я не часть системы, я — выход из неё.")
            st.write("Скажи: ты знаком с теорией (книга **'Кто такой Алкоголь'**)?")
            
            c1, c2 = st.columns(2)
            if c1.button("ДА, ЗНАКОМ", use_container_width=True):
                update_onboarding_data(st.session_state.row_num, "read_book", True)
                st.session_state.onboarding_step = 1
                st.rerun()
            if c2.button("НЕТ, НЕ ЗНАКОМ", use_container_width=True):
                st.info("Рекомендую загрузить данные перед началом.")
                st.markdown("👉 [**Скачать данные (LitRes)**](https://www.litres.ru/book/roman-vybornov/pochemu-ya-nikogo-ne-em-72075331/)")
                if st.button("ПРОПУСТИТЬ ЗАГРУЗКУ", use_container_width=True):
                    update_onboarding_data(st.session_state.row_num, "read_book", False)
                    st.session_state.onboarding_step = 1
                    st.rerun()
                    
        elif st.session_state.onboarding_step == 1:
            st.write("🎯 **Цель.**")
            st.write("Какова твоя истинная мотивация? Ради чего ты выходишь из системы?")
            
            if goal_input := st.chat_input("Моя цель..."):
                update_onboarding_data(st.session_state.row_num, "goal", goal_input)
                st.session_state.onboarding_step = 2
                st.rerun()
                
        elif st.session_state.onboarding_step == 2:
            st.write("⚓️ **Аварийный протокол.**")
            st.write("Что вернет тебя в реальность, если программа зависимости попытается перехватить управление?")
            
            if trigger_input := st.chat_input("Меня остановит..."):
                data = update_onboarding_data(st.session_state.row_num, "stop_factor", trigger_input)
                st.session_state.stop_factor = trigger_input
                
                # Финал онбординга
                st.session_state.onboarding_step = -1
                
                welcome_msg = "Профиль создан. Защита активна.\nНажми кнопку **'СЕГОДНЯ ЧИСТ'**, чтобы подтвердить контроль."
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
                <h2 style="color: #FF3D00; margin:0; letter-spacing: 5px; font-size: 2rem;">⚠️ SYSTEM BREACH</h2>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"<div style='text-align:center; margin-bottom:20px;'>Твой якорь:<br><strong style='font-size:28px; color:#EAEAEA; letter-spacing:1px;'>{st.session_state.stop_factor}</strong></div>", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            c1.info(f"💨 **ДЫХАНИЕ**\n\n4 сек Вдох - 4 сек Пауза - 4 сек Выдох.\n\nПовтори {SOS_BREATH_CYCLES} раз.")
            c2.warning(f"⚡️ **ДЕЙСТВИЕ**\n\n{SOS_SQUATS} приседаний.\n\nСброс адреналина.")
            
            if st.button("КОНТРОЛЬ ВОССТАНОВЛЕН", use_container_width=True):
                st.session_state.sos_mode = False
                
                follow_up = "Сигнал принят. Ты справился. Система стабильна.\n\nРасскажи, что спровоцировало сбой?"
                st.session_state.messages.append({"role": "assistant", "content": follow_up})
                save_history(st.session_state.row_num, st.session_state.messages)
                st.rerun()

        else:
            # HEADER
            st.markdown(f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;'><div style='font-family: Orbitron; font-weight:800; font-size:24px; color:#EAEAEA; letter-spacing:2px;'>MUKTI <span style='color:#00E676; font-size:16px;'>v6.0</span></div><div style='text-align:right; font-size:12px; color:#888;'>OPERATOR<br><span style='color:#00E676; font-family:Orbitron;'>{st.session_state.username}</span></div></div>", unsafe_allow_html=True)
            
            # DASHBOARD
            st.markdown('<div class="glass-container" style="padding: 20px; margin-bottom: 25px;">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 1.5, 1])
            
            with col1:
                 st.markdown(f"<div style='text-align:center;'><div style='font-size: 10px; color: #888; letter-spacing: 2px; text-transform:uppercase;'>Days Free</div><div style='font-family: Orbitron; font-size: 42px; font-weight:800; color: #fff; text-shadow: 0 0 20px rgba(0, 230, 118, 0.4);'>{st.session_state.streak}</div></div>", unsafe_allow_html=True)
            
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
                        if delta > 1 and st.session_state.streak > 0:
                             new_streak = 1
                             st.toast("Цикл перезапущен.", icon="🔄")
                        else:
                             new_streak = st.session_state.streak + 1
                             st.toast("Синхронизация успешна.", icon="🔋")
                             
                        update_db_field(st.session_state.row_num, 3, new_streak)
                        update_db_field(st.session_state.row_num, 4, str(today))
                        st.session_state.streak = new_streak
                        st.session_state.last_active = str(today)
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
                    <h3 style='color: #888; margin:0; font-size: 16px;'>🔒 DAILY LIMIT REACHED</h3>
                    <p style='color: #CCCCCC; font-size: 14px; margin-top: 10px;'>
                        Для снятия ограничений отправь <b>MUKTI</b> Роману.
                    </p>
                    <a href="https://t.me/Vybornov_Roman" target="_blank" style="color:#00E676; font-weight:bold; border-bottom:1px solid #00E676;">👉 TELEGRAM LINK</a>
                    <br><br>
                </div>
                """, unsafe_allow_html=True)
                
                code = st.text_input("ACCESS CODE:")
                if st.button("UNLOCK SYSTEM", use_container_width=True):
                    if code == VIP_CODE:
                        update_db_field(st.session_state.row_num, 8, "TRUE")
                        st.session_state.vip = True
                        st.success("ACCESS GRANTED")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("INVALID CODE")
            else:
                if prompt := st.chat_input("Ввод данных..."):
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.markdown(prompt)
                    
                    with st.chat_message("assistant"):
                        with st.spinner("PROCESSING..."):
                            system_prompt = f"""
                            Ты - MUKTI. Пользователь: {st.session_state.username}.
                            Роль: Спокойный, уверенный проводник из "Матрицы" зависимости.
                            
                            СТИЛЬ:
                            1. Простой, но глубокий. Без пафоса.
                            2. Избегать слов: "протокол", "аватар", "модификация".
                            3. Использовать: "система", "привычка", "осознанность", "выход".
                            4. Алкоголь = "Программа" или "Паразит".
                            5. Ответы краткие (3-4 предложения).
                            6. Всегда завершать мысль вопросом или призывом к действию.
                            
                            БАЗА ЗНАНИЙ: {BOOK_SUMMARY}
                            МОТИВАЦИЯ ЮЗЕРА: {st.session_state.get('stop_factor')}
                            """
                            full_prompt = f"{system_prompt}\nИстория:\n{st.session_state.messages[-5:]}\nUser: {prompt}"
                            
                            try:
                                response_text = None
                                for attempt in range(3):
                                    try:
                                        response_text = model.generate_content(full_prompt).text
                                        break
                                    except:
                                        time.sleep(1)
                                        continue
                                
                                if response_text:
                                    st.markdown(response_text)
                                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                                    save_history(st.session_state.row_num, st.session_state.messages)
                                else:
                                    try:
                                        backup = genai.GenerativeModel('gemini-1.5-flash')
                                        res = backup.generate_content(full_prompt).text
                                        st.markdown(res)
                                        st.session_state.messages.append({"role": "assistant", "content": res})
                                        save_history(st.session_state.row_num, st.session_state.messages)
                                    except:
                                        st.error("СБОЙ СВЯЗИ")
                            except Exception as e:
                                st.error(f"ERROR: {e}")

        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.sidebar.button("LOGOUT"):
             st.session_state.logged_in = False
             st.rerun()
