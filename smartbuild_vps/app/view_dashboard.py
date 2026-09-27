# view_dashboard.py
import os
import base64
import time
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta
from config import ANNOTATED_DIR, TIMELAPSE_PATH, LIVE_PATH
from media_utils import get_latest_frame, generate_timelapse
from gantt_component import render_custom_gantt

def render_timelapse(path):
    with open(path, "rb") as video_file:
        video_data = base64.b64encode(video_file.read()).decode("ascii")
    st.video(TIMELAPSE_PATH, autoplay=True, loop=True, muted=True)


def render_live_video(path):
    with open(path, "rb") as video_file:
        video_data = base64.b64encode(video_file.read()).decode("ascii")
    st.html(
        f'<video autoplay="autoplay" muted="muted" loop="loop" '
        f'playsinline preload="auto" style="width: 100%;" '
        f'src="data:video/mp4;base64,{video_data}"></video>'
    )


def render_dashboard_page():
    st.header("Сводка за сегодня")
    
    if st.session_state.plan_df is None:
        st.warning("Сначала классифицируйте план по ГЭСН на первой вкладке.")
        st.stop()
        
    # --- БЛОК 1: KPI МЕТРИКИ ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Статус проекта", "В графике", "0 дней")
    st.markdown("---")
    
    # --- БЛОК 2: ДИАГРАММА ГАНТА ---
    st.subheader("📉 График СМР (План vs Факт ИИ)")

    import json
    import os
    import pandas as pd

    # 1. Читаем демо-конфиг
    config_path = os.path.join(os.path.dirname(__file__), "demo_config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            demo_progress = json.load(f)
    except Exception:
        demo_progress = {}

    # 2. Анализируем отставания
    today = pd.Timestamp.today().normalize()
    has_delays = False

    for idx, row in st.session_state.plan_df.iterrows():
        end_dt = pd.to_datetime(row["Окончание"])
        name = str(row["Наименование работ (из файла)"]).strip()
        
        # Берем прогресс из JSON (или 0)
        progress = demo_progress.get(name, 0)
            
        if end_dt < today and progress < 100:
            has_delays = True
            break

    # 3. Выводим статус
    if has_delays:
        st.error("⚠️ **СТАТУС ПРОЕКТА:** Зафиксировано частичное отставание от графика производства работ.", icon="🚨")
    else:
        st.success("✅ **СТАТУС ПРОЕКТА:** Строительно-монтажные работы выполняются согласно графику.", icon="🏗️")

    render_custom_gantt(st.session_state.plan_df, height=480)
    st.markdown("---")
    
    # --- БЛОК 3: ЛАЙВ АНАЛИТИКА С ГРАФИКАМИ ДИНАМИКИ ---
    st.markdown("---")
    st.subheader("📷 Визуальный контроль: Камера 1 (Котлован)")
    col_media, col_controls = st.columns([3, 2])

    with col_media:
        if st.session_state.active_media is None:
            latest_img = get_latest_frame(ANNOTATED_DIR)
            print(f"[Dashboard] Последний кадр: {latest_img}, ANNOTATED_DIR={ANNOTATED_DIR}")
            if latest_img:
                mod_time = time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(latest_img)))
                st.image(latest_img, caption=f"🟢 Последний кадр (Обновлено в {mod_time})", width='stretch')
            else:
                st.info("Ожидание первых кадров от YOLO...", icon="⏳")

        elif st.session_state.active_media == "timelapse":
            with st.spinner("Склеиваем кадры за сегодня..."):
                success = generate_timelapse(input_folder=ANNOTATED_DIR, output_file=TIMELAPSE_PATH)
                if success:
                    st.success("✅ Таймлапс сгенерирован")
                    render_timelapse(TIMELAPSE_PATH)
                else:
                    st.error("Нет кадров для создания таймлапса.")
            if st.button("✖️ Закрыть таймлапс"):
                st.session_state.active_media = None
                st.rerun()

        elif st.session_state.active_media == "live":
            st.warning("🔴 Прямая трансляция (без обработки ИИ)")
            # Для MVP просто вставляем заглушку видео или тег HTML. 
            # В реальности здесь будет st.components.v1.iframe("http://ip_камеры/stream")
            render_live_video(LIVE_PATH)
            
            if st.button("✖️ Вернуться к AI-кадрам"):
                st.session_state.active_media = None
                st.rerun()

    with col_controls:
        st.markdown("**Инструменты просмотра:**")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("⏪ Таймлапс за день", width='stretch'):
                st.session_state.active_media = "timelapse"
                st.rerun()
        with col_btn2:
            if st.button("🔴 Live-видео", width='stretch'):
                st.session_state.active_media = "live"
                st.rerun()
                
        st.markdown("<br>", unsafe_allow_html=True)
        dates = pd.date_range(end=pd.Timestamp.today(), periods=5)
        df_soil = pd.DataFrame({"Дата": dates, "Вывезено (м³)": [400, 450, 480, 570, 120]})
        fig_soil = px.bar(
            df_soil, x="Дата", y="Вывезено (м³)", 
            title="Динамика вывоза грунта (ГЭСН 01)", text_auto=True
        )
        fig_soil.update_traces(marker_color='#FF9F1C')
        fig_soil.update_layout(height=280, margin=dict(l=0, r=0, t=40, b=0), xaxis_title=None)
        st.plotly_chart(fig_soil, width='stretch')
        
    st.markdown("---")
    st.subheader("🚨 Лог критических отклонений")
    st.error("**09:30 | Контроль Земли (Камера 1)** — Снижение темпа вывоза грунта. За час выехало 2 самосвала (Норма: 5).")
    st.warning("**11:15 | Трекинг буровых (Камера 2)** — Сваебойная установка ID:2 не активна более 45 минут.")
