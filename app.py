import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
import time
import json
import random

# --- 1. НАСТРОЙКИ И КОНСТАНТЫ ---
try:
    from book import FULL_BOOK_TEXT, BOOK_SUMMARY
except ImportError:
    FULL_BOOK_TEXT = "Текст книги недоступен."
    BOOK_SUMMARY = "Философия освобождения от зависимости."

GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"] if "GOOGLE_API_KEY" in st.secrets else "NO_KEY"
VIP_CODE = "MUKTI_BOSS"

genai.configure(api_key=GOOGLE_API_KEY)

# --- 2. УМНОЕ ПОДКЛЮЧЕНИЕ МОЗГОВ ---
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

# --- 3. ДИЗАЙН "CYBERPUNK GLASS" ---
st.set_page_config(page_title="MUKTI PORTAL", page_icon="💠", layout="centered")

st.markdown("""
<style>
    /* 1. ГЛУБОКИЙ ФОН (КОСМОС) */
    .stApp {
        background: radial-gradient(circle at center, #1e1b4b 0%, #0f172a 40%, #020617 100%);
        background-attachment: fixed;
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }

    /* 2. ЭФФЕКТ СТЕКЛА (GLASSMORPHISM) ДЛЯ БЛОКОВ */
    .glass-panel {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
    }
    
    /* Сообщения чата - тоже стекло */
    .stChatMessage {
        background: rgba(15, 23, 42, 0.6);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        transition: all 0.3s ease;
    }
    .stChatMessage:hover {
        background: rgba(30, 41, 59, 0.7);
        border-color: rgba(14, 165, 233, 0.3);
    }

    /* 3. ПОЛЯ ВВОДА (НЕОН) */
    .stTextInput > div > div > input {
        background-color: rgba(15, 23, 42, 0.8) !important;
        color: #0ea5e9 !important;
        border: 1px solid #1e293b !important;
        border-radius: 10px;
        transition: 0.3s;
    }
    .stTextInput > div > div > input:focus {
        border-color: #0ea5e9 !important;
        box-shadow: 0 0 15px rgba(14, 165, 233, 0.4);
    }

    /* 4. КНОПКИ (СВЕЧЕНИЕ) */
    .stButton > button {
        background: linear-gradient(135deg, #0ea5e9 0%, #3b82f6 100%);
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        letter-spacing: 1px;
        transition: all 0.4s ease;
        text-transform: uppercase;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 0 20px rgba(14, 165, 233, 0.6);
    }

    /* Скроллбар */
    ::-webkit-scrollbar {
        width: 8px;
        background: #020617;
    }
    ::-webkit-scrollbar-thumb {
        background: #1e293b;
        border-radius: 4px;
    }
    
    /* Заголовки */
    h1, h2, h3 {
        color: #f8fafc;
        text-shadow: 0 0 10px rgba(255,255,255,0.3);
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
        # Fallback for root secrets
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
    # F = onboarding (пусто в начале), G = history, H = vip
    # Мы сохраняем PIN в колонку password
    row = [username, pin, 0, today_str, today_str, "{}", "[]", "FALSE"]
    sheet.append_row(row)
    return "OK"

def update_db_field(row_num, col_num, value):
    sheet = get_db()
    if sheet: sheet.update_cell(row_num, col_num, value)

def save_history(row_num, messages):
    # Сохраняем последние 30 сообщений
    try:
        history_str = json.dumps(messages[-30:])
        update_db_field(row_num, 7, history_str)
    except: pass

def update_onboarding_data(row_num, key, value):
    # Читаем, обновляем JSON, пишем обратно
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
    st.session_state.onboarding_step = -1 # -1 = завершено, 0-3 = этапы

# === ЭКРАН ВХОДА (ПОРТАЛ) ===
if not st.session_state.logged_in:
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; font-weight: 300; letter-spacing: 5px; color: #0ea5e9;'>MUKTI <span style='font-size: 20px; color: #64748b;'>// ПОРТАЛ</span></h1>", unsafe_allow_html=True)
    
    # Стеклянная панель входа
    st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔒 ВХОД", "🆕 РЕГИСТРАЦИЯ"])
    
    with tab1:
        st.write(" ")
        l_user = st.text_input("Твое Имя", key="l_u")
        l_pin = st.text_input("PIN-код (4 цифры)", type="password", key="l_p", max_chars=4)
        
        if st.button("ВОЙТИ В СИСТЕМУ", use_container_width=True):
            with st.spinner("Идентификация биоритмов..."):
                user_data, row_num = load_user(l_user)
                if user_data and str(user_data[1]) == str(l_pin):
                    st.session_state.logged_in = True
                    st.session_state.username = l_user
                    st.session_state.row_num = row_num
                    
                    # Загрузка данных
                    st.session_state.streak = int(user_data[2]) if len(user_data) > 2 else 0
                    st.session_state.last_active = user_data[3] if len(user_data) > 3 else str(date.today())
                    st.session_state.reg_date = user_data[4] if len(user_data) > 4 else str(date.today())
                    st.session_state.vip = (str(user_data[7]).upper() == "TRUE") if len(user_data) > 7 else False
                    
                    # История
                    try: st.session_state.messages = json.loads(user_data[6]) if len(user_data) > 6 else []
                    except: st.session_state.messages = []

                    # Проверка онбординга
                    try:
                        ob_data = json.loads(user_data[5])
                        st.session_state.stop_factor = ob_data.get("stop_factor", "Свобода")
                        # Если данные есть, онбординг завершен (-1), если нет - начинаем (0)
                        if "goal" in ob_data and "stop_factor" in ob_data:
                            st.session_state.onboarding_step = -1
                        else:
                            st.session_state.onboarding_step = 0
                    except:
                        st.session_state.onboarding_step = 0
                        st.session_state.stop_factor = "Свобода"
                    
                    st.rerun()
                else:
                    st.error("Доступ запрещен. Неверное Имя или PIN.")

    with tab2:
        st.write(" ")
        st.info("Придумай Имя и 4 цифры PIN-кода. Запомни их. Это твой ключ.")
        r_user = st.text_input("Придумай Имя", key="r_u")
        r_pin = st.text_input("Придумай PIN (4 цифры)", type="password", key="r_p", max_chars=4)
        
        if st.button("СОЗДАТЬ ПРОФИЛЬ", use_container_width=True):
            if r_user and len(r_pin) == 4:
                res = register_user(r_user, r_pin)
                if res == "OK":
                    st.success("Профиль создан. Теперь войди.")
                elif res == "TAKEN":
                    st.error("Имя занято.")
                else:
                    st.error("Ошибка сети.")
            else:
                st.warning("Введи имя и 4 цифры PIN.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# === ВНУТРИ СИСТЕМЫ ===
else:
    # --- ОНБОРДИНГ (ЕСЛИ НОВЫЙ) ---
    if st.session_state.onboarding_step >= 0:
        
        st.title("НАСТРОЙКА СВЯЗИ")
        
        # Чат онбординга (только вывод)
        onboard_history = []
        if st.session_state.onboarding_step == 0:
            st.chat_message("assistant").write(f"Приветствую, {st.session_state.username}. Я MUKTI. Прежде чем мы начнем работу, ответь: ты уже знаком с Книгой 'Кто такой Алкоголь'? Это важно, чтобы мы говорили на одном языке.")
            
            c1, c2 = st.columns(2)
            if c1.button("Да, я в теме"):
                update_onboarding_data(st.session_state.row_num, "read_book", True)
                st.session_state.onboarding_step = 1
                st.rerun()
            if c2.button("Нет, не читал"):
                st.info("Рекомендую начать с теории. Без понимания врага его сложно победить.")
                st.markdown("[📖 Скачать книгу на LitRes](https://www.litres.ru/book/roman-vybornov/pochemu-ya-nikogo-ne-em-72075331/)") # Твоя ссылка
                if st.button("Я прочитаю позже, давай начнем"):
                    update_onboarding_data(st.session_state.row_num, "read_book", False)
                    st.session_state.onboarding_step = 1
                    st.rerun()
                    
        elif st.session_state.onboarding_step == 1:
            st.chat_message("assistant").write("Принято. Теперь калибровка целей. Напиши мне: **Что является твоей главной мотивацией?** Ради чего ты хочешь обрести свободу? (Семья, Деньги, Здоровье, Самоуважение...)")
            
            if goal_input := st.chat_input("Моя мотивация - это..."):
                st.chat_message("user").write(goal_input)
                update_onboarding_data(st.session_state.row_num, "goal", goal_input)
                st.session_state.onboarding_step = 2
                time.sleep(1)
                st.rerun()
                
        elif st.session_state.onboarding_step == 2:
            st.chat_message("assistant").write("Зафиксировано. Последний вопрос настройки. **Что может остановить тебя в момент срыва?** Вспомни то, что отрезвляет тебя мгновенно. (Звонок другу, взгляд ребенка, воспоминание о похмелье...)")
            
            if trigger_input := st.chat_input("Меня остановит..."):
                st.chat_message("user").write(trigger_input)
                data = update_onboarding_data(st.session_state.row_num, "stop_factor", trigger_input)
                st.session_state.stop_factor = trigger_input
                
                # Завершаем онбординг
                st.session_state.onboarding_step = -1
                
                # Добавляем первое приветствие в основной чат
                welcome_msg = "Настройка завершена. Я активировал режим поддержки. Помни: ты не бросаешь, ты освобождаешься. Я рядом. Жми 'Сегодня чист', чтобы запустить таймер свободы."
                st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
                save_history(st.session_state.row_num, st.session_state.messages)
                st.rerun()

    # --- ОСНОВНОЙ ИНТЕРФЕЙС (КОГДА ОНБОРДИНГ ПРОЙДЕН) ---
    else:
        # ЛОГИКА SOS
        if "sos_mode" not in st.session_state: st.session_state.sos_mode = False

        if st.session_state.sos_mode:
            st.markdown("""
            <div style="background: rgba(239, 68, 68, 0.1); border: 2px solid #ef4444; padding: 20px; border-radius: 16px; text-align: center; margin-bottom: 20px; backdrop-filter: blur(10px);">
                <h2 style="color: #fca5a5; margin:0; text-shadow: 0 0 10px #ef4444;">⚠️ АТАКА ПАРАЗИТА</h2>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"<h3 style='text-align:center;'>⚓️ ЯКОРЬ: <span style='color:#0ea5e9'>{st.session_state.stop_factor}</span></h3>", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            c1.info("💨 **ДЫХАНИЕ**\n\n4 сек Вдох -> 4 сек Пауза -> 4 сек Выдох.\nПовтори 5 раз.")
            c2.warning("⚡️ **ДЕЙСТВИЕ**\n\n20 приседаний. Прямо сейчас.\nСжги адреналин.")
            
            if st.button("Я ВЕРНУЛ КОНТРОЛЬ. ОТБОЙ.", use_container_width=True):
                st.session_state.sos_mode = False
                st.session_state.messages.append({"role": "assistant", "content": "Отличная работа. Ты удержал штурвал. Это победа."})
                save_history(st.session_state.row_num, st.session_state.messages)
                st.rerun()

        else:
            # ВЕРХНЯЯ ПАНЕЛЬ
            st.markdown(f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;'><h2 style='margin:0;'>MUKTI <span style='font-size:14px; color:#0ea5e9; vertical-align:middle;'>// ONLINE</span></h2><div style='text-align:right;'><span style='color:#94a3b8; font-size:12px;'>АГЕНТ</span><br>{st.session_state.username}</div></div>", unsafe_allow_html=True)
            
            # ПАНЕЛЬ СТАТИСТИКИ И ДЕЙСТВИЙ (СТЕКЛО)
            st.markdown('<div class="glass-panel" style="padding: 15px; margin-bottom: 20px;">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 1.5, 1])
            
            with col1:
                 st.markdown(f"<div style='text-align:center;'><div style='font-size: 10px; color: #94a3b8; letter-spacing: 2px;'>СВОБОДА</div><div style='font-size: 32px; font-weight:bold; color: #fff; text-shadow: 0 0 10px #0ea5e9;'>{st.session_state.streak}<span style='font-size:12px;'> ДН.</span></div></div>", unsafe_allow_html=True)
            
            with col2:
                # ЛОГИКА КНОПКИ
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
                             st.toast("Счетчик перезапущен. Новая попытка.", icon="🔄")
                        else:
                             new_streak = st.session_state.streak + 1
                             st.toast("Энергия восстановлена +1", icon="🔋")
                             
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

            # ЧАТ
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            
            # ЛОГИКА ЛИМИТОВ
            locked = False
            if not st.session_state.vip:
                 try: reg_d = datetime.strptime(st.session_state.reg_date, "%Y-%m-%d").date()
                 except: reg_d = date.today()
                 limit = 7 if (date.today() - reg_d).days == 0 else 3
                 msgs_today = sum(1 for m in st.session_state.messages if m["role"] == "user")
                 if msgs_today >= limit: locked = True

            if locked:
                st.info(f"🔒 Лимит энергии ({limit}) исчерпан. Система перезаряжается до завтра.")
                code = st.text_input("Ввести код доступа (VIP)")
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
                        with st.spinner("Синхронизация..."):
                            system_prompt = f"""
                            Ты - MUKTI. Пользователь: {st.session_state.username}.
                            Твой стиль: "Кибер-наставник". Спокойный, уверенный, технологичный.
                            Не используй слова "протокол" или "код" в смысле правил.
                            
                            ТВОЯ ЦЕЛЬ: Поддерживать свободу пользователя от алкоголя (Паразита).
                            
                            ИНСТРУКЦИИ:
                            1. Ответы краткие (3-4 предложения).
                            2. Если уместно, задай встречный вопрос, чтобы углубить осознанность.
                            3. Ссылайся на философию Книги (разделение Аватара и Паразита), но говори естественно.
                            
                            БАЗА ЗНАНИЙ: {BOOK_SUMMARY}
                            МОТИВАЦИЯ ЮЗЕРА: {st.session_state.get('stop_factor')}
                            """
                            full_prompt = f"{system_prompt}\nИстория:\n{st.session_state.messages[-5:]}\nUser: {prompt}"
                            
                            try:
                                response = model.generate_content(full_prompt).text
                                st.markdown(response)
                                st.session_state.messages.append({"role": "assistant", "content": response})
                                save_history(st.session_state.row_num, st.session_state.messages)
                            except Exception as e:
                                st.error("Сбой связи с ядром.")

        # FOOTER
        st.markdown("<br><hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
        c1, c2 = st.columns([3,1])
        with c2:
            if st.button("ВЫХОД", use_container_width=True):
                st.session_state.logged_in = False
                st.rerun()
