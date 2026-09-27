import os
import glob
import time
import streamlit as st
from view_mapping import render_mapping_page
from view_dashboard import render_dashboard_page

st.set_page_config(page_title="SmartBuild AI | ГЭСН", layout="wide", initial_sidebar_state="expanded")

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
    st.title("🏗️ SmartBuild AI")
    st.markdown("---")
    
    # Навигация
    page = st.radio(
        "Навигация:", 
        ["1. Маппинг по ГЭСН", "2. Дашборд Мониторинга"], 
        key="current_page"
    )
    
    st.markdown("---")
    st.info("💡 Алгоритмы ИИ привязываются автоматически на основе выбранного кода ГЭСН.")
    st.markdown("---")
    
    # Элементы управления режимом презентации
    st.subheader("⚙️ Режим презентации")
    live_update = st.checkbox("🔴 Включить Live-обновление (каждые 3 сек)")
    
    # Кнопка ручного сброса
    if st.button("🗑️ Сбросить все кадры (Очистить демо)", use_container_width=True):
        clear_demo_folders() # Вызываем нашу умную функцию
        st.session_state.active_media = None
        st.success("Кадры удалены! Запустите edge_simulator.py заново.")
        time.sleep(2)
        st.rerun()

if live_update:
    time.sleep(3)
    st.rerun()

# --- Маршрутизация (Роутер страниц) ---
if page == "1. Маппинг по ГЭСН":
    render_mapping_page()
elif page == "2. Дашборд Мониторинга":
    render_dashboard_page()