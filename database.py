import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date
import json

def get_db():
    creds_dict = None
    if "gcp_service_account" in st.secrets:
        raw = st.secrets["gcp_service_account"]
        if hasattr(raw, "to_dict"): creds_dict = raw.to_dict()
        elif isinstance(raw, dict): creds_dict = raw
        elif isinstance(raw, str):
            try: creds_dict = json.loads(raw)
            except: pass
            
    if not creds_dict and "private_key" in st.secrets:
        creds_dict = {k: st.secrets.get(k) for k in ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id", "auth_uri", "token_uri", "auth_provider_x509_cert_url", "client_x509_cert_url"]}

    if not creds_dict: return None

    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("MUKTI_DB").sheet1
    except: return None

# ИЩЕМ ПО EMAIL В 1-Й КОЛОНКЕ
def load_user(email):
    sheet = get_db()
    if not sheet: return None, None
    try:
        # Ищем строго в первой колонке (Email)
        cell = sheet.find(email, in_column=1)
        if cell: return sheet.row_values(cell.row), cell.row
    except: pass
    return None, None

# РЕГИСТРИРУЕМ С EMAIL
def register_user(email, username, password):
    sheet = get_db()
    if not sheet: return "ERROR"
    try:
        if sheet.find(email, in_column=1): return "TAKEN"
    except: pass
    
    today = str(date.today())
    # Исходный профиль с нулевым прогрессом посланий
    initial_profile = json.dumps({
        "msg_day": 0,
        "last_msg_date": ""
    }, ensure_ascii=False)
    
    # Структура: [Email, Имя, Пароль, Сообщения, Дата, Профиль, История, VIP]
    row = [email, username, password, 0, today, initial_profile, "[]", "FALSE"]
    sheet.append_row(row)
    return "OK"

def update_field(row_num, col_num, value):
    sheet = get_db()
    if sheet: sheet.update_cell(row_num, col_num, value)

def save_history(row_num, messages, depth=30):
    try:
        history_str = json.dumps(messages[-depth:], ensure_ascii=False) 
        update_field(row_num, 7, history_str)
    except: pass

def update_profile(row_num, key, value):
    sheet = get_db()
    if sheet:
        try:
            current_json = sheet.cell(row_num, 6).value
            data = json.loads(current_json) if current_json else {}
            data[key] = value
            sheet.update_cell(row_num, 6, json.dumps(data, ensure_ascii=False))
        except: pass

# --- ИСПРАВЛЕННАЯ ФУНКЦИЯ ДЛЯ ПАНЕЛИ АРХИТЕКТОРА (ПОД GOOGLE SHEETS) ---
def get_all_users():
    sheet = get_db()
    if not sheet: return []
    try:
        # Получаем все данные из таблицы разом (чтобы не перегружать API Google)
        records = sheet.get_all_values()
        users = []
        
        # Перебираем строки. idx - это индекс в списке (начинается с 0), 
        # поэтому номер строки в Google Sheets будет idx + 1
        for idx, row in enumerate(records):
            if not row or len(row) < 6: continue 
            
            # Пропускаем строку с заголовками, если она есть
            if row[0].lower() == "email": continue
            
            r_num = idx + 1
            u_email = row[0]
            u_name = row[1]
            p_json = row[5] # Профиль в формате JSON находится в 6-й колонке (индекс 5)
            
            # Добавляем данные в список в формате: (номер_строки, email, имя, json_профиля)
            users.append((r_num, u_email, u_name, p_json))
            
        return users
    except Exception as e:
        print(f"Ошибка выгрузки базы: {e}")
        return []
