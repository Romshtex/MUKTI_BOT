import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
import time
import json
import random

# --- 1. НАСТРОЙКИ ---
try:
    from book import FULL_BOOK_TEXT, BOOK_SUMMARY
except ImportError:
    FULL_BOOK_TEXT = "Текст книги недоступен."
    BOOK_SUMMARY = "Философия освобождения от зависимости."

GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"] if "GOOGLE_API_KEY" in st.secrets else "NO_KEY"
VIP_CODE = "MUKTI_BOSS"

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

# --- 3. ДИЗАЙН ИЗ ТВОЕГО ФАЙЛА (ADAPTED FOR STREAMLIT) ---
st.set_page_config(page_title="MUKTI PORTAL", page_icon="💠", layout="centered")

st.markdown("""
<style>
    /* ИМПОРТ ШРИФТА MANROPE */
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;600&display=swap');

    /* 1. ГЛОБАЛЬНЫЙ ФОН И ШРИФТЫ */
    .stApp {
        background: radial-gradient(circle at 50% 0%, #1a1f35 0%, #070A14 60%, #000000 100%);
        color: #EAF0FF;
        font-family: 'Manrope', sans-serif;
    }
    
    /* Скрываем стандартный хедер и футер */
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* 2. СТЕКЛЯННЫЕ ПАНЕЛИ (GLASSMORPHISM) */
    .glass-container {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(160, 130, 255, 0.15);
        border-radius: 22px;
        padding: 24px;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
        margin-bottom: 20px;
    }

    /* 3. ПОЛЯ ВВОДА */
    .stTextInput > div > div > input {
        background: rgba(11, 15, 31, 0.6) !important;
        border: 1px solid rgba(160, 130, 255, 0.3) !important;
        color: #22D3EE !important; /* Cyan text */
        border-radius: 12px;
        height: 50px;
        font-size: 16px;
        transition: all 0.3s ease;
    }
    .stTextInput > div > div > input:focus {
        border-color: #22D3EE !important;
        box-shadow: 0 0 15px rgba(34, 211, 238, 0.2);
        background: rgba(11, 15, 31, 0.9) !important;
    }

    /* 4. КНОПКИ (ГРАДИЕНТ И СВЕЧЕНИЕ) */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #8B5CF6 100%); /* Violet Gradient */
        color: white;
        border: none;
        border-radius: 14px;
        height: 50px;
        font-weight: 600;
        font-size: 16px;
        letter-spacing: 0.5px;
        box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
        transition: all 0.3s ease;
        text-transform: uppercase;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(139, 92, 246, 0.5);
    }
    
    /* Кнопка SOS - Красная */
    div[data-testid="column"] button {
        /* Это применится ко всем кнопкам в колонках, но мы переопределим SOS отдельно если нужно */
    }

    /* 5. ЧАТ (СООБЩЕНИЯ) */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 18px;
        margin-bottom: 10px;
    }
    /* Аватарки */
    .stChatMessage .stChatMessageAvatar {
        background: linear-gradient(135deg, #22D3EE, #8B5CF6);
    }
    
    /* 6. ВКЛАДКИ (TABS) */
    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent;
        border-bottom: 1px solid rgba(255,255,255,0.1);
    }
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8;
        font-size: 16px;
    }
    .stTabs [aria-selected="true"] {
        color: #22D3EE !important;
        background-color: transparent !important;
        border-bottom: 2px solid #22D3EE;
    }

    /* Заголовки */
    h1 {
        font-weight: 800;
        background: linear-gradient(90deg, #EAF0FF, #22D3EE);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        letter-spacing: 2px;
    }
    
    /* Прогресс бар */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #22D3EE, #8B5CF6);
    }
</style>
""", unsafe_allow_html=True)

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
    # При регистрации Streak = 0
    row = [username, pin, 0, today_str, today_str, "{}", "[]", "FALSE"]
    sheet.append_row(row)
    return "OK"

def update_db_field(row_num, col_num, value):
    sheet = get_db()
    if sheet: sheet.update_cell(row_num, col_num, value)

