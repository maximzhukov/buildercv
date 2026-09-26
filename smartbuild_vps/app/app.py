# app.py
import time
import streamlit as st
from view_mapping import render_mapping_page
from view_dashboard import render_dashboard_page

st.set_page_config(page_title="SmartBuild AI | ГЭСН", layout="wide", initial_sidebar_state="expanded")

# --- Инициализация состояния сессии ---
if "plan_df" not in st.session_state:
    st.session_state.plan_df = None
if "active_media" not in st.session_state:
    st.session_state.active_media = None

# --- Боковое меню (Сайдбар) ---
with st.sidebar:
    st.title("🏗️ SmartBuild AI")
    st.markdown("---")
    
    # Навигация
    page = st.radio("Навигация:", ["1. Маппинг по ГЭСН", "2. Дашборд Мониторинга"])
    
    st.markdown("---")
    st.info("💡 Алгоритмы ИИ привязываются автоматически на основе выбранного кода ГЭСН.")
    st.markdown("---")
    
    # Элементы управления режимом презентации
    st.subheader("⚙️ Режим презентации")
    live_update = st.checkbox("🔴 Включить Live-обновление (каждые 3 сек)")

if live_update:
    time.sleep(3)
    st.rerun()

# --- Маршрутизация (Роутер страниц) ---
if page == "1. Маппинг по ГЭСН":
    render_mapping_page()
elif page == "2. Дашборд Мониторинга":
    render_dashboard_page()