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
</style>
""", unsafe_allow_html=True)

# --- 1. АВТОРИЗАЦИЯ ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("❌ Нет ключа API. Добавь его в Secrets.")
    st.stop()

# --- 2. ВЫБОР МОДЕЛИ (ХИТРЫЙ БЛОК) ---
# Мы пробуем подключить самую мощную. Если нет — берем стандартную.
try:
    model = genai.GenerativeModel('gemini-1.5-pro')
except:
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
    except:
        model = genai.GenerativeModel('gemini-pro')

# --- 3. МОЗГИ MUKTI (СЮДА ВСТАВЬ ТЕКСТ КНИГИ) ---
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
st.title("🔥 MUKTI: Путь к свободе")

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
        with st.spinner("MUKTI слушает..."):
            try:
                # Формируем запрос
                history_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
                full_query = f"{SYSTEM_PROMPT}\n\nДИАЛОГ:\n{history_text}\n\nОТВЕТ MUKTI:"
                
                response = model.generate_content(full_query)
                ai_answer = response.text
                
                st.markdown(ai_answer)
                st.session_state.messages.append({"role": "assistant", "content": ai_answer})
            
            except Exception as e:
                st.error(f"Ошибка связи с космосом: {e}")
