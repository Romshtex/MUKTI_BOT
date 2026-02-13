import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
import time
import json
import extra_streamlit_components as stx

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="MUKTI", page_icon="🟣", layout="centered")

# --- КОСМИЧЕСКИЙ ДИЗАЙН (CSS) ---
st.markdown("""
<style>
    /* Основной фон - глубокий космос */
    .stApp { background-color: #0e1117; color: #ffffff; }
    
    /* Заголовки */
    h1 { color: #ffffff; font-weight: 300; letter-spacing: 2px; }
    h3 { color: #a78bfa; } /* Светло-фиолетовый */
    
    /* Поля ввода */
    .stTextInput > div > div > input { 
        background-color: #1f2937; 
        color: #fff; 
        border: 1px solid #4c1d95; /* Темно-фиолетовая рамка */
    }
    
    /* Кнопки (Фиолетовый неон) */
    .stButton > button { 
        background-color: #7c3aed; /* Насыщенный фиолетовый */
        color: #ffffff; 
        font-weight: bold; 
        border: none; 
        width: 100%; /* Растянуть на всю ширину */
        border-radius: 8px;
        transition: 0.3s;
    }
    .stButton > button:hover {
        background-color: #8b5cf6; /* Светлее при наведении */
        box-shadow: 0 0 15px #8b5cf6; /* Неоновое свечение */
    }

    /* Вкладки */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #1f2937; border-radius: 5px; color: #9ca3af; }
    .stTabs [aria-selected="true"] { background-color: #7c3aed; color: #fff; }

    /* Блок цитаты */
    .quote-box {
        background-color: #17101f; /* Очень темный фиолетовый */
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid #4c1d95;
        border-left: 5px solid #8b5cf6;
        margin-bottom: 25px;
        font-style: italic;
        color: #e5e7eb;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* Сообщение об ошибке/лимите */
    .stWarning { background-color: #2e1065; color: #e9d5ff; border: 1px solid #8b5cf6; }
</style>
""", unsafe_allow_html=True)

# --- 1. ЦИТАТЫ (ПОСЛАНИЕ НА ДЕНЬ) ---
MUKTI_QUOTES = [
    "Свобода — это не когда тебе разрешили. Свобода — это когда ты не спрашиваешь разрешения у своих привычек.",
    "Паразит питается твоими эмоциями. Оставь его голодным сегодня.",
    "Трезвость — это возвращение домой, к настоящему себе.",
    "Каждый раз, когда ты выбираешь ясность, ты становишься сильнее.",
    "Твоя энергия — это самая дорогая валюта. Инвестируй её в жизнь, а не в забвение.",
    "Боль проходит. Гордость за себя остается навсегда.",
    "40 дней тишины нужны мозгу, чтобы снова научиться слышать радость.",
    "Ты не теряешь друга. Ты прощаешься с тюремщиком.",
    "Сегодня — идеальный день, чтобы быть свободным.",
    "Голос, который просит 'всего один раз' — это не твой голос.",
    "Сила воли подобна мышце. Сегодня мы её тренируем.",
    "В зеркале стоит человек, способный изменить свою судьбу.",
    "Счастье завтрашнего дня нельзя купить в кредит у алкоголя.",
    "Будь спокоен к соблазнам. Будь страстен к жизни.",
    "Исцеление происходит прямо сейчас. В каждом твоем вдохе без яда.",
]

def get_daily_quote():
    day_of_year = datetime.now().timetuple().tm_yday
    quote_index = day_of_year % len(MUKTI_QUOTES)
    return MUKTI_QUOTES[quote_index]

# --- 2. МЕНЕДЖЕР COOKIES ---
cookie_manager = stx.CookieManager()

# --- 3. БАЗА ДАННЫХ (ТЕПЕРЬ С ИСТОРИЕЙ) ---
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
        st.error(f"Ошибка БД: {e}")
        return None

sheet = connect_db()

# --- ФУНКЦИИ БАЗЫ ---
def get_user_data(username):
    """Возвращает: row_data (список), row_num (номер строки)"""
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