def save_history(row_num, messages):
    try:
        history_str = json.dumps(messages[-30:]) 
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
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h1>MUKTI PORTAL</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94a3b8; margin-bottom: 30px;'>Система освобождения сознания</p>", unsafe_allow_html=True)
    
    # Стеклянный контейнер для входа
    st.markdown('<div class="glass-container">', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["ВХОД", "НОВАЯ ЖИЗНЬ (РЕГИСТРАЦИЯ)"])
    
    with tab1: # ВХОД
        st.write("")
        l_user = st.text_input("Твое Имя", key="l_u")
        l_pin = st.text_input("PIN-код (4 цифры)", type="password", key="l_p", max_chars=4)
        
        if st.button("ВОЙТИ", use_container_width=True):
            with st.spinner("Синхронизация..."):
                user_data, row_num = load_user(l_user)
                if user_data and str(user_data[1]) == str(l_pin):
                    # === ЛОГИКА ВХОДА ===
                    st.session_state.logged_in = True
                    st.session_state.username = l_user
                    st.session_state.row_num = row_num
                    st.session_state.streak = int(user_data[2]) if len(user_data) > 2 else 0
                    st.session_state.last_active = user_data[3] if len(user_data) > 3 else str(date.today())
                    st.session_state.reg_date = user_data[4] if len(user_data) > 4 else str(date.today())
                    st.session_state.vip = (str(user_data[7]).upper() == "TRUE") if len(user_data) > 7 else False
                    
                    try: st.session_state.messages = json.loads(user_data[6]) if len(user_data) > 6 else []
                    except: st.session_state.messages = []

                    # Проверяем, прошел ли онбординг
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

    with tab2: # РЕГИСТРАЦИЯ (АВТО-ВХОД)
        st.write("")
        st.info("Придумай Имя и PIN. Система запомнит тебя.")
        r_user = st.text_input("Новое Имя", key="r_u")
        r_pin = st.text_input("Новый PIN (4 цифры)", type="password", key="r_p", max_chars=4)
        
        if st.button("НАЧАТЬ ПУТЬ (РЕГИСТРАЦИЯ)", use_container_width=True):
            if r_user and len(r_pin) == 4:
                res = register_user(r_user, r_pin)
                if res == "OK":
                    # === АВТОМАТИЧЕСКИЙ ВХОД ПОСЛЕ РЕГИСТРАЦИИ ===
                    with st.spinner("Создание нейросвязей..."):
                        # Сразу загружаем созданного пользователя
                        time.sleep(1) # Даем базе секунду на запись
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
                            
                            # Сразу кидаем на этап онбординга
                            st.session_state.onboarding_step = 0 
                            
                            st.success("Профиль создан! Входим...")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Ошибка авто-входа. Попробуй войти вручную.")
                elif res == "TAKEN":
                    st.error("Это Имя уже занято. Выбери другое.")
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
        st.markdown(f"<h2 style='text-align:center;'>НАСТРОЙКА ПРОТОКОЛА</h2>", unsafe_allow_html=True)
        
        # Стеклянный контейнер для диалога настройки
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)

        if st.session_state.onboarding_step == 0:
            st.write(f"👋 **Приветствую, {st.session_state.username}.**")
            st.write("Я MUKTI. Прежде чем мы начнем перепрошивку, скажи: ты читал книгу **'Кто такой Алкоголь'**? Это база нашей работы.")
            
            c1, c2 = st.columns(2)
            if c1.button("ДА, Я В ТЕМЕ", use_container_width=True):
                update_onboarding_data(st.session_state.row_num, "read_book", True)
                st.session_state.onboarding_step = 1
                st.rerun()
            if c2.button("НЕТ, НЕ ЧИТАЛ", use_container_width=True):
                st.info("Без теории практика слаба. Но мы начнем.")
                st.markdown("👉 [**Скачать книгу на LitRes**](https://www.litres.ru/book/roman-vybornov/pochemu-ya-nikogo-ne-em-72075331/)")
                if st.button("Продолжить без книги", use_container_width=True):
                    update_onboarding_data(st.session_state.row_num, "read_book", False)
                    st.session_state.onboarding_step = 1
                    st.rerun()
                    
        elif st.session_state.onboarding_step == 1:
            st.write("🎯 **Калибровка цели.**")
            st.write("Напиши мне в чат ниже: **Что тебя мотивирует больше всего?** (Семья, Деньги, Здоровье, Свобода...)")
            
            if goal_input := st.chat_input("Моя цель..."):
                update_onboarding_data(st.session_state.row_num, "goal", goal_input)
                st.session_state.onboarding_step = 2
                st.rerun()
                
        elif st.session_state.onboarding_step == 2:
            st.write("⚓️ **Последний вопрос.**")
            st.write("Что остановит тебя в момент срыва? Твой **'Стоп-фактор'**? (Звонок, воспоминание, страх...)")
            
            if trigger_input := st.chat_input("Меня остановит..."):
                data = update_onboarding_data(st.session_state.row_num, "stop_factor", trigger_input)
                st.session_state.stop_factor = trigger_input
                
                # Финал
                st.session_state.onboarding_step = -1
                welcome_msg = "Профиль настроен. Я активировал защиту. Жми 'Сегодня чист', чтобы запустить таймер."
                st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
                save_history(st.session_state.row_num, st.session_state.messages)
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

    # --- ОСНОВНОЙ РАБОЧИЙ СТОЛ ---
    else:
        # SOS LOGIC
        if "sos_mode" not in st.session_state: st.session_state.sos_mode = False

        if st.session_state.sos_mode:
            st.markdown("""
            <div style="background: rgba(220, 38, 38, 0.15); border: 1px solid #ef4444; padding: 20px; border-radius: 16px; text-align: center; margin-bottom: 20px; backdrop-filter: blur(10px); box-shadow: 0 0 30px rgba(220,38,38, 0.4);">
                <h2 style="color: #fca5a5; margin:0; text-shadow: 0 0 10px #ef4444; letter-spacing: 3px;">⚠️ АТАКА ПАРАЗИТА</h2>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"<div style='text-align:center; margin-bottom:20px;'>Твой якорь:<br><strong style='font-size:24px; color:#22D3EE;'>{st.session_state.stop_factor}</strong></div>", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            c1.info("💨 **ДЫХАНИЕ**\n\n4 сек Вдох -> 4 сек Пауза -> 4 сек Выдох.\n\nПовтори 5 раз.")
            c2.warning("⚡️ **ДЕЙСТВИЕ**\n\n20 приседаний.\n\nПрямо сейчас. Сжги адреналин.")
            
            if st.button("Я ВЕРНУЛ КОНТРОЛЬ", use_container_width=True):
                st.session_state.sos_mode = False
                st.session_state.messages.append({"role": "assistant", "content": "Сигнал принят. Ты справился. Горжусь."})
                save_history(st.session_state.row_num, st.session_state.messages)
                st.rerun()

        else:
            # HEADER
            st.markdown(f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;'><div style='font-weight:800; font-size:20px; color:#EAF0FF;'>MUKTI <span style='color:#22D3EE;'>//</span> ONLINE</div><div style='text-align:right; font-size:12px; color:#94a3b8;'>АГЕНТ<br><span style='color:#22D3EE;'>{st.session_state.username}</span></div></div>", unsafe_allow_html=True)
            
            # DASHBOARD (GLASS)
            st.markdown('<div class="glass-container" style="padding: 15px; margin-bottom: 20px;">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 1.5, 1])
            
            with col1:
                 st.markdown(f"<div style='text-align:center;'><div style='font-size: 10px; color: #94a3b8; letter-spacing: 2px; text-transform:uppercase;'>Свобода</div><div style='font-size: 36px; font-weight:bold; color: #fff; text-shadow: 0 0 15px rgba(34, 211, 238, 0.6);'>{st.session_state.streak}</div></div>", unsafe_allow_html=True)
            
            with col2:
                # LOGIC BUTTON
                today = date.today()
                try: last_active = datetime.strptime(st.session_state.last_active, "%Y-%m-%d").date()
                except: last_active = today
                
                delta = (today - last_active).days
                
                if delta == 0 and st.session_state.streak > 0:
                    st.button("✅ ЗАЧТЕНО", disabled=True, use_container_width=True)
                else:
                    if st.button("✨ СЕГОДНЯ ЧИСТ", use_container_width=True):
                        if delta > 1 and st.session_state.streak > 0:
                             new_streak = 1
                             st.toast("Счетчик перезапущен.", icon="🔄")
                        else:
                             new_streak = st.session_state.streak + 1
                             st.toast("Система обновлена.", icon="🔋")
                             
                        update_db_field(st.session_state.row_num, 3, new_streak)
                        update_db_field(st.session_state.row_num, 4, str(today))
                        st.session_state.streak = new_streak
                        st.session_state.last_active = str(today)
                        st.rerun()
            
            with col3:
                # Специальный стиль для кнопки SOS (красный) внутри колонки
                if st.button("🚨 SOS", use_container_width=True):
                    st.session_state.sos_mode = True
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)

            # CHAT AREA
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            
            # LIMITS
            locked = False
            if not st.session_state.vip:
                 try: reg_d = datetime.strptime(st.session_state.reg_date, "%Y-%m-%d").date()
                 except: reg_d = date.today()
                 limit = 7 if (date.today() - reg_d).days == 0 else 3
                 msgs_today = sum(1 for m in st.session_state.messages if m["role"] == "user")
                 if msgs_today >= limit: locked = True

            if locked:
                st.info(f"🔒 Лимит энергии ({limit}) исчерпан.")
                code = st.text_input("Ввести код MUKTI BOSS")
                if st.button("АКТИВИРОВАТЬ"):
                    if code == VIP_CODE:
                        update_db_field(st.session_state.row_num, 8, "TRUE")
                        st.session_state.vip = True
                        st.rerun()
            else:
                if prompt := st.chat_input("Введи сообщение..."):
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.markdown(prompt)
                    
                    with st.chat_message("assistant"):
                        with st.spinner("Анализ..."):
                            system_prompt = f"""
                            Ты - MUKTI. Пользователь: {st.session_state.username}.
                            Стиль: Технологичный, краткий, поддерживающий. Кибер-наставник.
                            
                            ИНСТРУКЦИИ:
                            1. Ответы краткие (3-4 предложения).
                            2. Задавай вопросы, развивай диалог.
                            3. Называй алкоголь "Паразит".
                            
                            БАЗА: {BOOK_SUMMARY}
                            МОТИВАЦИЯ ЮЗЕРА: {st.session_state.get('stop_factor')}
                            """
                            full_prompt = f"{system_prompt}\nИстория:\n{st.session_state.messages[-5:]}\nUser: {prompt}"
                            
                            try:
                                response = model.generate_content(full_prompt).text
                                st.markdown(response)
                                st.session_state.messages.append({"role": "assistant", "content": response})
                                save_history(st.session_state.row_num, st.session_state.messages)
                            except Exception as e:
                                st.error("Сбой связи.")

        # FOOTER
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.sidebar.button("ВЫХОД ИЗ СИСТЕМЫ"):
             st.session_state.logged_in = False
             st.rerun()
