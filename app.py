import streamlit as st
import google.generativeai as genai

# --- НАСТРОЙКИ ---
st.set_page_config(page_title="MUKTI", page_icon="🔥", layout="centered")

# --- ДИЗАЙН ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #fff; }
    h1 { color: #facc15; }
    .stChatInput { bottom: 20px; }
    .debug-box { font-size: 12px; color: #4b5563; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

st.title("🔥 MUKTI: Путь к свободе")

# --- 1. АВТОРИЗАЦИЯ ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("❌ Нет ключа API. Добавь GOOGLE_API_KEY в Secrets.")
    st.stop()

# --- 2. АВТО-ПОИСК РАБОЧЕЙ МОДЕЛИ ---
# Это самый надежный блок. Мы спрашиваем у Google, что есть, и берем лучшее.
@st.cache_resource
def get_working_model():
    try:
        # Получаем список всех доступных моделей для твоего ключа
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        # Логика выбора: Ищем 1.5 Pro -> иначе 1.5 Flash -> иначе просто Pro -> иначе первую попавшуюся
        if not available_models:
            return None, "Нет доступных моделей"

        selected_name = ""
        # Приоритеты
        if 'models/gemini-1.5-pro' in available_models:
            selected_name = 'models/gemini-1.5-pro'
        elif 'models/gemini-1.5-pro-latest' in available_models:
            selected_name = 'models/gemini-1.5-pro-latest'
        elif 'models/gemini-1.5-flash' in available_models:
            selected_name = 'models/gemini-1.5-flash'
        elif 'models/gemini-pro' in available_models:
            selected_name = 'models/gemini-pro'
        else:
            selected_name = available_models[0] # Берем любую, если основных нет
            
        return genai.GenerativeModel(selected_name), selected_name
    except Exception as e:
        return None, str(e)

# Инициализация модели
model, model_name = get_working_model()

# Выводим инфо (чтобы ты видел, к чему подключились)
if model:
    st.markdown(f'<div class="debug-box">📡 Подключено к мозгу: {model_name}</div>', unsafe_allow_html=True)
else:
    st.error(f"💥 Не удалось найти ни одной модели. Ошибка: {model_name}")
    st.stop()

# --- 3. СИСТЕМНЫЙ ПРОМПТ (MUKTI) ---
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
"""

# --- 4. ЧАТ ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Привет. Я — MUKTI. Я здесь, чтобы помочь тебе проснуться. \n\nНачни с главного: как тебя зовут?"}
    ]

# Показываем историю
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Обработка ввода
if prompt := st.chat_input("Твой ответ..."):
    # Пишет пользователь
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Отвечает AI
    with st.chat_message("assistant"):
        with st.spinner("MUKTI анализирует..."):
            try:
                # Формируем запрос
                history_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
                full_query = f"{SYSTEM_PROMPT}\n\nТЕКУЩИЙ ДИАЛОГ:\n{history_text}\n\nОТВЕТ MUKTI:"
                
                response = model.generate_content(full_query)
                ai_answer = response.text
                
                st.markdown(ai_answer)
                st.session_state.messages.append({"role": "assistant", "content": ai_answer})
            
            except Exception as e:
                st.error(f"Ошибка генерации: {e}")
