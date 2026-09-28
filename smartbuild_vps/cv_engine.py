import json
import os
import re
import pandas as pd
from app.stage_registry import CONCRETE_STAGE, EARTHWORK_STAGE, GENERAL_STAGE, YOLO_STAGE_CLASSES
from app.progress_utils import cumulative_progress

STATE_FILE = os.path.join(os.path.dirname(__file__), "cv_state.json")

class BuilderCVEngine:
    def __init__(self):
        self.plan_df = self._load_plan()
        self.state = self._load_state()

    def _load_plan(self):
        search_paths = [os.path.join(os.path.dirname(__file__), "app", "plan.csv")]
        for path in search_paths:
            if os.path.exists(path):
                try:
                    return pd.read_csv(path, sep=";", encoding="utf-8-sig")
                except:
                    pass
        return None

    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    if "completed_stages" not in state: state["completed_stages"] = []
                    if "history" not in state: state["history"] = {}
                    if "stage_strategies" not in state: state["stage_strategies"] = {}
                    if "stage_volumes" not in state: state["stage_volumes"] = {}
                    state.pop("lastday_states", None)
                    return state
            except:
                pass
                
        return {
            "unique_dump_trucks": 0,
            "unique_mixers": 0,
            "progress": {},
            "completed_stages": [],
            "stage_strategies": {},
            "stage_volumes": {},
            "history": {},
        }

    def _extract_volume(self, task_name):
        volume_value = self.state.get("stage_volumes", {}).get(task_name)

        if volume_value is None and self.plan_df is not None:
            name_col = next(
                (column for column in self.plan_df.columns if "вид работ" in column.lower() or "наименование" in column.lower()),
                self.plan_df.columns[0],
            )
            volume_col = next(
                (column for column in self.plan_df.columns if "объем" in column.lower()),
                None,
            )
            if volume_col:
                matching_rows = self.plan_df[
                    self.plan_df[name_col].astype(str).str.strip() == task_name
                ]
                if not matching_rows.empty:
                    volume_value = matching_rows.iloc[0][volume_col]

        if volume_value is None or pd.isna(volume_value):
            raise ValueError(f"В CSV не задан объем для этапа: {task_name}")

        normalized_value = re.sub(r"\s+", "", str(volume_value)).replace(",", ".")
        match = re.search(r"[-+]?\d+(?:\.\d+)?", normalized_value)
        if not match or float(match.group()) <= 0:
            raise ValueError(f"Некорректный объем в CSV для этапа {task_name}: {volume_value}")

        return float(match.group())

    def _calculate_earthwork_progress(self, task_name, new_trucks, today_str):
        total_volume = self._extract_volume(task_name)
        existing_volume = self.state.get("history", {}).get(task_name, {}).get(
            today_str, {}
        ).get("fact_vol", 0)
        today_volume = existing_volume + new_trucks * 25
        daily_progress = min(int(today_volume / total_volume * 100), 100)
        return daily_progress, today_volume

    def _calculate_concrete_progress(self, task_name, new_mixers, today_str):
        total_volume = self._extract_volume(task_name)
        existing_volume = self.state.get("history", {}).get(task_name, {}).get(
            today_str, {}
        ).get("fact_vol", 0)
        today_volume = existing_volume + new_mixers * 9
        daily_progress = min(int(today_volume / total_volume * 100), 100)
        return daily_progress, today_volume

    def _define_active_stages(self, classes, stage_strategies, completed_stages):
        incomplete_strategies = {
            strategy
            for task_name, strategy in stage_strategies.items()
            if task_name not in completed_stages
        }
        active_stages = [
            stage
            for stage, stage_classes in YOLO_STAGE_CLASSES.items()
            if stage in incomplete_strategies and classes.intersection(stage_classes)
        ]
        if classes and GENERAL_STAGE in incomplete_strategies and not active_stages:
            active_stages.append(GENERAL_STAGE)
        return active_stages

    def process_classes(self, detected_classes, new_trucks=0, new_mixers=0):
        classes = set(detected_classes)
        today_str = pd.Timestamp.today().normalize().strftime('%Y-%m-%d')
        if self.state.get("counter_date") != today_str:
            self.state["unique_dump_trucks"] = 0
            self.state["unique_mixers"] = 0
            self.state["counter_date"] = today_str
        self.state["unique_dump_trucks"] += new_trucks
        self.state["unique_mixers"] += new_mixers

        try:
            with open(STATE_FILE, "r", encoding="utf-8") as state_file:
                persisted_state = json.load(state_file)
            self.state["stage_strategies"] = persisted_state.get("stage_strategies", {})
            self.state["stage_volumes"] = persisted_state.get("stage_volumes", {})
            self.state["history"] = persisted_state.get("history", {})
        except (OSError, json.JSONDecodeError):
            pass
        
        completed_stages = self.state.get("completed_stages", [])
        stage_strategies = self.state.get("stage_strategies", {})
        active_stages = self._define_active_stages(
            classes, stage_strategies, completed_stages
        )
                
        if not active_stages:
            self.state["current_classes"] = list(classes)
            self.state["active_stages"] = []
            self.state["progress"] = {
                task_name: 0 for task_name in stage_strategies
            }
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=4)
            return [], self.state.get("progress", {})

        final_progress = {task_name: 0 for task_name in stage_strategies}

        if self.plan_df is not None:
            name_col = next((c for c in self.plan_df.columns if "вид работ" in c.lower() or "наименование" in c.lower()), self.plan_df.columns[0])
            active_indices = [
                idx for idx, row in self.plan_df.iterrows()
                if stage_strategies.get(str(row[name_col]).strip()) in active_stages
            ]
            min_active = min(active_indices) if active_indices else -1
            max_active = max(active_indices) if active_indices else -1
            
            for idx, row in self.plan_df.iterrows():
                task_name = str(row[name_col]).strip()
                
                if task_name not in self.state.get("history", {}):
                    self.state["history"][task_name] = {}

                if task_name in completed_stages:
                    final_progress[task_name] = 100
                    continue
                if idx < min_active: 
                    # если индекс этапа меньше минимального активного то счиаем что он завершен
                    completed_stages.append(task_name)
                elif idx > max_active:
                    final_progress[task_name] = 0
                elif idx in active_indices:
                    # если этап находится в active_stages, то считаем что он в работе и прогресс расчитываем по объему
                    strategy = self.state.get("stage_strategies", {}).get(task_name)
                    if strategy == EARTHWORK_STAGE:
                        prog, fact_vol = self._calculate_earthwork_progress(
                            task_name, new_trucks, today_str
                        )
                    elif strategy == CONCRETE_STAGE:
                        prog, fact_vol = self._calculate_concrete_progress(
                            task_name, new_mixers, today_str
                        )
                    else:
                        prog, fact_vol = 0, 0
                        
                    final_progress[task_name] = prog
                    print(f"[AI Engine] Этап: {task_name}, Стратегия: {strategy}, Прогресс: {prog}%, Факт. объем: {fact_vol}")
                    self.state["history"][task_name][today_str] = {
                        "progress": prog,
                        "fact_vol": fact_vol
                    }
                    
                    if cumulative_progress(self.state["history"][task_name], self._extract_volume(task_name)) >= 100:
                        completed_stages.append(task_name)
                else:
                    final_progress[task_name] = 0
                    
        self.state["progress"] = final_progress
        self.state["active_stages"] = active_stages
        self.state["current_classes"] = list(classes)
        self.state["completed_stages"] = list(set(completed_stages))
        
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=4)
            
        return active_stages, final_progress