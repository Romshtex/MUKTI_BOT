import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
import time
import json
import random

# --- 1. НАСТРОЙКИ ---
try:
    from book import FULL_BOOK_TEXT, BOOK_SUMMARY
except ImportError:
    FULL_BOOK_TEXT = "Текст книги недоступен."
    BOOK_SUMMARY = "Философия освобождения от зависимости."

GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"] if "GOOGLE_API_KEY" in st.secrets else "NO_KEY"
VIP_CODE = "MUKTI_BOSS"

genai.configure(api_key=GOOGLE_API_KEY)

# --- 2. МОЗГИ ---
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

# --- 3. ДИЗАЙН (CYBERPUNK GLASS) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;600;700;800&display=swap');

:root{
  --bg0:#070A14;
  --bg1:#0B0F1F;

  --glass:rgba(255,255,255,.08);
  --glass2:rgba(255,255,255,.05);

  --stroke:rgba(139,92,246,.35);
  --stroke2:rgba(34,211,238,.28);

  --text:#EAF0FF;
  --muted:rgba(234,240,255,.70);

  --violet:#8B5CF6;
  --cyan:#22D3EE;
  --pink:#FF4FD8;

  --r:22px;
  --shadow:0 18px 60px rgba(0,0,0,.55);
}

/* Base */
.stApp{
  font-family:'Manrope', sans-serif;
  color:var(--text);
  background:
    radial-gradient(1200px 900px at 20% 10%, rgba(139,92,246,.22), transparent 55%),
    radial-gradient(1200px 900px at 85% 15%, rgba(34,211,238,.16), transparent 60%),
    radial-gradient(900px 700px at 65% 92%, rgba(255,79,216,.10), transparent 60%),
    linear-gradient(180deg, var(--bg0), var(--bg1));
  overflow:hidden;
}

/* Hide Streamlit chrome */
header {visibility:hidden;}
footer {visibility:hidden;}
#MainMenu {visibility:hidden;}

/* Cyberpunk background layers */
.stApp:before{
  content:"";
  position:fixed;
  inset:-20%;
  pointer-events:none;
  background:
    /* “city” vertical rhythm */
    repeating-linear-gradient(90deg,
      rgba(255,255,255,.05) 0 1px,
      transparent 1px 48px),
    /* fog beams */
    radial-gradient(700px 900px at 18% 70%, rgba(139,92,246,.10), transparent 60%),
    radial-gradient(700px 900px at 78% 60%, rgba(34,211,238,.08), transparent 60%),
    radial-gradient(600px 800px at 55% 30%, rgba(255,79,216,.06), transparent 60%);
  opacity:.85;
  transform:rotate(-2deg) scale(1.05);
  filter:saturate(1.1) contrast(1.05);
  animation: drift 18s ease-in-out infinite;
}

.stApp:after{
  content:"";
  position:fixed;
  inset:0;
  pointer-events:none;
  background:
    /* scanlines */
    repeating-linear-gradient(180deg,
      rgba(255,255,255,.03) 0 1px,
      transparent 1px 6px);
  opacity:.18;
  mix-blend-mode: overlay;
  animation: scan 7s linear infinite;
}

@keyframes drift{
  0%,100%{transform:translate3d(0,0,0) rotate(-2deg) scale(1.05)}
  50%{transform:translate3d(-2%,1.5%,0) rotate(-2deg) scale(1.05)}
}
@keyframes scan{
  0%{transform:translateY(0)}
  100%{transform:translateY(12px)}
}

/* Glass container */
.glass-container{
  background: linear-gradient(135deg, rgba(255,255,255,.10), rgba(255,255,255,.05));
  border: 1px solid rgba(255,255,255,.12);
  border-radius: var(--r);
  padding: 22px;
  box-shadow: var(--shadow);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  position:relative;
  overflow:hidden;
}

.glass-container:before{
  content:"";
  position:absolute;
  inset:-2px;
  pointer-events:none;
  background:
    radial-gradient(900px 260px at 20% 0%, rgba(139,92,246,.28), transparent 55%),
    radial-gradient(700px 260px at 85% 10%, rgba(34,211,238,.20), transparent 60%);
  opacity:.55;
  filter: blur(6px);
}

