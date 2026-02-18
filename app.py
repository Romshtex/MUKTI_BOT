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

# ==========================================
# 1. ЛЕНДИНГ И ВХОД
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<br><h1>MUKTI</h1>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center; color:#00E676; margin-bottom:30px; letter-spacing:1px;'>Твой персональный ИИ-ассистент для выхода из зависимости</div>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="glass-container">
        <ul>
            <li><b>💠 Интеллект</b><br>Не просто трекер, а диалог с понимающим ассистентом и наставником 24/7</li>
            <li><b>🛡 Защита</b><br>Кнопка SOS и нейро-техники сброса тяги: от "ледяного шока" до перепрошивки триггеров</li>
            <li><b>🧠 Философия</b><br>Основано на методике разделения Личности и "Паразита". Ты — это не твой мозг</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["ВХОД В СИСТЕМУ", "СОЗДАТЬ АККАУНТ"])
    
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
        if st.button("ЗАРЕГИСТРИРОВАТЬСЯ", use_container_width=True):
            if db.register_user(ru, rp) == "OK":
                st.success("Готово! Входим...")
                time.sleep(1)
                udata, row = db.load_user(ru)
                st.session_state.logged_in = True
                st.session_state.username = ru
                st.session_state.row_num = row
                st.session_state.streak = 0
                st.session_state.last_active = str(date.today())
                st.session_state.reg_date = str(date.today())
                st.session_state.vip = False
                st.session_state.user_profile = {}
                
                # Приветствие в чате
                welcome = "Профиль создан. Добро пожаловать.\nТвой первый шаг — нажми кнопку **'✨ СЕГОДНЯ ЧИСТ'** вверху, чтобы активировать защиту."
                st.session_state.messages = [{"role": "assistant", "content": welcome}]
                db.save_history(row, st.session_state.messages)
                
                st.rerun()
            else: st.error("Имя занято.")

