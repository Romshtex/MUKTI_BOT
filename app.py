import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
import time
import json
import base64
import os
import random

# --- 1. КОНСТАНТЫ И НАСТРОЙКИ ---
LIMIT_NEW_USER = 10
LIMIT_OLD_USER = 5
HISTORY_DEPTH = 30
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
            if p in available_models: return genai.GenerativeModel(p)
        if available_models: return genai.GenerativeModel(available_models[0])
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

bg_file = "matrix_bg.jpg"
if not os.path.exists(bg_file): bg_file = "matrix_bg.png"
if not os.path.exists(bg_file): bg_file = "background.jpg"
bin_str = get_base64_of_bin_file(bg_file)

css_code = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Orbitron:wght@400;500;700&display=swap');

    /* БАЗА */
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

    /* GLASSMORPHISM */
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

    /* ТИПОГРАФИКА */
    h1 {{
        font-family: 'Orbitron', sans-serif;
        color: #EAEAEA;
        text-transform: uppercase;
        letter-spacing: 4px;
        text-align: center;
        transition: 0.4s;
    }}
    h1:hover {{
        color: #FFFFFF;
        text-shadow: 0 0 15px rgba(0, 230, 118, 0.8), 0 0 30px rgba(0, 230, 118, 0.4);
    }}
    h2, h3 {{ font-family: 'Orbitron', sans-serif; color: #EAEAEA; }}
    p, li {{ color: #CCCCCC; font-weight: 300; line-height: 1.6; }}
    ul {{ list-style-type: none; padding: 0; }}
    li::before {{ content: "▪ "; color: #00E676; }}

    /* ИНПУТЫ */
    .stTextInput > div > div > input {{
        background: rgba(10, 10, 10, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        color: #00E676 !important;
        border-radius: 12px;
        height: 50px;
    }}
    .stTextInput > div > div > input:focus {{
        border-color: #00E676 !important;
        box-shadow: 0 0 15px rgba(0, 230, 118, 0.2);
    }}

    /* КНОПКИ */
    .stButton > button {{
        background: transparent !important;
        border: 1px solid #00E676 !important;
        color: #00E676 !important;
        border-radius: 12px;
        height: 50px;
        font-family: 'Orbitron', sans-serif;
        text-transform: uppercase;
        transition: 0.3s;
    }}
    .stButton > button:hover {{
        background: rgba(0, 230, 118, 0.05) !important;
        color: #FFFFFF !important;
        box-shadow: 0 0 15px rgba(0, 230, 118, 0.5);
        transform: translateY(-1px);
    }}

    /* SOS КНОПКА */
    div[data-testid="column"]:nth-of-type(3) .stButton > button {{
        border-color: #FF3D00 !important; color: #FF3D00 !important;
    }}
    div[data-testid="column"]:nth-of-type(3) .stButton > button:hover {{
        background: rgba(255, 61, 0, 0.1) !important;
        box-shadow: 0 0 20px rgba(255, 61, 0, 0.6);
    }}

    /* ЧАТ */
    .stChatMessage {{
        background: rgba(30, 30, 30, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 16px;
    }}
    
    a {{ color: #00E676; text-decoration: none; }}
</style>
"""
if not bin_str: css_code = css_code.replace('background-image: url("data:image/jpg;base64,None");', 'background-color: #000000;')
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
    today = str(date.today())
    row = [username, pin, 0, today, today, "{}", "[]", "FALSE"]
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

def get_onboarding_data(row_num):
    sheet = get_db()
    if sheet:
        try:
            current_json = sheet.cell(row_num, 6).value
            return json.loads(current_json) if current_json else {}
        except: return {}
    return {}

# --- 5. ЛОГИКА ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "calibration_step" not in st.session_state: st.session_state.calibration_step = 0 # 0=нет, 1-4=вопросы

# === ЛЕНДИНГ И ВХОД ===
if not st.session_state.logged_in:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h1>MUKTI</h1>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center; color:#00E676; margin-bottom:30px; letter-spacing:1px;'>Твой персональный ИИ-ассистент для выхода из зависимости</div>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="glass-container">
        <ul style="padding-left: 10px;">
            <li style="margin-bottom: 15px;"><b>💠 Интеллект:</b><br>Не просто трекер, а диалог с понимающим ассистентом и наставником 24/7.</li>
            <li style="margin-bottom: 15px;"><b>🛡 Защита:</b><br>Кнопка SOS и нейро-техники сброса тяги: от "ледяного шока" до перепрошивки триггеров.</li>
            <li style="margin-bottom: 0px;"><b>🧠 Философия:</b><br>Основано на методике разделения Личности и "Паразита".</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["ВХОД В СИСТЕМУ", "СОЗДАТЬ АККАУНТ"])
    
    with tab1:
        l_u = st.text_input("ИМЯ", key="l_u")
        l_p = st.text_input("PIN", type="password", key="l_p", max_chars=4)
        if st.button("ВОЙТИ", use_container_width=True):
            user_data, row_num = load_user(l_u)
            if user_data and str(user_data[1]) == str(l_p):
                st.session_state.logged_in = True
                st.session_state.username = l_u
                st.session_state.row_num = row_num
                st.session_state.streak = int(user_data[2]) if len(user_data) > 2 else 0
                st.session_state.last_active = user_data[3] if len(user_data) > 3 else str(date.today())
                st.session_state.reg_date = user_data[4] if len(user_data) > 4 else str(date.today())
                st.session_state.vip = (str(user_data[7]).upper() == "TRUE") if len(user_data) > 7 else False
                try: st.session_state.messages = json.loads(user_data[6]) if len(user_data) > 6 else []
                except: st.session_state.messages = []
                st.session_state.user_profile = get_onboarding_data(row_num)
                st.rerun()
            else: st.error("Ошибка доступа.")

    with tab2:
        r_u = st.text_input("НОВОЕ ИМЯ", key="r_u")
        r_p = st.text_input("НОВЫЙ PIN", type="password", key="r_p", max_chars=4)
        if st.button("ЗАРЕГИСТРИРОВАТЬСЯ", use_container_width=True):
            if r_u and len(r_p) == 4:
                if register_user(r_u, r_p) == "OK":
                    st.success("Аккаунт создан! Входим...")
                    time.sleep(1)
                    # Авто-вход
                    user_data, row_num = load_user(r_u)
                    st.session_state.logged_in = True
                    st.session_state.username = r_u
                    st.session_state.row_num = row_num
                    st.session_state.streak = 0
                    st.session_state.last_active = str(date.today())
                    st.session_state.reg_date = str(date.today())
                    st.session_state.vip = False
                    st.session_state.messages = []
                    st.session_state.user_profile = {}
                    st.rerun()
                else: st.error("Имя занято.")
            else: st.warning("Заполни поля.")

# === ВНУТРИ СИСТЕМЫ ===
else:
    # SOS LOGIC (ОБНОВЛЕННАЯ)
    if "sos_mode" not in st.session_state: st.session_state.sos_mode = False

    if st.session_state.sos_mode:
        # Случайный выбор одной из 3-х техник
        if "sos_technique" not in st.session_state:
            techniques = [
                {"name": "❄️ ЛЕДЯНОЙ СБРОС", "desc": "Включи холодную воду. Подержи запястья под струей 30 секунд или умой лицо ледяной водой.\n\nЭто активирует 'рефлекс ныряльщика' и мгновенно гасит панику."},
                {"name": "⏪ ПЕРЕМОТКА ПЛЕНКИ", "desc": "Не думай о первом глотке. Проиграй кино до конца.\nПредставь завтрашнее утро. Головную боль. Стыд. Вкус во рту.\nПосмотри в самый конец этого сценария прямо сейчас."},
                {"name": "🗣 ИМЯ ВРАГА", "desc": "Скажи вслух: 'Это не я хочу выпить. Это Паразит умирает и просит еды. Я не буду его кормить'.\n\nРаздели себя и Голос Зависимости."}
            ]
            st.session_state.sos_technique = random.choice(techniques)
        
        tech = st.session_state.sos_technique
        
        st.markdown(f"""
        <div style="background: rgba(40, 0, 0, 0.8); border: 1px solid #FF3D00; padding: 25px; border-radius: 20px; text-align: center; margin-bottom: 25px; backdrop-filter: blur(20px);">
            <h2 style="color: #FF3D00; margin:0; letter-spacing: 3px;">{tech['name']}</h2>
        </div>
        """, unsafe_allow_html=True)
        
        st.info(tech['desc'])
        
        if st.button("Я ВЕРНУЛ КОНТРОЛЬ", use_container_width=True):
            st.session_state.sos_mode = False
            del st.session_state.sos_technique # Сброс техники
            msg = "Сигнал принят. Ты справился. Горжусь.\n\nРасскажи, что именно спровоцировало тягу? Мы должны знать врага."
            st.session_state.messages.append({"role": "assistant", "content": msg})
            save_history(st.session_state.row_num, st.session_state.messages)
            st.rerun()

    else:
        # HEADER
        st.markdown(f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;'><div style='font-family: Orbitron; font-weight:800; font-size:20px; color:#EAEAEA; letter-spacing:2px;'>MUKTI <span style='color:#00E676; font-size:14px;'>// ONLINE</span></div><div style='text-align:right; font-size:12px; color:#888;'>АГЕНТ<br><span style='color:#00E676; font-family:Orbitron;'>{st.session_state.username}</span></div></div>", unsafe_allow_html=True)
        
        # DASHBOARD
        st.markdown('<div class="glass-container" style="padding: 20px; margin-bottom: 25px;">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.5, 1])
        
        with col1:
             st.markdown(f"<div style='text-align:center;'><div style='font-size: 10px; color: #888; letter-spacing: 2px; text-transform:uppercase;'>Дней</div><div style='font-family: Orbitron; font-size: 42px; font-weight:800; color: #fff; text-shadow: 0 0 20px rgba(0, 230, 118, 0.4);'>{st.session_state.streak}</div></div>", unsafe_allow_html=True)
        
        with col2:
            today = date.today()
            try: last_active = datetime.strptime(str(st.session_state.last_active), "%Y-%m-%d").date()
            except: last_active = today
            delta = (today - last_active).days
            
            if delta == 0 and st.session_state.streak > 0:
                st.button("✅ ЗАЧТЕНО", disabled=True, use_container_width=True)
            else:
                if st.button("✨ СЕГОДНЯ ЧИСТ", use_container_width=True):
                    # ЛОГИКА КАЛИБРОВКИ
                    # Если профиль пуст (нет ключа 'frequency'), запускаем калибровку
                    profile = st.session_state.get('user_profile', {})
                    if 'frequency' not in profile:
                        st.session_state.calibration_step = 1
                        first_msg = "День зачтен. Фундамент заложен.\n\nЧтобы я мог эффективно прикрывать тебя, мне нужно настроить радары на Врага. Ответь на 4 вопроса.\n\n1. **Как часто Паразит обычно атакует?** (Каждый день, по пятницам, запоями?)"
                    else:
                        st.session_state.calibration_step = 0
                        if delta > 1 and st.session_state.streak > 0:
                            first_msg = "Счетчик перезапущен. Срыв — это урок. Что случилось?"
                        else:
                            first_msg = "День зафиксирован. Ты становишься сильнее. Как твое состояние?"

                    # Обновляем счетчик
                    new_streak = 1 if delta > 1 and st.session_state.streak > 0 else st.session_state.streak + 1
                    update_db_field(st.session_state.row_num, 3, new_streak)
                    update_db_field(st.session_state.row_num, 4, str(today))
                    st.session_state.streak = new_streak
                    st.session_state.last_active = str(today)
                    
                    st.session_state.messages.append({"role": "assistant", "content": first_msg})
                    save_history(st.session_state.row_num, st.session_state.messages)
                    st.rerun()
        
        with col3:
            if st.button("🚨 SOS", use_container_width=True):
                st.session_state.sos_mode = True
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

        # CHAT
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # INPUT LOGIC
        if prompt := st.chat_input("Ввод данных..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)

            # === ЛОГИКА КАЛИБРОВКИ (ВОПРОСЫ) ===
            step = st.session_state.calibration_step
            if step > 0:
                next_msg = ""
                # Сохраняем ответ на ПРЕДЫДУЩИЙ вопрос
                if step == 1:
                    update_onboarding_data(st.session_state.row_num, "frequency", prompt)
                    next_msg = "Принято. Вопрос 2.\n**В какие моменты тяга самая сильная?** (Стресс, скука, одиночество, компании?)"
                    st.session_state.calibration_step = 2
                elif step == 2:
                    update_onboarding_data(st.session_state.row_num, "triggers", prompt)
                    next_msg = "Записал. Вопрос 3.\n**Твой опыт борьбы?** (Это первая попытка или были срывы?)"
                    st.session_state.calibration_step = 3
                elif step == 3:
                    update_onboarding_data(st.session_state.row_num, "history", prompt)
                    next_msg = "Понял. Последний вопрос.\n**Что ты чувствуешь прямо сейчас?** (Страх, уверенность, вину, пустоту?)"
                    st.session_state.calibration_step = 4
                elif step == 4:
                    update_onboarding_data(st.session_state.row_num, "state", prompt)
                    st.session_state.user_profile = get_onboarding_data(st.session_state.row_num) # Обновляем локально
                    next_msg = "Калибровка завершена. Профиль Врага создан. Я активировал персональный протокол защиты.\n\nЯ на связи. Если накроет — жми SOS."
                    st.session_state.calibration_step = 0 # Конец
                
                with st.chat_message("assistant"):
                    st.markdown(next_msg)
                    st.session_state.messages.append({"role": "assistant", "content": next_msg})
                    save_history(st.session_state.row_num, st.session_state.messages)
            
            # === ОБЫЧНЫЙ РЕЖИМ (AI) ===
            else:
                # Проверка лимитов
                limit = LIMIT_NEW_USER if st.session_state.streak < 3 else LIMIT_OLD_USER
                if not st.session_state.vip and sum(1 for m in st.session_state.messages if m["role"] == "user") >= limit:
                    msg = "🔒 Лимит исчерпан. Для снятия пиши **MUKTI** Роману: t.me/Vybornov_Roman"
                    st.session_state.messages.append({"role": "assistant", "content": msg})
                    st.rerun()
                else:
                    with st.chat_message("assistant"):
                        with st.spinner("PROCESSING..."):
                            # Формируем контекст из профиля
                            profile = st.session_state.get('user_profile', {})
                            context_str = f"""
                            Профиль пользователя:
                            - Частота: {profile.get('frequency', 'Неизвестно')}
                            - Триггеры: {profile.get('triggers', 'Неизвестно')}
                            - Опыт: {profile.get('history', 'Неизвестно')}
                            """
                            
                            system_prompt = f"""
                            Ты MUKTI. Пользователь: {st.session_state.username}.
                            {context_str}
                            Твоя роль: Друг, Наставник.
                            Стиль: Простой, человеческий, без пафоса. Алкоголь = "Паразит".
                            БАЗА ЗНАНИЙ: {BOOK_SUMMARY}
                            """
                            full_prompt = f"{system_prompt}\nИстория:\n{st.session_state.messages[-5:]}\nUser: {prompt}"
                            
                            try:
                                response_text = None
                                for i in range(3):
                                    if model:
                                        try:
                                            response_text = model.generate_content(full_prompt).text
                                            break
                                        except: time.sleep(1)
                                if response_text:
                                    st.markdown(response_text)
                                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                                    save_history(st.session_state.row_num, st.session_state.messages)
                                else: st.error("Сбой связи.")
                            except: st.error("Ошибка.")

    # FOOTER
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.sidebar.button("LOGOUT"):
            st.session_state.logged_in = False
            st.rerun()
