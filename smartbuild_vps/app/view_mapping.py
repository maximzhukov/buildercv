# view_mapping.py
import streamlit as st
import pandas as pd
from config import GESN_TO_AI_STRATEGY

def render_mapping_page():
    st.header("📂 Классификация плана СМР по ГЭСН")
    st.write("Сопоставьте этапы работ из вашего графика со стандартными кодами ГЭСН. Система автоматически подберет нужную модель компьютерного зрения.")
    
    # Генерация демо-данных "из CSV"
    df = pd.DataFrame({
        "Наименование работ (из файла)": [
            "Подготовка территории", 
            "Копка ямы под секцию 1", 
            "Вдавливание свай", 
            "Заливка фундаментной плиты",
            "Установка металлического забора"
        ],
        "Начало": ["2026-09-01", "2026-09-15", "2026-09-25", "2026-10-05", "2026-10-20"],
        "Окончание": ["2026-09-14", "2026-09-24", "2026-10-04", "2026-10-15", "2026-10-25"],
        "Объем": ["-", "5000 м3", "200 шт", "800 м3", "150 м"]
    })
        
    if "Код ГЭСН" not in df.columns:
        df["Код ГЭСН"] = "Выбрать норму..."
        
    st.subheader("🔗 Ручная привязка нормативов")
    
    edited_df = st.data_editor(
        df,
        column_config={
            "Код ГЭСН": st.column_config.SelectboxColumn(
                "Норматив ГЭСН",
                help="Выберите соответствующий раздел ГЭСН",
                options=list(GESN_TO_AI_STRATEGY.keys()),
                required=True,
            ),
            "Наименование работ (из файла)": st.column_config.Column(disabled=True),
            "Начало": st.column_config.Column(disabled=True),
            "Окончание": st.column_config.Column(disabled=True),
            "Объем": st.column_config.Column(disabled=True),
        },
        width='stretch',
        hide_index=True
    )
    
    edited_df["Назначенная AI-Стратегия"] = edited_df["Код ГЭСН"].map(GESN_TO_AI_STRATEGY)
    
    st.subheader("🤖 Результат авто-назначения алгоритмов")
    st.dataframe(
        edited_df[["Наименование работ (из файла)", "Код ГЭСН", "Назначенная AI-Стратегия"]],
        width='stretch',
        hide_index=True
    )
    
    if st.button("💾 Утвердить план и запустить ИИ", type="primary"):
        st.session_state.plan_df = edited_df
        st.success("Маппинг завершен! Алгоритмы настроены. Перейдите на вкладку 'Дашборд Мониторинга'.")
