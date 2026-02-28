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

# --- МОДЕЛЬ ---
@st.cache_resource
def get_model():
    try:
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority = ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']
        for p in priority:
            if p in available: return genai.GenerativeModel(p)
        return genai.GenerativeModel(available[0]) if available else None
    except: return None

model = get_model()
settings.load_css() 

# --- СОСТОЯНИЕ ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "calibration_step" not in st.session_state: st.session_state.calibration_step = 0
if "current_view" not in st.session_state: st.session_state.current_view = "chat"

# ==========================================
# ФУНКЦИЯ: ИНТЕРФЕЙС ДНЕВНИКА
# ==========================================
def render_diary():
    st.markdown("<h2 style='text-align: center; color: #00E676;'>ДНЕВНИК СВОБОДЫ</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #A0A0A0;'>Алкоголь живет в тумане. Здесь мы включаем свет.</p>", unsafe_allow_html=True)
    
    tab_mirror, tab_energy, tab_matrix, tab_sos = st.tabs(["🪞 ЗЕРКАЛО", "⚡ ЭНЕРГИЯ", "📊 МАТРИЦА", "🚨 SOS"])
    
    # --- ВКЛАДКА 1: ЗЕРКАЛО ---
    with tab_mirror:
        st.markdown("### Взлом системы (Анализ атаки Гостя)")
        with st.form("mirror_form"):
            context = st.text_input("Контекст (Где ты был? Что делал?)")
            trick = st.text_area("Трюк Гостя (Что он тебе говорил/обещал?)")
            intensity = st.slider("Интенсивность тяги (1 - шепот, 10 - крик)", 1, 10, 5)
            action = st.selectbox("Чем перехватил импульс?", 
                                  ["Вода + дыхание", "Прогулка", "Фокус на другом", "Написал в чат", "Другое"])
            win_phrase = st.text_input("Какая мысль сработала лучше всего?")
            
            submit_mirror = st.form_submit_button("💾 СОХРАНИТЬ ЛОГ")
            if submit_mirror:
                st.success("Лог Зеркала успешно загружен в Матрицу! (Пока это просто тест дизайна)")

    # --- ВКЛАДКА 2: ЭНЕРГИЯ ---
    with tab_energy:
        st.markdown("### Регенерация Аватара")
        with st.form("energy_form"):
            col1, col2 = st.columns(2)
            with col1:
                sleep = st.number_input("Сон (часов)", min_value=0.0, max_value=24.0, value=7.0, step=0.5)
                energy_level = st.select_slider("Уровень энергии", options=["Истощен", "Слабость", "Норма", "Заряжен", "Мощь"])
            with col2:
                money_saved = st.number_input("Сохранено денег (₽)", min_value=0, step=100)
                time_saved = st.number_input("Возвращено времени (ч)", min_value=0.0, step=0.5)
                
            small_win = st.text_input("Маленькая победа за сегодня")
            submit_energy = st.form_submit_button("🔋 ЗАРЯДИТЬ БАТАРЕИ")
            if submit_energy:
                st.success("Параметры энергии обновлены! (Пока это просто тест дизайна)")

    # --- ВКЛАДКА 3: МАТРИЦА ---
    with tab_matrix:
        st.markdown("### Панель Наблюдателя")
        col1, col2, col3 = st.columns(3)
        col1.metric("Дней Свободы", "12", delta="+1 день")
        col2.metric("Сохранено денег", "15 400 ₽", delta="+800 ₽")
        col3.metric("Уровень Сознания", "ПРОБУЖДЕНИЕ")
        
        st.progress(12) 
        st.markdown("**Цель:** 100 дней (Процесс дефрагментации мозга)")

    # --- ВКЛАДКА 4: SOS ---
    with tab_sos:
        st.markdown("<h3 style='color: #FF3D00;'>🚨 ЭКСТРЕННЫЙ ПЕРЕХВАТ</h3>", unsafe_allow_html=True)
        st.warning("**Задача:** Не «победить», а сорвать сценарий. Тяга длится максимум 10-15 минут.")
        
        st.markdown("#### Фильтр реальности:")
        st.checkbox("Если я выпью — что будет через 1 час?")
        st.checkbox("Если я НЕ выпью — что будет через 1 час?")
        
        st.markdown("#### Быстрое действие (Выбери одно на 10 минут):")
        st.radio("Доступные инструменты:", 
                 ["💧 Выпить стакан воды и сделать 10 глубоких вдохов", 
                  "🚶‍♂️ Выйти на улицу (без телефона) на 10 минут", 
                  "🚿 Холодная вода на запястья / лицо",
                  "✍️ Записать мысли в 'Зеркало'"])
        if st.button("⚡ АКТИВИРОВАТЬ ЗАЩИТУ"):
            st.info("Засеки 10 минут. Если не отпустит - возвращайся за новым действием.")


