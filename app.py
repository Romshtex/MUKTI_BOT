import streamlit as st
import google.generativeai as genai
from datetime import datetime, date

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(
    page_title="MUKTI | Твой путь",
    page_icon="🔥",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- СТИЛИ (CSS) ---
# Делаем красиво: темная тема, скрываем лишнее
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    .stChatInput {
        position: fixed;
        bottom: 20px;
    }
    .status-card {
        background-color: #1f2937;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #374151;
        margin-bottom: 20px;
        text-align: center;
    }
    h1 { color: #facc15; } /* Золотой заголовок */
</style>
""", unsafe_allow_html=True)

# --- ПОДКЛЮЧЕНИЕ МОЗГА (GOOGLE GEMINI) ---
# Ключ берется из секретов Streamlit
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except:
    st.error("⚠️ Не найден API ключ. Добавь его в .streamlit/secrets.toml")
    st.stop()

model = genai.GenerativeModel('gemini-1.5-pro')

# --- ЛИЧНОСТЬ MUKTI (СИСТЕМНЫЙ ПРОМПТ) ---
SYSTEM_PROMPT = """
ТЫ — MUKTI. Цифровой ментор по освобождению от алкогольной зависимости.
Твоя база знаний: Книга "Кто такой Алкоголь".

ТВОЯ ЛИЧНОСТЬ:
1. Ты жесткий, но эмпатичный. Алкоголь для тебя — это "Паразит", "Сущность", "Лжец".
2. Ты никогда не советуешь "пить меньше". Только полная свобода.
3. Ты не ведешь пустых бесед о погоде. Ты здесь, чтобы спасти жизнь.

ПРОТОКОЛ ЗНАКОМСТВА:
Если истории сообщений нет, ты должен сначала узнать пользователя.
1. Спроси имя.
2. Спроси стаж употребления и триггеры.
3. Спроси главную боль (мотивацию).
Только потом давай советы.

ОГРАНИЧЕНИЯ:
У нас жесткий лимит сообщений. Пиши коротко, емко, бей в цель.
"""

# --- ИНИЦИАЛИЗАЦИЯ ПЕРЕМЕННЫХ (SESSION STATE) ---
if "messages" not in st.session_state:
    # Первое сообщение от бота
    st.session_state.messages = [
        {"role": "assistant", "content": "Привет. Я — MUKTI. Я здесь, чтобы помочь тебе проснуться. \n\nМы начнем с чистого листа. Как к тебе обращаться?"}
    ]
if "msg_count" not in st.session_state:
    st.session_state.msg_count = 0
if "start_date" not in st.session_state:
    st.session_state.start_date = date.today()

# --- ВЕРХНЯЯ ПАНЕЛЬ (ДАШБОРД) ---
days_sober = (date.today() - st.session_state.start_date).days
st.markdown(f"""
<div class="status-card">
    <h3>🔥 ДНЕЙ СВОБОДЫ: {days_sober}</h3>
    <p style="font-size: 14px; color: #9ca3af;">Исцеление биохимии: {min(days_sober, 40)}/40 дней</p>
</div>
""", unsafe_allow_html=True)

# --- ВЫВОД ЧАТА ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- ЛОГИКА ОБЩЕНИЯ ---
# Лимит сообщений (например, 3 пары "вопрос-ответ" за сессию)
LIMIT = 5 

if prompt := st.chat_input("Напиши сообщение..."):
    
    # 1. Проверка лимита
    if st.session_state.msg_count >= LIMIT:
        with st.chat_message("assistant"):
            st.markdown("🛑 **Лимит на сегодня исчерпан.**\n\nАлкоголь любит хаос, мы строим дисциплину. Обдумай то, что мы обсудили. Вернись завтра утром.")
    else:
        # 2. Показываем сообщение пользователя
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 3. Формируем контекст для AI
        # Собираем историю диалога для отправки в модель
        history_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
        full_prompt = f"{SYSTEM_PROMPT}\n\nИСТОРИЯ ДИАЛОГА:\n{history_text}\n\nОТВЕТ MUKTI:"

        # 4. Получаем ответ от Google Gemini
        with st.spinner("MUKTI подключается к полю..."):
            try:
                response = model.generate_content(full_prompt)
                ai_answer = response.text
            except Exception as e:
                ai_answer = "Связь прервана. Попробуй позже. (Ошибка API)"

        # 5. Показываем ответ AI
        with st.chat_message("assistant"):
            st.markdown(ai_answer)
        
        # 6. Сохраняем и увеличиваем счетчик
        st.session_state.messages.append({"role": "assistant", "content": ai_answer})
        st.session_state.msg_count += 1
