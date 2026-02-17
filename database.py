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
    
    today = str(date.today())
    # Структура: User, Pin, Streak, LastActive, RegDate, ProfileJson, HistoryJson, VIP
    row = [username, pin, 0, today, today, "{}", "[]", "FALSE"]
    sheet.append_row(row)
    return "OK"

def update_field(row_num, col_num, value):
    sheet = get_db()
    if sheet: sheet.update_cell(row_num, col_num, value)

def save_history(row_num, messages, depth=30):
    try:
        history_str = json.dumps(messages[-depth:]) 
        update_field(row_num, 7, history_str)
    except: pass

def update_profile(row_num, key, value):
    sheet = get_db()
    if sheet:
        try:
            current_json = sheet.cell(row_num, 6).value
            data = json.loads(current_json) if current_json else {}
            data[key] = value
            sheet.update_cell(row_num, 6, json.dumps(data))
            return data
        except: return {}

def get_profile(row_num):
    sheet = get_db()
    if sheet:
        try:
            current_json = sheet.cell(row_num, 6).value
            return json.loads(current_json) if current_json else {}
        except: return {}
    return {}
