# view_dashboard.py
import os
import base64
import time
import json
import re
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta
from config import ANNOTATED_DIR, TIMELAPSE_PATH, LIVE_PATH
from media_utils import get_latest_frame, generate_timelapse
from gantt_component import render_custom_gantt
from progress_utils import cumulative_progress, parse_volume

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
    st.header("Сводка за текущий день")
    
    if st.session_state.plan_df is None:
        st.warning("Сначала классифицируйте план по ГЭСН на первой вкладке.")
        st.stop()

    cv_state_path = os.path.join(os.path.dirname(__file__), "..", "cv_state.json")
    try:
        with open(cv_state_path, "r", encoding="utf-8") as f:
            cv_state = json.load(f)
    except Exception:
        cv_state = {"active_stages": [], "progress": {}, "history": {}}

    active_stages = cv_state.get("active_stages", [])
    stage_strategies = cv_state.get("stage_strategies", {})
    history = cv_state.get("history", {})
    completed_stages = cv_state.get("completed_stages", [])
    plan_name_col = next(
        (column for column in st.session_state.plan_df.columns if "наименование" in column.lower()),
        st.session_state.plan_df.columns[0],
    )
    today = pd.Timestamp.today().normalize()
    today_key = today.strftime("%Y-%m-%d")

    # Анализ отставаний
    delays = []
    
    for idx, row in st.session_state.plan_df.iterrows():
        name = str(row[plan_name_col]).strip()
        end_dt = pd.to_datetime(row["Окончание"])
        
        task_history = history.get(name, {})
        prog = cumulative_progress(task_history, parse_volume(row.get("Объем", 0)))
        if name in completed_stages:
            prog = 100
            
        if end_dt < today and prog < 100:
            delay_days = (today - end_dt).days
            if delay_days > 0:
                delays.append({"name": name, "days": delay_days})

    project_status = "Частично отстает от графика" if delays else "В графике"

    active_strategy_keys = {
        re.sub(r"\s*\(YOLO11s\)\s*$", "", str(stage)).strip().casefold()
        for stage in active_stages
    }
    plan_volume_col = next(
        (column for column in st.session_state.plan_df.columns if "объем" in column.lower()),
        None,
    )
    
    activity_details = []
    if plan_volume_col:
        for _, row in st.session_state.plan_df.iterrows():
            task_name = str(row[plan_name_col]).strip()
            strategy = stage_strategies.get(task_name, "")
            normalized_strategy = re.sub(
                r"\s*\(YOLO11s\)\s*$", "", str(strategy)
            ).strip().casefold()
            if normalized_strategy not in active_strategy_keys:
                continue

            today_entry = history.get(task_name, {}).get(today_key, {})
            if float(today_entry.get("progress", 0)) == 0:
                continue

            total_volume = parse_volume(row[plan_volume_col])
            task_progress = cumulative_progress(history.get(task_name, {}), total_volume)
            today_volume = float(today_entry.get("fact_vol", 0))
            today_percent = min(today_volume / total_volume * 100, 100) if total_volume else 0

            activity_details.append({
                "name": task_name,
                "history": history.get(task_name, {}),
                "total_volume": total_volume,
                "cumulative_progress": task_progress,
                "today_percent": today_percent
            })

    # --- БЛОК 1: KPI МЕТРИКИ В ШАПКЕ ---
    num_cols = max(2, len(active_stages) + 1)
    cols = st.columns(num_cols)

    with cols[0]:
        st.metric(label="Статус проекта", value=project_status)

    st.markdown("---")

    # --- БЛОК 2: АКТИВНОСТИ (Сгруппированные блоки) ---
    if activity_details:
        st.info("Активные этапы:")
        st.markdown("<br>", unsafe_allow_html=True)
        
        for i, activity in enumerate(activity_details, 1):
            # Создаем смещение: 5% ширины на цифру, 95% на контент
            col_num, col_content = st.columns([0.05, 0.95])
            
            with col_num:
                st.markdown(f"### {i}.")
                
            with col_content:
                # 1. Таблица этапа
                st.dataframe(
                    pd.DataFrame([{
                        "Этап": activity["name"],
                        "Выполнено всего": f"{activity['cumulative_progress']}%",
                        "Объем за сегодня": f"{activity['today_percent']:.1f}%",
                    }]),
                    hide_index=True,
                    use_container_width=True,
                )
                
                # 2. График динамики
                task_history = activity["history"]
                history_dates = sorted(task_history)[-7:]
                
                if history_dates:
                    chart_data = pd.DataFrame({
                        "Дата": history_dates,
                        "Объем за день": [
                            float(task_history[history_date].get("fact_vol", 0))
                            for history_date in history_dates
                        ],
                    })
                    fig = px.line(
                        chart_data,
                        x="Дата",
                        y="Объем за день",
                        title=f"Динамика этапа за последние {len(history_dates)} дн.",
                        markers=True,
                    )
                    fig.update_traces(line_color="#FF9F1C", line_width=3)
                    fig.update_layout(
                        height=250,
                        margin=dict(l=0, r=0, t=40, b=0),
                        xaxis_title=None,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # 3. Прогноз
                    observed_volumes = chart_data["Объем за день"]
                    average_daily_volume = observed_volumes.mean()
                    remaining_volume = activity["total_volume"] * (
                        1 - activity["cumulative_progress"] / 100
                    )
                    if average_daily_volume > 0 and remaining_volume > 0:
                        days_left = remaining_volume / average_daily_volume
                        eta_date = today + pd.Timedelta(days=round(days_left))
                        eta_str = eta_date.strftime("%d.%m.%Y")
                        st.info(
                            f"**Прогноз:** При текущем темпе этап завершится "
                            f"**{eta_str}** (осталось ~{round(days_left)} дн.)"
                        )
                    elif activity["cumulative_progress"] >= 100:
                        st.success("Этап успешно завершен!")
                    else:
                        st.info("Недостаточно данных для прогноза")
                        
            st.markdown("<hr style='margin-top: 2rem; margin-bottom: 2rem; border-top: 1px dashed #ccc;'>", unsafe_allow_html=True)
    else:
        st.info("Сегодня не выявлено активных этапов")

    # Вывод деталей отставания
    if delays:
        st.error("Отставания:")
        df = pd.DataFrame([
            {"Название этапа": delay["name"], "Дни": delay["days"]}
            for delay in delays
        ])
        df["Дни"] = df["Дни"].astype(str)

        st.dataframe(df, hide_index=False, use_container_width=True)
        st.markdown("---")
        
    st.subheader("График")
    render_custom_gantt(st.session_state.plan_df, height=480)
    st.markdown("---")
    
    # --- БЛОК 3: ЛАЙВ АНАЛИТИКА ---
    st.subheader("Визуальный контроль")
    
    if "active_media" not in st.session_state or st.session_state.active_media is None:
        st.session_state.active_media = "live"

    col_media, col_controls = st.columns([3, 2])

    with col_media:
        if st.session_state.active_media == "timelapse":
            with st.spinner("Склеиваем кадры за сегодня..."):
                success = generate_timelapse(input_folder=ANNOTATED_DIR, output_file=TIMELAPSE_PATH)
                if success:
                    st.success("Таймлапс сгенерирован")
                    render_timelapse(TIMELAPSE_PATH)
                else:
                    st.error("Нет кадров для создания таймлапса.")

        elif st.session_state.active_media == "live":
            st.warning("Прямая трансляция")
            render_live_video(LIVE_PATH)

    with col_controls:
        is_timelapse_active = st.session_state.active_media == "timelapse"
        is_live_active = st.session_state.active_media == "live"

        if st.button(
            "Таймлапс с начала дня", 
            use_container_width=True, 
            type="primary" if is_timelapse_active else "secondary"
        ):
            st.session_state.active_media = "timelapse"
            st.rerun()
            
        if st.button(
            "Трансляция", 
            use_container_width=True, 
            type="primary" if is_live_active else "secondary"
        ):
            st.session_state.active_media = "live"
            st.rerun()