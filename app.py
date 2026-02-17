import streamlit as st
import google.generativeai as genai
from datetime import datetime, date
import time
import json
import random

# ИМПОРТ МОДУЛЕЙ
import settings
import database as db

# --- НАСТРОЙКИ ---
VIP_CODE = st.secrets.get("VIP_CODE", settings.VIP_CODE_DEFAULT)
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"] if "GOOGLE_API_KEY" in st.secrets else "NO_KEY"
genai.configure(api_key=GOOGLE_API_KEY)

try:
    from book import BOOK_SUMMARY
except ImportError:
    BOOK_SUMMARY = "Методика освобождения."

# --- ИНИЦИАЛИЗАЦИЯ МОДЕЛИ ---
@st.cache_resource
def get_model():
    try:
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Приоритет Flash (скорость), потом Pro
        priority = ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']
        for p in priority:
            if p in available: return genai.GenerativeModel(p)
        return genai.GenerativeModel(available[0]) if available else None
    except: return None

model = get_model()
settings.load_css() # ЗАГРУЗКА ДИЗАЙНА

# --- СОСТОЯНИЕ (SESSION STATE) ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "calibration_step" not in st.session_state: st.session_state.calibration_step = 0

# ==========================================
# 1. ЛЕНДИНГ И ВХОД
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<br><h1>MUKTI</h1>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center; color:#00E676; margin-bottom:30px;'>Персональный ИИ-ассистент для выхода из зависимости</div>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="glass-container">
        <ul style="padding-left:10px; color:#ccc;">
            <li><b>💠 Интеллект:</b> Диалог с наставником 24/7.</li>
            <li><b>🛡 Защита:</b> Кнопка SOS и нейро-техники.</li>
            <li><b>🧠 Философия:</b> Разделение Личности и Паразита.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["ВХОД", "РЕГИСТРАЦИЯ"])
    
    with tab1:
        lu = st.text_input("ИМЯ", key="l_u")
        lp = st.text_input("PIN", type="password", key="l_p", max_chars=4)
        if st.button("ВОЙТИ", use_container_width=True):
            udata, row = db.load_user(lu)
            if udata and str(udata[1]) == str(lp):
                st.session_state.logged_in = True
                st.session_state.username = lu
                st.session_state.row_num = row
                st.session_state.streak = int(udata[2])
                st.session_state.last_active = udata[3]
                st.session_state.reg_date = udata[4]
                st.session_state.vip = (str(udata[7]).upper() == "TRUE") if len(udata)>7 else False
                try: st.session_state.messages = json.loads(udata[6])
                except: st.session_state.messages = []
                st.session_state.user_profile = db.get_profile(row)
                st.rerun()
            else: st.error("Неверный вход.")

    with tab2:
        ru = st.text_input("НОВОЕ ИМЯ", key="r_u")
        rp = st.text_input("НОВЫЙ PIN", type="password", key="r_p", max_chars=4)
        if st.button("СОЗДАТЬ", use_container_width=True):
            if db.register_user(ru, rp) == "OK":
                st.success("Готово! Входим...")
                time.sleep(1)
                # Авто-вход
                udata, row = db.load_user(ru)
                st.session_state.logged_in = True
                st.session_state.username = ru
                st.session_state.row_num = row
                st.session_state.streak = 0
                st.session_state.last_active = str(date.today())
                st.session_state.reg_date = str(date.today())
                st.session_state.vip = False
                st.session_state.messages = []
                st.session_state.user_profile = {}
                st.rerun()
            else: st.error("Имя занято.")

