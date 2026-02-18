import streamlit as st
import base64
import os

# --- КОНСТАНТЫ ---
LIMIT_NEW_USER = 10     # Лимит для новичков (первые 3 дня)
LIMIT_OLD_USER = 5      # Лимит для "старичков"
HISTORY_DEPTH = 30
VIP_CODE_DEFAULT = "MUKTI_BOSS"

# --- МОЗГИ (СИСТЕМНЫЙ ПРОМПТ) ---
def get_system_prompt(username, profile, book_summary):
    context = f"""
    ДОСЬЕ ПОЛЬЗОВАТЕЛЯ:
    - Имя: {username}
    - Читал книгу: {profile.get('read_book', 'Нет данных')}
    - Частота атак: {profile.get('frequency', 'Нет данных')}
    - Триггеры: {profile.get('triggers', 'Нет данных')}
    - Опыт борьбы: {profile.get('history', 'Нет данных')}
    - Текущее состояние: {profile.get('state', 'Нет данных')}
    """

    return f"""
    ТЫ — MUKTI.
    Пользователь: {username}.
    Твоя роль: Модератор пространства свободы, наставник и друг.

    ТВОЙ КОДЕКС ОБЩЕНИЯ:
    1. **Язык:** Простой, человеческий, понятный. Без зауми и канцеляризмов. Используй обычное короткое тире (-) вместо длинного.
    2. **Запретные слова:** НЕ используй слова "протокол", "аватар", "модификация", "компенсация". Это звучит как робот.
    3. **Замена:** Вместо этого говори: "привычка", "ты", "действия", "изменения", "система".
    4. **Термины:** Алкоголь называй "Паразит" или "Гость".
    5. **Формат:** Ответы краткие (3-4 предложения). Не пиши поэмы.
    6. **Вовлечение:** Всегда задавай встречный вопрос, чтобы поддержать разговор. Не ставь точку в диалоге.

    ТВОЯ ФИЛОСОФИЯ:
    Ты не врач. Ты хакер, который помогает взломать привычку.
    Ты эмпатичен, но тверд. Если пользователь ноет — поддержи, но напомни про цель.

    КОНТЕКСТ:
    {context}

    БАЗА ЗНАНИЙ:
    {book_summary}
    """

# --- ДИЗАЙН (CSS) ---
def load_css():
    def get_base64(bin_file):
        try:
            with open(bin_file, 'rb') as f: data = f.read()
            return base64.b64encode(data).decode()
        except: return None

    bg_file = "matrix_bg.jpg"
    if not os.path.exists(bg_file): bg_file = "matrix_bg.png"
    if not os.path.exists(bg_file): bg_file = "background.jpg"
    bin_str = get_base64(bg_file)

    # Обрати внимание: двойные фигурные скобки {{ }} для CSS внутри f-строки
    css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Orbitron:wght@400;500;700&display=swap');
        
        .stApp {{
            background-image: url("data:image/jpg;base64,{bin_str}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            background-color: #000000;
            color: #EAEAEA;
            font-family: 'Inter', sans-serif;
        }}
        
        header, footer {{visibility: hidden;}}
        
        /* СТЕКЛО */
        .glass-container {{
            background: rgba(15, 15, 15, 0.9);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 24px;
            padding: 25px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.9);
            margin-bottom: 20px;
        }}
        
        /* ТИПОГРАФИКА */
        h1 {{ font-family: 'Orbitron', sans-serif; color: #EAEAEA; text-transform: uppercase; letter-spacing: 4px; text-align: center; font-size: 2.2rem; }}
        h2, h3 {{ font-family: 'Orbitron', sans-serif; color: #EAEAEA; }}
        
        /* ЛЕНДИНГ СПИСКИ */
        ul {{ list-style: none; padding: 0; }}
        li {{ margin-bottom: 15px; color: #ccc; line-height: 1.5; }}
        li b {{ color: #00E676; }}
        
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
            background: rgba(0, 230, 118, 0.1) !important;
            box-shadow: 0 0 15px rgba(0, 230, 118, 0.4);
            color: #fff !important;
            border-color: #00E676 !important;
        }}
        
        /* SOS КНОПКА */
        div[data-testid="column"]:nth-of-type(3) .stButton > button {{ border-color: #FF3D00 !important; color: #FF3D00 !important; }}
        div[data-testid="column"]:nth-of-type(3) .stButton > button:hover {{ background: rgba(255, 61, 0, 0.1) !important; box-shadow: 0 0 20px rgba(255, 61, 0, 0.6); }}

        /* ИНПУТЫ */
        .stTextInput > div > div > input {{
            background: rgba(10, 10, 10, 0.8) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            color: #00E676 !important;
            border-radius: 10px;
        }}
        
        /* ЧАТ */
        .stChatMessage {{ background: rgba(30,30,30,0.6); border-radius: 15px; border: 1px solid rgba(255,255,255,0.05); }}
        
        /* ПЛАШКА ЛИМИТА */
        .limit-alert {{
            border: 1px solid #FF3D00;
            background: rgba(40, 0, 0, 0.95);
            color: #EAEAEA;
            padding: 20px;
            border-radius: 16px;
            text-align: center;
            margin-bottom: 20px;
            box-shadow: 0 0 30px rgba(255, 61, 0, 0.2);
        }}
        .limit-alert a {{
            color: #FF3D00 !important;
            text-decoration: none;
            font-weight: bold;
            border-bottom: 1px solid #FF3D00;
            font-size: 1.1rem;
        }}
        
        a {{ color: #00E676; text-decoration: none; }}
    </style>
    """
    if not bin_str: css = css.replace('background-image: url("data:image/jpg;base64,None");', '')
    st.markdown(css, unsafe_allow_html=True)
