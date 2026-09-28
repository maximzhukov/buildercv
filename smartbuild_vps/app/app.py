import os
import glob
import time
import streamlit as st
from view_mapping import render_mapping_page
from view_dashboard import render_dashboard_page

st.set_page_config(page_title="Smart CV building", layout="wide", initial_sidebar_state="expanded")

def clear_demo_folders():
    """Железобетонно находит папку uploads и очищает кадры"""
    # Вычисляем абсолютный путь к текущему скрипту
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Если мы находимся в папке app, поднимаемся на уровень выше
    if os.path.basename(current_dir) == "app":
        base_dir = os.path.dirname(current_dir)
    else:
        base_dir = current_dir
        
    raw_dir = os.path.join(base_dir, "uploads")
    annotated_dir = os.path.join(raw_dir, "annotated")
    
    print(f"\n[Очистка] Проверка директорий:\n - {raw_dir}\n - {annotated_dir}")
    
    # Удаляем файлы из обеих папок
    for target_dir in [annotated_dir, raw_dir]:
        if os.path.exists(target_dir):
            files = glob.glob(f"{target_dir}/*")
            for f in files:
                if os.path.isfile(f):
                    try:
                        os.remove(f)
                        print(f"  [-] Удален файл: {os.path.basename(f)}")
                    except Exception as e:
                        print(f"  [!] Ошибка удаления: {e}")

# --- АВТО-ОЧИСТКА ПАПОК ПРИ ЗАПУСКЕ ---
if "demo_initialized" not in st.session_state:
    st.session_state.demo_initialized = True
    # clear_demo_folders()
    # print("[Система] 🧹 Папки очищены. Готово к новой симуляции!\n")

# --- Инициализация состояния сессии ---
if "plan_df" not in st.session_state:
    st.session_state.plan_df = None
if "active_media" not in st.session_state:
    st.session_state.active_media = None

# --- Боковое меню (Сайдбар) ---
if st.session_state.get("redirect_to_dashboard"):
    st.session_state.current_page = "2. Дашборд Мониторинга"
    st.session_state.redirect_to_dashboard = False

# --- Боковое меню (Сайдбар) ---
with st.sidebar:
    st.title("Smart CV building")
    st.markdown("---")
    
    # Навигация
    page = st.radio(
        "Навигация:", 
        ["1. Конфигурация", "2. Мониторинг"], 
        key="current_page"
    )
    
# --- Маршрутизация (Роутер страниц) ---
if page == "1. Конфигурация":
    render_mapping_page()
elif page == "2. Мониторинг":
    render_dashboard_page()