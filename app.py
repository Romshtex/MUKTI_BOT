import streamlit as st
import google.generativeai as genai
from datetime import datetime, date

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="MUKTI", page_icon="🔥", layout="centered")

# --- СТИЛИ ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #fff; }
    .status-card { background-color: #1f2937; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px;}
</style>
""", unsafe_allow_html=True)

# --- 1. ПРОВЕРЯЕМ КЛЮЧ ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    # Показываем первые 4 символа ключа для проверки (остальное скрыто)
    st.caption(f"🔑 Ключ загружен: {api_key[:4]}... (Ок)")
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"❌ ПРОБЛЕМА С КЛЮЧОМ: {e}")
    st.stop()

# --- 2. ПОДКЛЮЧАЕМ МОДЕЛЬ (ПРОБУЕМ FLASH - ОНА СТАБИЛЬНЕЕ) ---
try:
    # Используем Flash, она быстрее и меньше глючит на бесплатных тарифах
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"❌ Ошибка настройки модели: {e}")

# --- 3. СИСТЕМНЫЙ ПРОМПТ (ВСТАВЬ СЮДА ДАННЫЕ ИЗ КНИГИ) ---
SYSTEM_PROMPT = """
ТЫ — MUKTI. Ментор по трезвости.
Твоя задача: Помочь человеку выйти из зависимости.
Стиль: Жесткий, но добрый.
Если спрашивают имя — говори MUKTI.
Если просят помощь — давай советы.
"""

# --- 4. ПАМЯТЬ ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Привет. Я — MUKTI. Я готов говорить. Напиши мне."}
    ]

# --- 5. ИНТЕРФЕЙС ---
st.title("🔥 MUKTI: Путь к свободе")

# Вывод чата
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# --- 6. ОБРАБОТКА СООБЩЕНИЯ (С ВЫВОДОМ ОШИБКИ) ---
if prompt := st.chat_input("Напиши сообщение..."):
    # Показываем сообщение пользователя
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # Генерация ответа
    with st.chat_message("assistant"):
        with st.spinner("MUKTI думает..."):
            try:
                # Собираем историю
                history = [
                    {"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]}
                    for m in st.session_state.messages
                ]
                
                # Добавляем системную инструкцию в начало запроса (хак для надежности)
                full_request = f"СИСТЕМНАЯ ИНСТРУКЦИЯ:\n{SYSTEM_PROMPT}\n\nВОПРОС ПОЛЬЗОВАТЕЛЯ:\n{prompt}"
                
                # Отправляем запрос
                response = model.generate_content(full_request)
                
                # Получаем текст
                ai_answer = response.text
                st.write(ai_answer)
                
                # Сохраняем
                st.session_state.messages.append({"role": "assistant", "content": ai_answer})
                
            except Exception as e:
                # ВОТ ЗДЕСЬ МЫ УВИДИМ РЕАЛЬНУЮ ОШИБКУ
                st.error(f"💥 ОШИБКА API: {e}")
                st.warning("Попробуй обновить страницу или создать новый API Key.")
