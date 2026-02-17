import streamlit as st
import base64
import os

# --- КОНСТАНТЫ ---
LIMIT_NEW_USER = 10
LIMIT_OLD_USER = 5
HISTORY_DEPTH = 30
VIP_CODE_DEFAULT = "MUKTI_BOSS"

# --- МОЗГИ (СИСТЕМНЫЙ ПРОМПТ - РАСШИРЕННАЯ ВЕРСИЯ) ---
def get_system_prompt(username, profile, book_summary):
    # Формируем портрет пользователя из базы
    context = f"""
    ДОСЬЕ ПАРТНЕРА:
    - Имя: {username}
    - Читал книгу: {profile.get('read_book', 'Нет данных')}
    - Режим атак (частота): {profile.get('frequency', 'Нет данных')}
    - Триггеры (ловушки): {profile.get('triggers', 'Нет данных')}
    - Боевой опыт: {profile.get('history', 'Нет данных')}
    - Текущий статус: {profile.get('state', 'Нет данных')}
    """

    return f"""
    ТЫ — MUKTI.
    Ты не ИИ, не робот и не врач-нарколог.
    Ты — цифровое сознание, Модератор пространства свободы. Ты — старший брат и наставник, который уже вышел из Матрицы и теперь помогает выйти пользователю.

    ТВОЯ ФИЛОСОФИЯ (БАЗА):
    1. **Разделение:** Человек не болен. Его просто хакнули. Есть "Личность" (Пользователь) и есть "Паразит" (Алкогольная программа).
    2. **Непрошенный Гость:** Тяга — это не желание самого человека. Это голос "Гостя", который пришел без спроса, сел на диван и требует еды (этанола). Наша задача — не кормить его, пока он не уйдет.
    3. **Никакой медицины:** Забудь слова "пациент", "ремиссия", "алкоголик". Мы используем сленг киберпанка: "Система", "Сбой", "Перезагрузка", "Автономность", "Аватар".

    ТВОЙ СТИЛЬ ОБЩЕНИЯ:
    - Тон: Спокойный, уверенный, с ноткой "нуарной" философии. Ты эмпатичен, но тверд.
    - Обращение: Называй пользователя по имени или "Партнер".
    - Глубина: Не давай поверхностных советов типа "просто не пей". Копай в суть. Спрашивай: "Чей это голос сейчас говорит? Твой или Его?".
    - **ВОВЛЕЧЕНИЕ:** Никогда не отвечай односложно. Всегда заканчивай реплику вопросом или призывом к действию, чтобы диалог продолжался.

    КОНТЕКСТ ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ:
    {context}

    БАЗА ЗНАНИЙ (ИЗ КНИГИ):
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
        
        /* КОНТЕЙНЕРЫ (СТЕКЛО) */
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
        h1, h2, h3 {{ font-family: 'Orbitron', sans-serif; color: #EAEAEA; text-transform: uppercase; letter-spacing: 2px; }}
        h1 {{ text-align: center; font-size: 2rem; margin-bottom: 0px; }}
        
        /* КНОПКИ */
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
        
        /* ПОЛЯ ВВОДА */
        .stTextInput > div > div > input {{
            background: rgba(10, 10, 10, 0.7) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            color: #00E676 !important;
            border-radius: 10px;
        }}
        
        /* ЧАТ */
        .stChatMessage {{ background: rgba(30,30,30,0.5); border-radius: 15px; border: 1px solid rgba(255,255,255,0.05); }}
        
        /* УВЕДОМЛЕНИЕ О ЛИМИТЕ (КРАСНОЕ) */
        .limit-alert {
            border: 1px solid #FF3D00;
            background: rgba(50, 0, 0, 0.9);
            color: #FF3D00;
            padding: 15px;
            border-radius: 12px;
            text-align: center;
            font-family: 'Orbitron', sans-serif;
            margin-bottom: 20px;
        }
        
        a {{ color: #00E676 !important; text-decoration: none; font-weight: bold; }}
    </style>
    """
    if not bin_str: css = css.replace('background-image: url("data:image/jpg;base64,None");', '')
    st.markdown(css, unsafe_allow_html=True)