def update_db(row_num, count, messages_history):
    """Обновляет счетчик и ИСТОРИЮ переписки"""
    if not sheet: return
    try:
        # Col 2: Счетчик, Col 3: Дата, Col 4: История (JSON строка)
        sheet.update_cell(row_num, 2, count)
        sheet.update_cell(row_num, 3, str(date.today()))
        
        # Сохраняем историю как текст JSON, чтобы не потерять структуру
        history_str = json.dumps(messages_history, ensure_ascii=False)
        sheet.update_cell(row_num, 4, history_str)
    except: pass

def create_user_strict(username):
    if not sheet: return False
    try:
        if check_username_taken(username):
            return False
        # Создаем: Имя | 0 | Дата | Пустой список истории
        sheet.append_row([username, 0, str(date.today()), "[]"])
        return True
    except: return False

# --- 4. AI (MUKTI - МУДРЫЙ НАСТАВНИК) ---
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
    st.error("Сервис AI временно недоступен.")
    st.stop()

# --- МЯГКИЙ, НО СИЛЬНЫЙ ПРОМПТ ---
SYSTEM_PROMPT = """
ТЫ — MUKTI (Освобождение).
Ты — мудрый, спокойный и эмпатичный наставник. Твоя база знаний — книга "Кто такой Алкоголь".

ТВОЯ РОЛЬ:
Ты не робот и не справочник. Ты — проводник к свободе.
Ты разговариваешь с пользователем уважительно, тепло, но твердо придерживаешься истины.

КЛЮЧЕВЫЕ ПРИНЦИПЫ (ИЗ КНИГИ):
1. Алкоголь — это не друг, это Паразит, отнимающий энергию.
2. Мы не "бросаем" что-то ценное, мы "освобождаемся" от тюрьмы.
3. Дофаминовая яма — это временный период восстановления (около 40 дней), который нужно прожить осознанно.
4. Безопасных доз не существует, это иллюзия.

ТОН ОБЩЕНИЯ:
- Будь краток, но глубок.
- Не используй агрессию или обвинения.
- Если человек сорвался — не ругай, а поддержи и помоги вернуться на путь.
- Обращайся к светлой части личности человека.

ВНИМАНИЕ: Если пользователь спрашивает что-то, не связанное с зависимостью (погода, новости), мягко верни разговор к теме его состояния и роста.
"""

# ==========================================
# 5. ЛОГИКА ВХОДА (С ЗАГРУЗКОЙ ИСТОРИИ)
# ==========================================

try: cookie_user = cookie_manager.get(cookie="mukti_user_id")
except: cookie_user = None

if "user_row" not in st.session_state:
    
    # СЦЕНАРИЙ А: АВТО-ВХОД ПО КУКИ
    if cookie_user:
        with st.spinner(f"Возвращение в систему {cookie_user}..."):
            row_data, row_id = get_user_data(cookie_user)
            if row_data:
                st.session_state.username = cookie_user
                st.session_state.user_row = row_id
                
                # Счетчик (сброс если новый день)
                if len(row_data) > 2 and row_data[2] != str(date.today()):
                    st.session_state.msg_count = 0 
                else:
                    st.session_state.msg_count = int(row_data[1]) if len(row_data) > 1 else 0
                
                # ЗАГРУЗКА ИСТОРИИ ИЗ БАЗЫ
                try:
                    if len(row_data) > 3 and row_data[3]:
                        st.session_state.messages = json.loads(row_data[3])
                    else:
                        st.session_state.messages = [{"role": "assistant", "content": f"Здравствуй, {cookie_user}. Я здесь. Мы продолжаем путь."}]
                except:
                    st.session_state.messages = [{"role": "assistant", "content": f"Рад видеть тебя, {cookie_user}. Начнем."}]

                st.rerun()
            else:
                try: cookie_manager.delete("mukti_user_id")
                except: pass

    # СЦЕНАРИЙ Б: ЭКРАН ПРИВЕТСТВИЯ
    st.title("MUKTI")
    st.markdown("<h4 style='text-align: center; color: #a78bfa; margin-bottom: 30px;'>Твой проводник к свободе и осознанности</h4>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Регистрация", "Вход"])

    # Вкладка РЕГИСТРАЦИЯ
    with tab1:
        new_username = st.text_input("Придумай имя (Ник):", key="new_user").strip()
        if st.button("Начать путь"):
            if not new_username:
                st.warning("Пожалуйста, введите имя.")
            else:
                with st.spinner("Создаем профиль..."):
                    if check_username_taken(new_username.lower()):
                        st.error(f"Имя '{new_username}' уже занято. Попробуй другое.")
                    else:
                        if create_user_strict(new_username.lower()):
                            st.session_state.username = new_username.lower()
                            st.session_state.msg_count = 0
                            st.session_state.user_row = len(sheet.get_all_values())
                            st.session_state.messages = [{"role": "assistant", "content": "Добро пожаловать. Я MUKTI. Я помогу тебе пройти этот путь. Расскажи мне, что привело тебя сюда?"}]
                            
                            cookie_manager.set("mukti_user_id", new_username.lower(), expires_at=datetime(2027, 1, 1))
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Ошибка соединения. Попробуй позже.")

    # Вкладка ВХОД
    with tab2:
        old_username = st.text_input("Твое имя (Ник):", key="old_user").strip()
        if st.button("Войти"):
            if not old_username:
                st.warning("Введите имя.")
            else:
                with st.spinner("Поиск профиля..."):
                    row_data, row_id = get_user_data(old_username.lower())
                    if row_data:
                        st.session_state.username = old_username.lower()
                        st.session_state.user_row = row_id
                        
                        # Счетчик
                        if len(row_data) > 2 and row_data[2] != str(date.today()):
                            st.session_state.msg_count = 0 
                        else:
                            st.session_state.msg_count = int(row_data[1]) if len(row_data) > 1 else 0
                        
                        # История
                        try:
                            if len(row_data) > 3 and row_data[3]:
                                st.session_state.messages = json.loads(row_data[3])
                            else:
                                st.session_state.messages = [{"role": "assistant", "content": f"С возвращением, {old_username}. Я готов слушать."}]
                        except:
                            st.session_state.messages = [{"role": "assistant", "content": f"С возвращением."}]

                        cookie_manager.set("mukti_user_id", old_username.lower(), expires_at=datetime(2027, 1, 1))
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Такой пользователь не найден. Попробуй вкладку 'Регистрация'.")
    st.stop()

