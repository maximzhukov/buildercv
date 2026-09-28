import json
import os
import streamlit as st
import pandas as pd
from datetime import timedelta
from nlp_mapper import predict_ai_strategy

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "cv_state.json")


def save_stage_strategies(plan_df):
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as state_file:
            state = json.load(state_file)
    except (OSError, json.JSONDecodeError):
        state = {}

    state["stage_strategies"] = dict(
        zip(plan_df["Наименование работ"], plan_df["Назначенная AI-Стратегия"])
    )
    state["stage_volumes"] = dict(zip(plan_df["Наименование работ"], plan_df["Объем"]))
    with open(STATE_FILE, "w", encoding="utf-8") as state_file:
        json.dump(state, state_file, ensure_ascii=False, indent=2)

def parse_plan_csv(file_or_path, shift_to_today=True):
    print(f"[Parser] Обработка файла: {file_or_path}, shift_to_today={shift_to_today}")
    try:
        df = pd.read_csv(file_or_path, sep=";", encoding="utf-8-sig")
    except Exception:
        if hasattr(file_or_path, 'seek'):
            file_or_path.seek(0)
        df = pd.read_csv(file_or_path, sep=",", encoding="utf-8-sig")
        
    df.columns = [str(c).strip() for c in df.columns]

    start_col = next((c for c in df.columns if "начало" in c.lower()), None)
    end_col = next((c for c in df.columns if "окончан" in c.lower()), None)
    name_col = next((c for c in df.columns if "вид работ" in c.lower() or "наименование" in c.lower()), df.columns[0])
    vol_col = next((c for c in df.columns if "объем" in c.lower()), None)

    if not start_col or not end_col:
        raise ValueError("В файле не найдены колонки с датами начала и окончания работ.")

    df = df.dropna(subset=[start_col, end_col]).copy()
    
    df["Наименование работ"] = df[name_col].astype(str).str.strip()
    df["Объем"] = df[vol_col].astype(str) if vol_col else "-"

    df["Начало"] = pd.to_datetime(df[start_col].astype(str).str.strip(), format="%d.%m.%Y", errors="coerce")
    df["Окончание"] = pd.to_datetime(df[end_col].astype(str).str.strip(), format="%d.%m.%Y", errors="coerce")
    df = df.dropna(subset=["Начало", "Окончание"]).copy()

    if shift_to_today:
        today = pd.Timestamp.today().normalize()
        target_mask = df["Наименование работ"].str.contains("котлован", case=False, na=False)
        
        if target_mask.any():
            target_start = df.loc[target_mask, "Начало"].iloc[0]
            shift_days = today - (target_start + timedelta(days=2))
            df["Начало"] = df["Начало"] + shift_days
            df["Окончание"] = df["Окончание"] + shift_days

    df["Начало"] = df["Начало"].dt.strftime("%Y-%m-%d")
    df["Окончание"] = df["Окончание"].dt.strftime("%Y-%m-%d")

    # === AI ПОД КАПОТОМ ===
    # Нейросеть невидимо для пользователя прогоняет каждую строку 
    # и назначает алгоритмы компьютерного зрения
    df["Назначенная AI-Стратегия"] = df["Наименование работ"].apply(predict_ai_strategy)
    
    return df[["Наименование работ", "Начало", "Окончание", "Объем", "Назначенная AI-Стратегия"]].reset_index(drop=True)


def render_mapping_page():

    file_id = "local_plan"
    demo_shift = False
    current_config = f"{file_id}_{demo_shift}"
    uploaded_file = None
    if st.session_state.get("last_config") != current_config:
        df = None
        if uploaded_file is not None:
            try:
                df = parse_plan_csv(uploaded_file, shift_to_today=demo_shift)
                st.success("Пользовательский файл успешно обработан ИИ.")
            except Exception as e:
                st.error(f"Ошибка обработки: {e}")
                st.stop()
        else:
            search_paths = ["plan.csv", "../plan.csv", "smartbuild_vps/plan.csv"]
            for path in search_paths:
                if os.path.exists(path):
                    print(f"[Parser] Найден файл: {path}, shift_to_today={demo_shift}")
                    df = parse_plan_csv(path, shift_to_today=demo_shift)
                    st.success("Загружен базовый план")
                    break
            
            if df is None:
                st.warning("Файл `plan.csv` не найден. Пожалуйста, загрузите CSV вручную.")
                st.stop()
                
        st.session_state.current_df = df
        st.session_state.last_config = current_config

    df = st.session_state.current_df
        
    st.subheader("📋 План производства работ")
    
    # Мы используем column_order, чтобы показать пользователю только чистую таблицу.
    # При этом колонка "Назначенная AI-Стратегия" сохраняется в памяти и будет передана на дашборд!
    st.dataframe(
        df,
        column_order=["Наименование работ", "Начало", "Окончание", "Объем"],
        hide_index=True,
        use_container_width=True
    )
    
    save_stage_strategies(df)
    st.session_state.plan_df = df