# ==========================================
# 2. ВНУТРИ СИСТЕМЫ
# ==========================================
else:
    # --- РАСЧЕТ ЛИМИТОВ (СРАЗУ ПРИ ЗАГРУЗКЕ) ---
    limit_total = settings.LIMIT_NEW_USER if st.session_state.streak < 3 else settings.LIMIT_OLD_USER
    msgs_used = sum(1 for m in st.session_state.messages if m["role"] == "user")
    
    # Если новый день - можно было бы сбрасывать, но мы считаем по истории
    # Упростим: берем последние сообщения за сегодня. 
    # (Для простоты пока считаем просто общее кол-во в текущей сессии/истории, как было)
    # Чтобы счетчик был красивым:
    energy_left = max(0, limit_total - msgs_used)
    
    # Проверка блокировки
    is_locked = (not st.session_state.vip) and (msgs_used >= limit_total)

    # --- ХЕДЕР С ЭНЕРГИЕЙ ---
    st.markdown(f"""
    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; font-family:Orbitron;'>
        <div style='font-size:18px;'>MUKTI <span style='color:#00E676; font-size:14px;'>// ONLINE</span></div>
        <div style='font-size:12px; color:#888;'>ЭНЕРГИЯ: <span style='color:{"#00E676" if energy_left > 0 else "#FF3D00"}'>{energy_left}/{limit_total}</span></div>
    </div>
    """, unsafe_allow_html=True)

    # --- ПЛАШКА БЛОКИРОВКИ (ЕСЛИ ЛИМИТ ИСЧЕРПАН) ---
    if is_locked:
        st.markdown(f"""
        <div class="limit-alert">
            <h3 style="color:#FF3D00; margin:0;">🔒 ЛИМИТ ИСЧЕРПАН</h3>
            <p style="color:#ccc; font-size:14px; margin-top:10px;">Энергия на сегодня закончилась.</p>
            <hr style="border-color:#550000;">
            <p style="margin-top:10px;">Чтобы снять ограничения:</p>
            <p>👉 <a href="https://t.me/Vybornov_Roman" target="_blank">НАПИСАТЬ РОМАНУ (MUKTI)</a></p>
            <p style="font-size:12px; color:#888;">Или введи код доступа ниже</p>
        </div>
        """, unsafe_allow_html=True)

    # --- ЭКРАН 1: SOS РЕЖИМ (ПОЛНЫЙ) ---
    if "sos_mode" not in st.session_state: st.session_state.sos_mode = False
    if st.session_state.sos_mode:
        if "sos_technique" not in st.session_state:
            techs = [
                {"name": "❄️ ЛЕДЯНОЙ СБРОС", "instr": "Включи ледяную воду. Подержи запястья под струей 30 секунд или умой лицо.", "why": "Это биологический рефлекс 'ныряльщика'. Организм переключается с режима 'Хочу дофамин' на режим 'Сохранение энергии'."},
                {"name": "⏪ ПЕРЕМОТКА ПЛЕНКИ", "instr": "Не думай о первом глотке. Представь завтрашнее утро. Головную боль. Стыд. Проиграй это кино до самого конца.", "why": "Тяга показывает только трейлер. Мы заставляем мозг посмотреть весь фильм ужасов."},
                {"name": "🗣 ИМЯ ВРАГА", "instr": "Скажи вслух: 'Это не я хочу выпить. Это Паразит умирает и просит еды. Я не буду его кормить'.", "why": "Разделяет 'Я' и 'Голос зависимости'."},
                {"name": "💨 ДЫХАНИЕ 'КВАДРАТ'", "instr": "Вдох (4 сек) — Пауза (4 сек) — Выдох (4 сек) — Пауза (4 сек). Повтори 5 циклов.", "why": "Выравнивает CO2 и физически гасит сигнал тревоги в мозге."}
            ]
            st.session_state.sos_technique = random.choice(techs)
        
        t = st.session_state.sos_technique
        st.markdown(f"""
        <div style='border:1px solid #FF3D00; padding:25px; border-radius:20px; background:rgba(40,0,0,0.9); text-align:center; margin-bottom:20px;'>
            <h2 style='color:#FF3D00; margin-bottom:20px;'>{t['name']}</h2>
            <div style='text-align:left; margin-bottom:15px;'>
                <p style='color:#fff;'><b>⚡️ ИНСТРУКЦИЯ:</b><br>{t['instr']}</p>
            </div>
            <div style='text-align:left; background:rgba(0,0,0,0.3); padding:10px; border-radius:10px;'>
                <p style='color:#888; font-size:13px; margin:0;'>💡 <b>Почему это работает:</b> {t['why']}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Я ВЕРНУЛ КОНТРОЛЬ", use_container_width=True):
            st.session_state.sos_mode = False
            del st.session_state.sos_technique
            st.rerun()
        st.stop()

    # --- ЭКРАН 2: ДАШБОРД ---
    st.markdown("<div class='glass-container'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    
    with c1:
        st.markdown(f"<div style='text-align:center; font-size:30px; font-weight:bold; font-family:Orbitron;'>{st.session_state.streak}</div>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:center; font-size:10px; color:#888;'>ДНЕЙ</div>", unsafe_allow_html=True)
    
    with c2:
        today = date.today()
        try: last = datetime.strptime(str(st.session_state.last_active), "%Y-%m-%d").date()
        except: last = today
        delta = (today - last).days
        
        if delta == 0 and st.session_state.streak > 0:
            st.button("✅ ЗАЧТЕНО", disabled=True, use_container_width=True)
        else:
            if st.button("✨ СЕГОДНЯ ЧИСТ", use_container_width=True):
                new_streak = 1 if delta > 1 and st.session_state.streak > 0 else st.session_state.streak + 1
                db.update_field(st.session_state.row_num, 3, new_streak)
                db.update_field(st.session_state.row_num, 4, str(today))
                st.session_state.streak = new_streak
                st.session_state.last_active = str(today)
                
                # --- ЛОГИКА КАЛИБРОВКИ (ЖИВОЙ ДИАЛОГ) ---
                # 1. Сначала проверка книги (если еще не спрашивали)
                if 'read_book' not in st.session_state.user_profile:
                    st.session_state.calibration_step = 1
                    msg = "День зачтен. Но прежде чем мы продолжим... Скажи, **ты уже читал книгу 'Кто такой Алкоголь'?**"
                
                # 2. Если книгу уже обсуждали, но профиль не полон - продолжаем вопросы
                elif 'frequency' not in st.session_state.user_profile:
                    st.session_state.calibration_step = 2
                    msg = "Отлично. Теперь давай настроим защиту. Скажи честно, **как часто Паразит обычно перехватывает управление?** (Каждый день, только по пятницам или бывают запои?)"
                
                # 3. Обычный режим
                else:
                    msg = "Данные обновлены. Как твое состояние сегодня? Паразит не беспокоил?"
                
                st.session_state.messages.append({"role": "assistant", "content": msg})
                db.save_history(st.session_state.row_num, st.session_state.messages)
                st.rerun()

    with c3:
        if st.button("🚨 SOS", use_container_width=True):
            st.session_state.sos_mode = True
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # --- ЧАТ ---
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    # --- ВВОД (ЛОГИКА) ---
    if is_locked:
        # Ввод кода при блокировке
        code_input = st.text_input("Введи Код Доступа:", key="vip_in")
        if st.button("АКТИВИРОВАТЬ", use_container_width=True):
            if code_input == VIP_CODE:
                db.update_field(st.session_state.row_num, 8, "TRUE")
                st.session_state.vip = True
                st.success("VIP активирован! Энергия восстановлена.")
                time.sleep(1)
                st.rerun()
            else: st.error("Неверный код")
    else:
        # Обычный чат
        if prompt := st.chat_input("Напиши сюда..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)

            # КАЛИБРОВКА (ВОПРОСЫ)
            step = st.session_state.calibration_step
            if step > 0:
                resp = ""
                # Шаг 1: Книга
                if step == 1:
                    db.update_profile(st.session_state.row_num, "read_book", prompt)
                    # Если ответ "нет" - предлагаем ссылку
                    if "нет" in prompt.lower():
                        resp = "Понял. Очень рекомендую прочитать, это усилит твою защиту на 80%. [Скачать можно тут](https://www.litres.ru/book/roman-vybornov/pochemu-ya-nikogo-ne-em-72075331/).\n\nА пока идем дальше. **Как часто Паразит обычно атакует?** (Каждый день, выходные, запои?)"
                    else:
                        resp = "Принято. Идем дальше. **Как часто Паразит обычно атакует?** (Каждый день, выходные, запои?)"
                    st.session_state.calibration_step = 2
                
                # Шаг 2: Частота -> Триггеры
                elif step == 2:
                    db.update_profile(st.session_state.row_num, "frequency", prompt)
                    resp = "Записал. **В какие именно моменты его голос звучит громче всего?** (Когда стресс на работе, когда скучно дома или в компании друзей?)"
                    st.session_state.calibration_step = 3
                
                # Шаг 3: Триггеры -> Опыт
                elif step == 3:
                    db.update_profile(st.session_state.row_num, "triggers", prompt)
                    resp = "Ясно. **Какой у тебя опыт сопротивления?** (Ты пробуешь бросить первый раз или уже были попытки и срывы?)"
                    st.session_state.calibration_step = 4
                
                # Шаг 4: Опыт -> Состояние
                elif step == 4:
                    db.update_profile(st.session_state.row_num, "history", prompt)
                    resp = "И последнее, но важное. **Что ты чувствуешь прямо сейчас?** (Тревогу, уверенность, вину или пустоту?)"
                    st.session_state.calibration_step = 5
                
                # Шаг 5: Финал -> Цель
                elif step == 5:
                    db.update_profile(st.session_state.row_num, "state", prompt)
                    st.session_state.user_profile = db.get_profile(st.session_state.row_num)
                    resp = "Профиль Врага оцифрован. Я настроил алгоритмы защиты.\n\nТеперь закрепим намерение. **Ради какой Большой Цели ты решил освободиться?** Что алкоголь у тебя крадет?"
                    st.session_state.calibration_step = 0
                
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

    if st.sidebar.button("ВЫХОД"):
        st.session_state.logged_in = False
        st.rerun()