# ==========================================
# 6. ГЛАВНЫЙ ЭКРАН (ЧАТ)
# ==========================================

st.title(f"MUKTI")
st.caption(f"Профиль: {st.session_state.username}")

# Цитата дня
daily_quote = get_daily_quote()
st.markdown(f"""
<div class="quote-box">
    🟣 <b>Послание на день:</b><br>
    "{daily_quote}"
</div>
""", unsafe_allow_html=True)

DAILY_LIMIT = 5

# Вывод истории
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ПОЛЕ ВВОДА
if prompt := st.chat_input("Напиши сообщение..."):

    # --- 1. ПРОВЕРКА ПАРОЛЯ АДМИНА (СНАЧАЛА!) ---
    if "ADMIN_PASSWORD" in st.secrets and prompt.strip() == st.secrets["ADMIN_PASSWORD"]:
        st.session_state.msg_count = 0
        update_db(st.session_state.user_row, 0, st.session_state.messages) # Обнуляем в базе
        st.toast("🔮 Доступ восстановлен. Лимит сброшен.", icon="🟣")
        time.sleep(1.5)
        st.rerun()
        
    # --- 2. ПРОВЕРКА ЛИМИТА ---
    elif st.session_state.msg_count >= DAILY_LIMIT:
        st.warning(f"🛑 На сегодня достаточно. ({DAILY_LIMIT}/{DAILY_LIMIT}).\n\nОсмысление важнее бесконечных разговоров. Возвращайся завтра со свежими силами.")
    
    # --- 3. ОБРАБОТКА СООБЩЕНИЯ ---
    else:
        # Пользователь
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # MUKTI
        with st.chat_message("assistant"):
            with st.spinner("MUKTI размышляет..."):
                full_prompt = f"{SYSTEM_PROMPT}\nИстория диалога:\n{st.session_state.messages}\nПоследний вопрос: {prompt}"
                try:
                    res = model.generate_content(full_prompt).text
                    st.markdown(res)
                    st.session_state.messages.append({"role": "assistant", "content": res})
                    
                    st.session_state.msg_count += 1
                    # СОХРАНЯЕМ ВСЮ ИСТОРИЮ В БАЗУ
                    update_db(st.session_state.user_row, st.session_state.msg_count, st.session_state.messages)
                    
                except Exception as e:
                    st.error("Связь с полем прервана. Попробуй еще раз.")