/* Titles */
h1{
  font-weight: 900;
  letter-spacing: 0.18em;
  text-align:center;
  background: linear-gradient(90deg, #EAF0FF, var(--cyan));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
h2,h3{ color: var(--text); }

/* Tabs */
.stTabs [data-baseweb="tab-list"]{
  background: transparent;
  border-bottom: 1px solid rgba(255,255,255,0.10);
}
.stTabs [data-baseweb="tab"]{
  color: rgba(234,240,255,.55);
  font-size: 15px;
  letter-spacing: .08em;
}
.stTabs [aria-selected="true"]{
  color: var(--cyan) !important;
  background: transparent !important;
  border-bottom: 2px solid var(--cyan);
}

/* Inputs */
.stTextInput > div > div > input{
  background: rgba(11,15,31,.55) !important;
  border: 1px solid rgba(255,255,255,.14) !important;
  color: var(--text) !important;
  border-radius: 14px !important;
  height: 52px;
  font-size: 15px;
  transition: all .25s ease;
  box-shadow: inset 0 0 0 1px rgba(139,92,246,.08);
}
.stTextInput > div > div > input:focus{
  border-color: rgba(34,211,238,.35) !important;
  box-shadow: 0 0 0 1px rgba(34,211,238,.16), 0 0 24px rgba(34,211,238,.10);
  background: rgba(11,15,31,.78) !important;
}

/* Buttons */
.stButton > button{
  background: linear-gradient(135deg, rgba(139,92,246,.85), rgba(34,211,238,.35));
  border: 1px solid rgba(255,255,255,.14);
  color: white;
  border-radius: 16px;
  height: 52px;
  font-weight: 800;
  font-size: 14px;
  letter-spacing: .14em;
  text-transform: uppercase;
  box-shadow: 0 0 0 1px rgba(139,92,246,.10), 0 18px 36px rgba(0,0,0,.40);
  transition: transform .12s ease, filter .12s ease, box-shadow .12s ease;
}
.stButton > button:hover{
  transform: translateY(-1px);
  filter: brightness(1.05);
  box-shadow: 0 0 0 1px rgba(34,211,238,.12), 0 22px 46px rgba(0,0,0,.42);
}
.stButton > button:active{
  transform: translateY(0) scale(.99);
}

/* Chat containers */
.stChatMessage{
  background: rgba(0,0,0,.22) !important;
  border: 1px solid rgba(255,255,255,.10) !important;
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  border-radius: 18px !important;
  margin-bottom: 10px;
  box-shadow: 0 10px 26px rgba(0,0,0,.35);
}

/* Avatar */
.stChatMessage .stChatMessageAvatar{
  background: linear-gradient(135deg, var(--cyan), var(--violet)) !important;
  box-shadow: 0 0 18px rgba(34,211,238,.18);
}

/* Differentiate user/assistant a bit (Streamlit markup is limited, but we can tint generally) */
div[data-testid="stChatMessage"][data-avatar="assistant"]{
  border-color: rgba(139,92,246,.22) !important;
  background: linear-gradient(135deg, rgba(139,92,246,.16), rgba(0,0,0,.22)) !important;
}
div[data-testid="stChatMessage"][data-avatar="user"]{
  border-color: rgba(34,211,238,.20) !important;
  background: linear-gradient(135deg, rgba(34,211,238,.12), rgba(0,0,0,.22)) !important;
}

/* Progress */
.stProgress > div > div > div > div{
  background: linear-gradient(90deg, var(--cyan), var(--violet));
}

/* Sidebar (optional - keep subtle) */
section[data-testid="stSidebar"]{
  background: rgba(0,0,0,.20);
  border-right: 1px solid rgba(255,255,255,.08);
  backdrop-filter: blur(18px);
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
    row = [username, pin, 0, today_str, today_str, "{}", "[]", "FALSE"]
    sheet.append_row(row)
    return "OK"

def update_db_field(row_num, col_num, value):
    sheet = get_db()
    if sheet: sheet.update_cell(row_num, col_num, value)

def save_history(row_num, messages):
    try:
        history_str = json.dumps(messages[-30:]) 
        update_db_field(row_num, 7, history_str)
    except: pass

def update_onboarding_data(row_num, key, value):
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
    st.session_state.onboarding_step = -1

# === ЭКРАН ВХОДА ===
if not st.session_state.logged_in:
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h1>MUKTI PORTAL</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94a3b8; margin-bottom: 30px;'>Система освобождения сознания</p>", unsafe_allow_html=True)
    
    st.markdown('<div class="glass-container">', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["ВХОД", "РЕГИСТРАЦИЯ"])
    
    with tab1: # ВХОД
        st.write("")
        l_user = st.text_input("Твое Имя", key="l_u")
        l_pin = st.text_input("PIN-код (4 цифры)", type="password", key="l_p", max_chars=4)
        
        if st.button("ВОЙТИ", use_container_width=True):
            with st.spinner("Синхронизация..."):
                user_data, row_num = load_user(l_user)
                if user_data and str(user_data[1]) == str(l_pin):
                    st.session_state.logged_in = True
                    st.session_state.username = l_user
                    st.session_state.row_num = row_num
                    st.session_state.streak = int(user_data[2]) if len(user_data) > 2 else 0
                    st.session_state.last_active = user_data[3] if len(user_data) > 3 else str(date.today())
                    st.session_state.reg_date = user_data[4] if len(user_data) > 4 else str(date.today())
                    st.session_state.vip = (str(user_data[7]).upper() == "TRUE") if len(user_data) > 7 else False
                    
                    try: st.session_state.messages = json.loads(user_data[6]) if len(user_data) > 6 else []
                    except: st.session_state.messages = []

                    try:
                        ob_data = json.loads(user_data[5])
                        st.session_state.stop_factor = ob_data.get("stop_factor", "Свобода")
                        if "goal" in ob_data and "stop_factor" in ob_data:
                            st.session_state.onboarding_step = -1
                        else:
                            st.session_state.onboarding_step = 0
                    except:
                        st.session_state.onboarding_step = 0
                        st.session_state.stop_factor = "Свобода"
                    
                    st.rerun()
                else:
                    st.error("Неверное Имя или PIN.")

    with tab2: # РЕГИСТРАЦИЯ
        st.write("")
        st.info("Придумай Имя и PIN. Система запомнит тебя.")
        r_user = st.text_input("Новое Имя", key="r_u")
        r_pin = st.text_input("Новый PIN (4 цифры)", type="password", key="r_p", max_chars=4)
        
        if st.button("СОЗДАТЬ ПРОФИЛЬ", use_container_width=True):
            if r_user and len(r_pin) == 4:
                res = register_user(r_user, r_pin)
                if res == "OK":
                    with st.spinner("Создание нейросвязей..."):
                        time.sleep(1)
                        user_data, row_num = load_user(r_user)
                        
                        if user_data:
                            st.session_state.logged_in = True
                            st.session_state.username = r_user
                            st.session_state.row_num = row_num
                            st.session_state.streak = 0
                            st.session_state.last_active = str(date.today())
                            st.session_state.reg_date = str(date.today())
                            st.session_state.vip = False
                            st.session_state.messages = []
                            st.session_state.stop_factor = "Свобода"
                            st.session_state.onboarding_step = 0 
                            
                            st.success("Профиль создан! Входим...")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Ошибка авто-входа.")
                elif res == "TAKEN":
                    st.error("Это Имя уже занято.")
                else:
                    st.error("Ошибка соединения.")
            else:
                st.warning("Введи Имя и 4 цифры PIN.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# === ВНУТРИ СИСТЕМЫ ===
else:
    # --- ЭТАП ОНБОРДИНГА ---
    if st.session_state.onboarding_step >= 0:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align:center;'>ЗНАКОМСТВО</h2>", unsafe_allow_html=True)
        
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)

        if st.session_state.onboarding_step == 0:
            st.write(f"👋 **Привет, {st.session_state.username}.**")
            st.write("Я MUKTI - модератор этого пространства, где ты обретаешь свободу от зависимости.")
            st.write("Скажи: ты уже читал книгу **'Кто такой Алкоголь'**?")
            
            c1, c2 = st.columns(2)
            if c1.button("ДА, ЧИТАЛ", use_container_width=True):
                update_onboarding_data(st.session_state.row_num, "read_book", True)
                st.session_state.onboarding_step = 1
                st.rerun()
            if c2.button("НЕТ, НЕ ЧИТАЛ", use_container_width=True):
                st.info("Советую прочитать, чтобы мы понимали друг друга.")
                st.markdown("👉 [**Скачать книгу на LitRes**](https://www.litres.ru/book/roman-vybornov/pochemu-ya-nikogo-ne-em-72075331/)")
                if st.button("Продолжить пока так", use_container_width=True):
                    update_onboarding_data(st.session_state.row_num, "read_book", False)
                    st.session_state.onboarding_step = 1
                    st.rerun()
                    
        elif st.session_state.onboarding_step == 1:
            st.write("🎯 **Цель.**")
            st.write("Напиши мне: **Ради чего ты здесь?** (Семья, Деньги, Здоровье, просто надоело...)")
            
            if goal_input := st.chat_input("Моя цель..."):
                update_onboarding_data(st.session_state.row_num, "goal", goal_input)
                st.session_state.onboarding_step = 2
                st.rerun()
                
        elif st.session_state.onboarding_step == 2:
            st.write("⚓️ **Стоп-кран.**")
            st.write("Что может тебя остановить, если вдруг захочется выпить?")
            
            if trigger_input := st.chat_input("Меня остановит..."):
                data = update_onboarding_data(st.session_state.row_num, "stop_factor", trigger_input)
                st.session_state.stop_factor = trigger_input
                
                # Финал онбординга
                st.session_state.onboarding_step = -1
                
                welcome_msg = "Профиль настроен. Я включил защиту.\nНажми кнопку **'СЕГОДНЯ ЧИСТ'** наверху, чтобы запустить счетчик свободы."
                st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
                save_history(st.session_state.row_num, st.session_state.messages)
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

    # --- ОСНОВНОЙ РАБОЧИЙ СТОЛ ---
    else:
        # SOS LOGIC
        if "sos_mode" not in st.session_state: st.session_state.sos_mode = False

        if st.session_state.sos_mode:
            st.markdown("""
            <div style="background: rgba(220, 38, 38, 0.15); border: 1px solid #ef4444; padding: 20px; border-radius: 16px; text-align: center; margin-bottom: 20px; backdrop-filter: blur(10px); box-shadow: 0 0 30px rgba(220,38,38, 0.4);">
                <h2 style="color: #fca5a5; margin:0; text-shadow: 0 0 10px #ef4444; letter-spacing: 3px;">⚠️ АТАКА ПАРАЗИТА</h2>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"<div style='text-align:center; margin-bottom:20px;'>Твой якорь:<br><strong style='font-size:24px; color:#22D3EE;'>{st.session_state.stop_factor}</strong></div>", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            c1.info("💨 **ДЫХАНИЕ**\n\n4 сек Вдох - 4 сек Пауза - 4 сек Выдох.\n\nПовтори 5 раз.")
            c2.warning("⚡️ **ДЕЙСТВИЕ**\n\n20 приседаний.\n\nПрямо сейчас. Сжги адреналин.")
            
            if st.button("Я ВЕРНУЛ КОНТРОЛЬ", use_container_width=True):
                st.session_state.sos_mode = False
                
                follow_up = "Сигнал принят. Ты справился. Горжусь.\n\nРасскажи, что именно случилось? Откуда пришла тяга?"
                st.session_state.messages.append({"role": "assistant", "content": follow_up})
                save_history(st.session_state.row_num, st.session_state.messages)
                st.rerun()

        else:
            # HEADER
            st.markdown(f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;'><div style='font-weight:800; font-size:20px; color:#EAF0FF;'>MUKTI <span style='color:#22D3EE;'>//</span> ONLINE</div><div style='text-align:right; font-size:12px; color:#94a3b8;'>АГЕНТ<br><span style='color:#22D3EE;'>{st.session_state.username}</span></div></div>", unsafe_allow_html=True)
            
            # DASHBOARD
            st.markdown('<div class="glass-container" style="padding: 15px; margin-bottom: 20px;">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 1.5, 1])
            
            with col1:
                 st.markdown(f"<div style='text-align:center;'><div style='font-size: 10px; color: #94a3b8; letter-spacing: 2px; text-transform:uppercase;'>Свобода</div><div style='font-size: 36px; font-weight:bold; color: #fff; text-shadow: 0 0 15px rgba(34, 211, 238, 0.6);'>{st.session_state.streak}</div></div>", unsafe_allow_html=True)
            
            with col2:
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
                             st.toast("Счетчик перезапущен.", icon="🔄")
                        else:
                             new_streak = st.session_state.streak + 1
                             st.toast("Система обновлена.", icon="🔋")
                             
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

            # CHAT AREA
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            
            # LIMITS CHECK
            locked = False
            if not st.session_state.vip:
                 try: reg_d = datetime.strptime(st.session_state.reg_date, "%Y-%m-%d").date()
                 except: reg_d = date.today()
                 limit = 7 if (date.today() - reg_d).days == 0 else 3
                 msgs_today = sum(1 for m in st.session_state.messages if m["role"] == "user")
                 if msgs_today >= limit: locked = True

            if locked:
                st.markdown("""
                <div class="glass-container" style="text-align:center;">
                    <h3 style='color: #94a3b8; margin:0;'>🔒 Лимит энергии исчерпан</h3>
                    <p style='color: #EAF0FF; font-size: 14px; margin-top: 10px;'>
                        Напиши слово <b>MUKTI</b> Роману, чтобы продолжить общение без ограничений.
                    </p>
                    <a href="https://t.me/Vybornov_Roman" target="_blank" class="vip-link">👉 НАПИСАТЬ РОМАНУ</a>
                    <br><br>
                </div>
                """, unsafe_allow_html=True)
                
                code = st.text_input("Введи код доступа сюда:")
                if st.button("АКТИВИРОВАТЬ КОД", use_container_width=True):
                    if code == VIP_CODE:
                        update_db_field(st.session_state.row_num, 8, "TRUE")
                        st.session_state.vip = True
                        st.success("Доступ открыт!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Неверный код.")
            else:
                if prompt := st.chat_input("Введи сообщение..."):
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.markdown(prompt)
                    
                    with st.chat_message("assistant"):
                        with st.spinner("Анализ..."):
                            system_prompt = f"""
                            Ты - MUKTI. Пользователь: {st.session_state.username}.
                            Твоя роль: Модератор пространства свободы. Друг, наставник.
                            
                            СТИЛЬ ОБЩЕНИЯ:
                            1. Простой, понятный, человеческий язык. Без "зауми".
                            2. НЕ используй слова: "протокол", "аватар", "модификация", "компенсация".
                            3. Вместо этого говори: "привычка", "ты", "действия", "изменения".
                            4. Алкоголь называй "Паразит".
                            5. Используй обычное короткое тире (-) вместо длинного.
                            6. Ответы краткие (3-4 предложения).
                            7. Задавай вопросы, чтобы поддержать разговор.
                            
                            БАЗА ЗНАНИЙ: {BOOK_SUMMARY}
                            МОТИВАЦИЯ ЮЗЕРА: {st.session_state.get('stop_factor')}
                            """
                            full_prompt = f"{system_prompt}\nИстория:\n{st.session_state.messages[-5:]}\nUser: {prompt}"
                            
                            # --- НОВЫЙ БЛОК ОТПРАВКИ С РЕЗЕРВНЫМ КАНАЛОМ ---
                            try:
                                # Попытка 1: Основной канал
                                response = model.generate_content(full_prompt)
                                response_text = response.text
                            except Exception as e:
                                # Попытка 2: Если сбой, ждем 2 секунды и пробуем Резервный канал (Flash)
                                time.sleep(2)
                                try:
                                    backup_model = genai.GenerativeModel('gemini-1.5-flash')
                                    response = backup_model.generate_content(full_prompt)
                                    response_text = response.text
                                except Exception as e2:
                                    # Попытка 3: Если совсем всё плохо
                                    response_text = "⚠️ Каналы перегружены. Подожди 5 секунд и отправь снова."
                            
                            # Вывод результата
                            st.markdown(response_text)
                            st.session_state.messages.append({"role": "assistant", "content": response_text})
                            save_history(st.session_state.row_num, st.session_state.messages)

        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.sidebar.button("ВЫХОД ИЗ СИСТЕМЫ"):
             st.session_state.logged_in = False
             st.rerun()