# ==========================================
# 2. ВНУТРИ СИСТЕМЫ
# ==========================================
else:
    # --- ЭКРАН 1: ПРОВЕРКА КНИГИ (КАК РАНЬШЕ) ---
    profile = st.session_state.get('user_profile', {})
    
    # Если в профиле нет отметки про книгу - показываем этот экран
    if 'read_book' not in profile:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<div class='glass-container' style='text-align:center;'>", unsafe_allow_html=True)
        st.markdown("<h3>БАЗА ЗНАНИЙ</h3>", unsafe_allow_html=True)
        st.write("Чтобы мы говорили на одном языке, ты должен знать теорию.")
        st.write("Ты читал книгу **'Кто такой Алкоголь'**?")
        
        c1, c2 = st.columns(2)
        if c1.button("ДА, ЧИТАЛ", use_container_width=True):
            db.update_profile(st.session_state.row_num, "read_book", "Да")
            st.session_state.user_profile['read_book'] = "Да"
            st.rerun()
            
        if c2.button("НЕТ", use_container_width=True):
            st.info("Рекомендую прочитать. Это усилит эффект на 80%.")
            st.markdown("👉 [**Скачать на LitRes**](https://www.litres.ru/book/roman-vybornov/pochemu-ya-nikogo-ne-em-72075331/)")
            if st.button("ПРОДОЛЖИТЬ БЕЗ КНИГИ", use_container_width=True):
                db.update_profile(st.session_state.row_num, "read_book", "Нет")
                st.session_state.user_profile['read_book'] = "Нет"
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop() # Останавливаем выполнение остального кода

    # --- ЭКРАН 2: SOS РЕЖИМ ---
    if "sos_mode" not in st.session_state: st.session_state.sos_mode = False
    
    if st.session_state.sos_mode:
        techs = [
            {"name": "❄️ ЛЕДЯНОЙ СБРОС", "d": "Умой лицо ледяной водой. Это рефлекс ныряльщика - он гасит панику."},
            {"name": "⏪ ПЕРЕМОТКА", "d": "Проиграй сценарий до похмелья. Не смотри трейлер, смотри финал."},
            {"name": "🗣 ДИССОЦИАЦИЯ", "d": "Скажи: 'Это не я хочу. Это Паразит просит еды'."}
        ]
        t = random.choice(techs)
        st.markdown(f"<div style='border:1px solid red; padding:20px; border-radius:15px; background:rgba(50,0,0,0.8); text-align:center;'><h2>{t['name']}</h2><p>{t['d']}</p></div>", unsafe_allow_html=True)
        if st.button("Я ВЕРНУЛ КОНТРОЛЬ", use_container_width=True):
            st.session_state.sos_mode = False
            st.rerun()
        st.stop()

    # --- ЭКРАН 3: ДАШБОРД ---
    # Хедер
    st.markdown(f"<div style='display:flex; justify-content:space-between; margin-bottom:15px;'><div>MUKTI <span style='color:#00E676'>// ONLINE</span></div><div>{st.session_state.username}</div></div>", unsafe_allow_html=True)

    # Статистика
    st.markdown("<div class='glass-container'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    
    with c1:
        st.markdown(f"<div style='text-align:center; font-size:30px; font-weight:bold;'>{st.session_state.streak}</div>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:center; font-size:10px;'>ДНЕЙ</div>", unsafe_allow_html=True)
    
    with c2:
        today = date.today()
        try: last = datetime.strptime(str(st.session_state.last_active), "%Y-%m-%d").date()
        except: last = today
        delta = (today - last).days
        
        if delta == 0 and st.session_state.streak > 0:
            st.button("✅ ЗАЧТЕНО", disabled=True, use_container_width=True)
        else:
            if st.button("✨ СЕГОДНЯ ЧИСТ", use_container_width=True):
                # ЛОГИКА НАЖАТИЯ
                new_streak = 1 if delta > 1 and st.session_state.streak > 0 else st.session_state.streak + 1
                db.update_field(st.session_state.row_num, 3, new_streak)
                db.update_field(st.session_state.row_num, 4, str(today))
                st.session_state.streak = new_streak
                st.session_state.last_active = str(today)
                
                # Если нет профиля (первый раз или сброс) - включаем калибровку
                if 'frequency' not in st.session_state.user_profile:
                    st.session_state.calibration_step = 1
                    msg = "День зачтен. Теперь давай настроим защиту. Ответь на 4 вопроса.\n\n1. **Как часто Паразит обычно атакует?** (Каждый день, Пятница, Запои?)"
                else:
                    msg = "Данные обновлены. Как твое состояние сегодня?"
                
                st.session_state.messages.append({"role": "assistant", "content": msg})
                db.save_history(st.session_state.row_num, st.session_state.messages)
                st.rerun()

    with c3:
        if st.button("🚨 SOS", use_container_width=True):
            st.session_state.sos_mode = True
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # ЧАТ
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    # ВВОД (ПРОВЕРКА ЛИМИТОВ И VIP)
    limit = settings.LIMIT_NEW_USER if st.session_state.streak < 3 else settings.LIMIT_OLD_USER
    msgs_count = sum(1 for m in st.session_state.messages if m["role"] == "user")
    
    is_locked = (not st.session_state.vip) and (msgs_count >= limit)
    
    if is_locked:
        # ВЕРНУЛ ПОЛЕ ВВОДА КОДА
        st.markdown("<div class='glass-container' style='text-align:center;'>🔒 <b>Лимит исчерпан</b><br>Пиши <b>MUKTI</b>: <a href='https://t.me/Vybornov_Roman'>Роману</a></div>", unsafe_allow_html=True)
        code_input = st.text_input("Есть код? Введи сюда:", key="vip_in")
        if st.button("АКТИВИРОВАТЬ", use_container_width=True):
            if code_input == VIP_CODE:
                db.update_field(st.session_state.row_num, 8, "TRUE")
                st.session_state.vip = True
                st.success("VIP активирован!")
                time.sleep(1)
                st.rerun()
            else: st.error("Неверный код")
    else:
        if prompt := st.chat_input("..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)

            # --- ЛОГИКА КАЛИБРОВКИ (ВОПРОСЫ) ---
            step = st.session_state.calibration_step
            if step > 0:
                resp = ""
                if step == 1:
                    db.update_profile(st.session_state.row_num, "frequency", prompt)
                    resp = "2. **В какие моменты тяга самая сильная?** (Стресс, Скука, Друзья?)"
                    st.session_state.calibration_step = 2
                elif step == 2:
                    db.update_profile(st.session_state.row_num, "triggers", prompt)
                    resp = "3. **Твой опыт борьбы?** (Первый раз или были срывы?)"
                    st.session_state.calibration_step = 3
                elif step == 3:
                    db.update_profile(st.session_state.row_num, "history", prompt)
                    resp = "4. **Что чувствуешь сейчас?** (Страх, Уверенность, Вину?)"
                    st.session_state.calibration_step = 4
                elif step == 4:
                    db.update_profile(st.session_state.row_num, "state", prompt)
                    st.session_state.user_profile = db.get_profile(st.session_state.row_num)
                    resp = "Профиль создан. **Ради какой Великой Цели ты это делаешь?**"
                    st.session_state.calibration_step = 0
                
                with st.chat_message("assistant"): st.markdown(resp)
                st.session_state.messages.append({"role": "assistant", "content": resp})
                db.save_history(st.session_state.row_num, st.session_state.messages)

            # --- ЛОГИКА AI ОТВЕТА ---
            else:
                with st.chat_message("assistant"):
                    with st.spinner("..."):
                        # Берем промпт из settings.py
                        sys_prompt = settings.get_system_prompt(
                            st.session_state.username, 
                            st.session_state.user_profile, 
                            BOOK_SUMMARY
                        )
                        full_p = f"{sys_prompt}\nИстория:\n{st.session_state.messages[-5:]}\nUser: {prompt}"
                        
                        # Retry
                        txt = None
                        for i in range(3):
                            if model:
                                try:
                                    txt = model.generate_content(full_p).text
                                    break
                                except: time.sleep(1)
                        
                        if txt:
                            st.markdown(txt)
                            st.session_state.messages.append({"role": "assistant", "content": txt})
                            db.save_history(st.session_state.row_num, st.session_state.messages)
                        else: st.error("Сбой связи")

    if st.sidebar.button("ВЫХОД"):
        st.session_state.logged_in = False
        st.rerun()