# ==========================================
# АВТОРИЗАЦИЯ
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: #00E676;'>MUKTI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #A0A0A0;'>Система выхода из матрицы зависимости</p>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["ВХОД", "РЕГИСТРАЦИЯ"])
    
    with tab1:
        with st.form("login_form"):
            user_in = st.text_input("Имя Аватара").strip().lower()
            pin_in = st.text_input("PIN-код (4 цифры)", type="password").strip()
            if st.form_submit_button("ВОЙТИ"):
                if user_in and pin_in:
                    row_data, r_num = db.load_user(user_in)
                    if row_data and row_data[1] == pin_in:
                        st.session_state.logged_in = True
                        st.session_state.username = user_in
                        st.session_state.row_num = r_num
                        st.session_state.is_vip = (len(row_data) > 7 and row_data[7] == "TRUE")
                        
                        try: st.session_state.user_profile = json.loads(row_data[5]) if len(row_data)>5 else {}
                        except: st.session_state.user_profile = {}
                        
                        try: st.session_state.messages = json.loads(row_data[6]) if len(row_data)>6 else []
                        except: st.session_state.messages = []
                        
                        if not st.session_state.messages:
                            st.session_state.calibration_step = 1
                        
                        # Расчет дней в системе
                        try:
                            reg_date = datetime.strptime(row_data[3], "%Y-%m-%d").date()
                            st.session_state.days_in_system = (date.today() - reg_date).days
                        except:
                            st.session_state.days_in_system = 0
                            
                        st.rerun()
                    else: st.error("Ошибка доступа. Неверное имя или PIN.")
                else: st.warning("Введи данные.")

    with tab2:
        with st.form("reg_form"):
            new_user = st.text_input("Придумай Имя Аватара").strip().lower()
            new_pin = st.text_input("Придумай PIN-код (4 цифры)", type="password").strip()
            vip_in = st.text_input("Код доступа (если есть)").strip()
            if st.form_submit_button("СОЗДАТЬ ПРОФИЛЬ"):
                if len(new_pin) != 4 or not new_pin.isdigit():
                    st.error("PIN должен состоять из 4 цифр.")
                elif new_user:
                    res = db.register_user(new_user, new_pin)
                    if res == "OK":
                        if vip_in == VIP_CODE:
                            _, r_num = db.load_user(new_user)
                            db.update_field(r_num, 8, "TRUE")
                        st.success("Профиль создан! Теперь войди в систему на вкладке ВХОД.")
                    elif res == "TAKEN": st.error("Это имя уже занято.")
                    else: st.error("Ошибка БД.")
                else: st.warning("Введи имя.")

# ==========================================
# КАЛИБРОВКА (АНКЕТА)
# ==========================================
elif st.session_state.calibration_step > 0:
    st.markdown("### 🛠 КАЛИБРОВКА АВАТАРА")
    step = st.session_state.calibration_step
    
    def next_step(key, val):
        st.session_state.user_profile[key] = val
        db.update_profile(st.session_state.row_num, key, val)
        st.session_state.calibration_step += 1
        st.rerun()

    if step == 1:
        st.write("Ты читал книгу «Кто такой Алкоголь»?")
        if st.button("Да, читал"): next_step("read_book", "Да")
        if st.button("Нет, не читал"): next_step("read_book", "Нет")
    elif step == 2:
        st.write("Как часто Гость берет контроль? (Как часто пьешь?)")
        if st.button("Каждый день"): next_step("frequency", "Каждый день")
        if st.button("Раз в неделю (Пятница/Выходные)"): next_step("frequency", "Выходные")
        if st.button("Редко, но метко (Запои)"): next_step("frequency", "Запои")
    elif step == 3:
        st.write("Что обычно служит триггером?")
        if st.button("Усталость после работы"): next_step("triggers", "Стресс/Усталость")
        if st.button("Скука, пустота"): next_step("triggers", "Скука")
        if st.button("Компании, праздники"): next_step("triggers", "Социум")
    elif step == 4:
        st.write("Какая попытка выйти из Матрицы по счету?")
        if st.button("Первая осознанная"): next_step("history", "Первая")
        if st.button("Пробовал, срывался (1-3 раза)"): next_step("history", "Были срывы")
        if st.button("Борюсь давно"): next_step("history", "Долгая борьба")
    elif step == 5:
        st.write("Что чувствуешь прямо сейчас?")
        if st.button("Страх, что не получится"): next_step("state", "Страх/Сомнения")
        if st.button("Решимость, я готов"): next_step("state", "Решимость")
        if st.button("Тягу, Гость уже шепчет"): next_step("state", "Тяга прямо сейчас")
    else:
        st.session_state.calibration_step = 0
        st.session_state.messages.append({"role": "assistant", "content": f"Калибровка завершена. Приветствую, {st.session_state.username}. Я — твой ИИ-наставник. Матрица зафиксировала твои параметры. С чего начнем?"})
        db.save_history(st.session_state.row_num, st.session_state.messages)
        st.rerun()

