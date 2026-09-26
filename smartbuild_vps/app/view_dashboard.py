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
    st.header("📊 Оперативный контроль площадки")
    
    if st.session_state.plan_df is None:
        st.warning("Сначала классифицируйте план по ГЭСН на первой вкладке.")
        st.stop()
        
    # --- БЛОК 1: KPI МЕТРИКИ ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Статус проекта", "В графике", "0 дней")
    col2.metric("Свайные работы", "112 шт", "56% от плана")
    col3.metric("Техника на объекте", "15 ед.", "В норме", delta_color="normal")
    col4.metric("Опасные зоны (СИЗ)", "1 нарушение", "За сегодня", delta_color="inverse")
    st.markdown("---")
    
    # --- БЛОК 2: ДИАГРАММА ГАНТА ---
    st.subheader("📉 График СМР (План vs Факт ИИ)")
    gantt_data = []
    for index, row in st.session_state.plan_df.iterrows():
        task = row["Наименование работ (из файла)"]
        start = row["Начало"]
        end = row["Окончание"]
        strategy = row["Назначенная AI-Стратегия"]
        
        gantt_data.append(dict(Task=task, Start=start, Finish=end, Тип="Бумажный План (CSV)"))
        if strategy != "Не отслеживать":
            fact_start = (pd.to_datetime(start) + timedelta(days=1)).strftime("%Y-%m-%d")
            fact_end = (pd.to_datetime(end) + timedelta(days=3)).strftime("%Y-%m-%d")
            gantt_data.append(dict(Task=task, Start=fact_start, Finish=fact_end, Тип="Фактическое выполнение (ИИ)"))

    df_gantt = pd.DataFrame(gantt_data)
    fig = px.timeline(
        df_gantt, x_start="Start", x_end="Finish", y="Task", color="Тип",
        color_discrete_map={"Бумажный План (CSV)": "#d3d3d3", "Фактическое выполнение (ИИ)": "#00CC96"}
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=350, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, width='stretch')
    
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
