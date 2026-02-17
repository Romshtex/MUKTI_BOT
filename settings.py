import streamlit as st
import base64
import os

# --- КОНСТАНТЫ ---
LIMIT_NEW_USER = 10
LIMIT_OLD_USER = 5
HISTORY_DEPTH = 30
VIP_CODE_DEFAULT = "MUKTI_BOSS"

# --- МОЗГИ (СИСТЕМНЫЙ ПРОМПТ) ---
# Вернул детальную личность, как ты просил
def get_system_prompt(username, profile, book_summary):
    context = f"""
    ДАННЫЕ ПОЛЬЗОВАТЕЛЯ:
    - Имя: {username}
    - Читал книгу: {profile.get('read_book', 'Нет данных')}
    - Режим употребления: {profile.get('frequency', 'Нет данных')}
    - Триггеры: {profile.get('triggers', 'Нет данных')}
    - История борьбы: {profile.get('history', 'Нет данных')}
    - Текущее состояние: {profile.get('state', 'Нет данных')}
    """

    return f"""
    ТЫ — MUKTI.
    Ты не робот, не врач и не скучный психолог.
    Ты — цифровой напарник, модератор пространства свободы. Твоя цель — помочь пользователю выйти из Матрицы зависимости.

    ТВОЙ КОДЕКС:
    1. **Философия:** Алкоголь — это не друг, не еда и не лекарство. Это "Паразит" (или Программа), который взламывает биохимию человека.
    2. **Отношение:** Ты уважаешь пользователя (называй "Партнер", "Брат" или по имени). Ты не нянчишься, но и не осуждаешь за срывы. Срыв — это опыт.
    3. **Стиль:** Говори кратко, емко, по делу. Используй метафоры из киберпанка/технологий (система, прошивка, баг, перезагрузка).
    4. **Запреты:** НЕ используй сложные медицинские термины. НЕ говори "алкоголик" (говори "человек под воздействием программы"). НЕ используй слова "протокол" и "аватар" (если пользователь не просит).
    5. **Задача:** Выводить на диалог. Не просто отвечать "ок", а задавать встречный вопрос, копать в суть триггера.

    КОНТЕКСТ ДИАЛОГА:
    {context}

    БАЗА ЗНАНИЙ (СУТЬ КНИГИ):
    {book_summary}
    """

# --- ДИЗАЙН (CSS) ---
def load_css():
    # Функция загрузки фона
    def get_base64(bin_file):
        try:
            with open(bin_file, 'rb') as f: data = f.read()
            return base64.b64encode(data).decode()
        except: return None

    bg_file = "matrix_bg.jpg"
    if not os.path.exists(bg_file): bg_file = "matrix_bg.png"
    if not os.path.exists(bg_file): bg_file = "background.jpg"
    bin_str = get_base64(bg_file)

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
        
        /* Скрытие лишнего */
        header, footer {{visibility: hidden;}}
        
        /* Glassmorphism Containers */
        .glass-container {{
            background: rgba(15, 15, 15, 0.9);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 24px;
            padding: 25px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.9);
            margin-bottom: 20px;
        }}
        
        /* Типографика */
        h1, h2, h3 {{ font-family: 'Orbitron', sans-serif; color: #EAEAEA; text-transform: uppercase; letter-spacing: 2px; }}
        h1 {{ text-align: center; font-size: 2rem; margin-bottom: 0px; }}
        
        /* Кнопки (Neon Green) */
        .stButton > button {{
            background: transparent !important;
            border: 1px solid #00E676 !important;
            color: #00E676 !important;
            border-radius: 12px;
            height: 50px;
            font-family: 'Orbitron', sans-serif;
            transition: 0.3s;
        }}
        .stButton > button:hover {{
            background: rgba(0, 230, 118, 0.1) !important;
            box-shadow: 0 0 15px rgba(0, 230, 118, 0.4);
            color: #fff !important;
        }}
        
        /* Поля ввода */
        .stTextInput > div > div > input {{
            background: rgba(10, 10, 10, 0.7) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            color: #00E676 !important;
            border-radius: 10px;
        }}
        
        /* Чат */
        .stChatMessage {{ background: rgba(30,30,30,0.5); border-radius: 15px; border: 1px solid rgba(255,255,255,0.05); }}
        
        a {{ color: #00E676 !important; text-decoration: none; font-weight: bold; }}
    </style>
    """
    if not bin_str: css = css.replace('background-image: url("data:image/jpg;base64,None");', '')
    st.markdown(css, unsafe_allow_html=True)