# ==========================================
# ОСНОВНОЙ РАБОЧИЙ ЭКРАН (ЧАТ ИЛИ ДНЕВНИК)
# ==========================================
else:
    # --- БОКОВОЕ МЕНЮ (САЙДБАР) ---
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        st.markdown("---")
        
        if st.button("💬 ТЕРМИНАЛ (Чат)"):
            st.session_state.current_view = "chat"
            st.rerun()
            
        if st.button("📓 ДНЕВНИК СВОБОДЫ"):
            st.session_state.current_view = "diary"
            st.rerun()
            
        st.markdown("---")
        if st.button("🚪 ВЫХОД"):
            st.session_state.logged_in = False
            st.rerun()


    # ОПРЕДЕЛЯЕМ, ЧТО ПОКАЗЫВАТЬ
    if st.session_state.current_view == "diary":
        render_diary()
        
    else:
        # --- ИНТЕРФЕЙС ЧАТА ---
        # Подсчет лимитов
        msgs_today = 0
        today_str = str(date.today())
        
        row_data, _ = db.load_user(st.session_state.username)
        if row_data:
            last_date = row_data[4] if len(row_data) > 4 else today_str
            msgs_today = int(row_data[2]) if len(row_data) > 2 and row_data[2].isdigit() else 0
            if last_date != today_str:
                msgs_today = 0
                db.update_field(st.session_state.row_num, 4, today_str)
                db.update_field(st.session_state.row_num, 3, msgs_today)

        is_newbie = st.session_state.days_in_system <= 3
        current_limit = settings.LIMIT_NEW_USER if is_newbie else settings.LIMIT_OLD_USER
        
        if st.session_state.is_vip:
            limit_text = "∞ (VIP)"
            can_send = True
        else:
            limit_text = f"{msgs_today} / {current_limit}"
            can_send = msgs_today < current_limit

        col1, col2 = st.columns([3, 1])
        with col1: st.markdown(f"**Статус:** {'🟢 Режим Адаптации' if is_newbie else '🔵 Основной Режим'}")
        with col2: st.markdown(f"**Энергия ИИ:** {limit_text}")

        # ИСТОРИЯ
        for msg in st.session_state.messages:
            if msg["role"] != "system":
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # ЛИМИТЫ
        if not can_send:
            st.markdown(f"""
            <div class='limit-alert'>
                <b>⚠️ Энергия наставника исчерпана на сегодня.</b><br>
                Сделай паузу. Подыши. Понаблюдай за мыслями.<br>
                Возвращайся завтра, система перезагрузится.
            </div>
            """, unsafe_allow_html=True)
            
        # ВВОД
        elif prompt := st.chat_input("Напиши мне..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)

            if not st.session_state.is_vip:
                msgs_today += 1
                db.update_field(st.session_state.row_num, 3, msgs_today)

            # ПАСХАЛКА
            easter_eggs = ["хочу выпить", "пиво", "накатить", "срыв"]
            if any(word in prompt.lower() for word in easter_eggs):
                resp = random.choice([
                    "🚨 **ВНИМАНИЕ! ОБНАРУЖЕНА АКТИВНОСТЬ ГОСТЯ.** 🚨\nЭто не твои мысли. Сделай 10 глубоких вдохов. Ты сильнее программы.",
                    "Активирован защитный протокол. Напоминаю: алкоголь забирает у тебя завтрашний день, чтобы дать в долг сегодня под бешеные проценты."
                ])
                with st.chat_message("assistant"): st.markdown(resp)
                st.session_state.messages.append({"role": "assistant", "content": resp})
                db.save_history(st.session_state.row_num, st.session_state.messages)

            # AI ОТВЕТ
            else:
                with st.chat_message("assistant"):
                    with st.spinner("..."):
                        sys_prompt = settings.get_system_prompt(
                            st.session_state.username, 
                            st.session_state.user_profile, 
                            BOOK_SUMMARY
                        )
                        full_p = f"{sys_prompt}\nИстория:\n{st.session_state.messages[-5:]}\nUser: {prompt}"
                        
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
                        else: st.error("Сбой связи. Попробуй еще раз.")
