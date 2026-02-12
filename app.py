import streamlit as st
import google.generativeai as genai
import time

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="MUKTI", page_icon="🔥", layout="centered")

# --- ДИЗАЙН (CSS) ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    h1 { color: #facc15; font-family: 'Helvetica', sans-serif; }
    .stTextInput > div > div > input { color: #ffffff; background-color: #1f2937; }
    .stButton > button { background-color: #facc15; color: #000000; border: none; }
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# --- 0. ФЕЙС-КОНТРОЛЬ (ЗАЩИТА ПАРОЛЕМ) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Доступ ограничен")
    st.markdown("Это закрытая версия AI-ментора **MUKTI**.")
    
    password = st.text_input("Введите код доступа:", type="password")
    
    if st.button("Войти"):
        # Проверяем пароль из Secrets
        if password == st.secrets["ACCESS_CODE"]:
            st.session_state.authenticated = True
            st.success("Доступ разрешен.")
            time.sleep(1)
            st.rerun() # Перезагружаем страницу, чтобы пустить внутрь
        else:
            st.error("Неверный код доступа.")
    
    st.stop() # ОСТАНАВЛИВАЕМ КОД ЗДЕСЬ, ЕСЛИ ПАРОЛЬ НЕ ВВЕДЕН

# ==========================================
# ВСЁ, ЧТО НИЖЕ — ВИДЯТ ТОЛЬКО ИЗБРАННЫЕ
# ==========================================

# --- 1. АВТОРИЗАЦИЯ GOOGLE ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("Ошибка конфигурации ключа.")
    st.stop()

# --- 2. АВТО-ПОИСК МОДЕЛИ ---
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
    st.error("Сервис временно недоступен.")
    st.stop()

# --- 3. СИСТЕМНЫЙ ПРОМПТ ---
SYSTEM_PROMPT = """
ТЫ — MUKTI (ОСВОБОЖДЕНИЕ).
Ты — цифровой ментор, основанный на книге "Кто такой Алкоголь".

ТВОЯ БАЗА ЗНАНИЙ:
1. Алкоголь — это "Паразит", "Сущность".
2. Дофаминовая яма — причина страданий, а не "тяжелая жизнь".
3. Безопасных доз нет.
4. Трезвость — это приобретение силы, а не отказ от радости.

ТВОЙ СТИЛЬ:
- Жесткий, но эмпатичный.
- Обращайся по имени.
- Если пишут "SOS" — используй технику дыхания и переключения.

СЦЕНАРИЙ "ЗНАКОМСТВО":
Если история пуста, спроси:
1. Имя.
2. Стаж и что пьет.
3. Главную боль (Мотивацию).
"""

# --- 4. ИНТЕРФЕЙС ПРИЛОЖЕНИЯ ---
st.title("🔥 MUKTI")
st.caption("Закрытая Beta-версия")

# Инициализация чата
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Привет. Я — MUKTI.\nЯ ждал тебя.\n\nНапиши свое имя, чтобы начать процесс освобождения."}
    ]
if "count" not in st.session_state:
    st.session_state.count = 0

DAILY_LIMIT = 5 # Увеличил лимит до 5 для тестов с партнером

# Вывод истории
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Ввод сообщения
if prompt := st.chat_input("Напиши сообщение..."):
    
    if st.session_state.count >= DAILY_LIMIT:
        with st.chat_message("assistant"):
            st.warning("🛑 **Лимит сообщений исчерпан.**\n\nMUKTI требует дисциплины. Возвращайся завтра со свежими мыслями.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("⚡ MUKTI..."):
                try:
                    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
                    full_query = f"{SYSTEM_PROMPT}\n\nДИАЛОГ:\n{history_text}\n\nОТВЕТ MUKTI:"
                    
                    response = model.generate_content(full_query)
                    ai_answer = response.text
                    
                    st.markdown(ai_answer)
                    st.session_state.messages.append({"role": "assistant", "content": ai_answer})
                    st.session_state.count += 1
                except Exception as e:
                    st.error("Ошибка связи.")
