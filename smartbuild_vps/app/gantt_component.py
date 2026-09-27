import pandas as pd
from datetime import timedelta
import streamlit.components.v1 as components
import json
import os

def render_custom_gantt(plan_df, height=480):
    df = plan_df.copy()
    df['Начало_dt'] = pd.to_datetime(df['Начало'])
    df['Окончание_dt'] = pd.to_datetime(df['Окончание'])
    
    # 1. ЗАГРУЗКА ДЕМО-ПРОГРЕССА ИЗ JSON
    config_path = os.path.join(os.path.dirname(__file__), "demo_config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            demo_progress = json.load(f)
    except Exception:
        demo_progress = {} # Фолбэк, если файл не найден

    # --- ВЫЧИСЛЕНИЕ ГРАНИЦ ТАЙМЛАЙНА ---
    min_date = df['Начало_dt'].min() - timedelta(days=3)
    max_date = df['Окончание_dt'].max() + timedelta(days=14)
    date_range = pd.date_range(start=min_date, end=max_date)
    total_days = len(date_range)
    
    today = pd.Timestamp.today().normalize()
    today_pos = (today - min_date).days + 0.5 
    
    # --- ГЕНЕРАЦИЯ ШАПКИ КАЛЕНДАРЯ ---
    ru_months = {1: 'Янв', 2: 'Фев', 3: 'Мар', 4: 'Апр', 5: 'Май', 6: 'Июн',
                 7: 'Июл', 8: 'Авг', 9: 'Сен', 10: 'Окт', 11: 'Ноя', 12: 'Дек'}
    
    months_html, days_html, month_lines_html = "", "", ""
    current_month = None
    days_in_month = 0
    month_start_offset = 0
    
    for i, d in enumerate(date_range):
        m_name = f"{ru_months[d.month]} {d.year}"
        if current_month != m_name:
            if current_month is not None:
                months_html += f'<div class="month-cell" style="--days: {days_in_month};">{current_month}</div>'
                month_lines_html += f'<div class="month-line" style="left: calc(var(--day-w) * {month_start_offset});"></div>'
            current_month = m_name
            days_in_month = 1
            month_start_offset = i
        else:
            days_in_month += 1
            
        is_weekend = " weekend" if d.weekday() >= 5 else ""
        days_html += f'<div class="day-cell{is_weekend}">{d.day:02d}</div>'
        
    if current_month is not None:
        months_html += f'<div class="month-cell" style="--days: {days_in_month};">{current_month}</div>'
        month_lines_html += f'<div class="month-line" style="left: calc(var(--day-w) * {month_start_offset});"></div>'

    # --- ГЕНЕРАЦИЯ СТРОК И ЛОГИКА ОТСТАВАНИЙ ---
    left_rows_html, right_rows_html = "", ""
    
    for idx, row in df.iterrows():
        name = str(row["Наименование работ (из файла)"]).strip()
        start_dt = row['Начало_dt']
        end_dt = row['Окончание_dt']
        
        # 2. ПОЛУЧАЕМ ПРОГРЕСС ИЗ СЛОВАРЯ (По умолчанию 0%)
        progress = demo_progress.get(name, 0)
            
        offset_days = (start_dt - min_date).days
        duration_days = (end_dt - start_dt).days + 1
        task_end_pos = offset_days + duration_days
        
        left_px = f"calc(var(--day-w) * {offset_days})"
        width_px = f"calc(var(--day-w) * {duration_days})"
        
        is_delayed = False
        delay_html = ""
        
        if end_dt < today and progress < 100:
            is_delayed = True
            delay_width = today_pos - task_end_pos
            if delay_width > 0:
                delay_left_px = f"calc(var(--day-w) * {task_end_pos})"
                delay_width_px = f"calc(var(--day-w) * {delay_width})"
                delay_html = f'<div class="delay-bar" style="left: {delay_left_px}; width: {delay_width_px};" title="Отставание от графика"></div>'
        
        if is_delayed: prog_color = '#EF4444'
        elif progress == 100: prog_color = '#16A34A'
        elif progress > 0: prog_color = '#2563EB'
        else: prog_color = '#94A3B8'

        left_rows_html += f"""
        <div class="left-row">
            <div class="cell-name" title="{name}">{name}</div>
            <div class="cell-prog" style="color: {prog_color};">{progress}%</div>
        </div>
        """
        
        tooltip = f"{name}&#10;Начало: {start_dt.strftime('%d.%m.%Y')}&#10;Конец: {end_dt.strftime('%d.%m.%Y')}&#10;Факт: {progress}%"
        right_rows_html += f"""
        <div class="right-row">
            <div class="bar-bg" style="left: {left_px}; width: {width_px};" title="{tooltip}">
                <div class="bar-fill" style="width: {progress}%;"></div>
            </div>
            {delay_html}
        </div>
        """
        
    today_html = ""
    if min_date <= today <= max_date:
        today_html = f'<div class="today-line" style="left: calc(var(--day-w) * {today_pos});" title="Текущий день"></div>'

    # --- HTML И CSS (Без изменений) ---
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            :root {{ --row-h: 42px; --left-w: 320px; --head-h: 56px; --border: #E2E8F0; --bg-even: #F8FAFC; --bar-bg: #E0E7FF; --bar-fill: #2563EB; --total-days: {total_days}; }}
            .zoom-day {{ --day-w: 38px; }} .zoom-week {{ --day-w: 12px; }} .zoom-month {{ --day-w: 3px; }}
            * {{ box-sizing: border-box; }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 0; background: #FFF; overflow: hidden; }}
            .controls {{ display: flex; gap: 8px; margin-bottom: 12px; height: 28px; }}
            .btn-view {{ background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 6px; padding: 4px 12px; font-size: 12px; font-weight: 500; color: #475569; cursor: pointer; transition: all 0.15s ease; }}
            .btn-view:hover {{ background: #F1F5F9; }} .btn-view.active {{ background: #2563EB; color: #FFF; border-color: #2563EB; }}
            .gantt-wrapper {{ display: flex; width: 100%; height: calc(100vh - 40px); border: 1px solid var(--border); border-radius: 8px; background: #FFF; }}
            .left-panel {{ width: var(--left-w); flex-shrink: 0; display: flex; flex-direction: column; border-right: 1px solid var(--border); background: #FFF; z-index: 30; }}
            .left-header {{ height: var(--head-h); flex-shrink: 0; display: flex; align-items: flex-end; padding: 10px 16px; background: var(--bg-even); border-bottom: 1px solid var(--border); font-size: 13px; font-weight: 600; color: #64748B; }}
            .left-body {{ flex-grow: 1; overflow-y: hidden; }}
            .left-row {{ height: var(--row-h); display: flex; align-items: center; padding: 0 16px; font-size: 13px; color: #1E293B; border-bottom: 1px solid transparent; }}
            .left-row:nth-child(even) {{ background: var(--bg-even); }}
            .cell-name {{ flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-right: 12px; font-weight: 500; }}
            .cell-prog {{ width: 48px; text-align: right; font-weight: 600; font-variant-numeric: tabular-nums; }}
            .right-panel {{ flex-grow: 1; overflow: auto; position: relative; }}
            .timeline-canvas {{ width: calc(var(--day-w) * var(--total-days)); min-width: 100%; display: flex; flex-direction: column; min-height: 100%; }}
            .right-header {{ height: var(--head-h); flex-shrink: 0; position: sticky; top: 0; background: #FFF; z-index: 20; border-bottom: 1px solid var(--border); display: flex; flex-direction: column; overflow: hidden; }}
            .months-row {{ display: flex; height: 30px; background: var(--bg-even); }}
            .month-cell {{ width: calc(var(--day-w) * var(--days)); border-right: 1px solid var(--border); display: flex; align-items: center; padding-left: 12px; font-size: 12px; font-weight: 600; color: #64748B; white-space: nowrap; overflow: hidden; }}
            .days-row {{ display: flex; height: 26px; }}
            .day-cell {{ width: var(--day-w); flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-size: 11px; color: #94A3B8; border-right: 1px solid #F1F5F9; overflow: hidden; transition: color 0.2s; }}
            .day-cell.weekend {{ background: rgba(226, 232, 240, 0.3); }}
            .zoom-week .day-cell {{ color: transparent; }} .zoom-month .days-row {{ display: none; }} .zoom-month .right-header {{ height: 30px; }}
            .right-body {{ position: relative; flex-grow: 1; background-image: linear-gradient(to right, #F1F5F9 1px, transparent 1px); background-size: var(--day-w) 100%; }}
            .zoom-week .right-body {{ background-size: calc(var(--day-w) * 7) 100%; }} .zoom-month .right-body {{ background-image: none; }}
            .right-row {{ height: var(--row-h); position: relative; border-bottom: 1px solid transparent; }}
            .right-row:nth-child(even) {{ background: rgba(248, 250, 252, 0.7); }}
            .month-line {{ position: absolute; top: 0; bottom: 0; width: 1px; background: #E2E8F0; z-index: 1; pointer-events: none; }}
            .bar-bg {{ position: absolute; top: 8px; height: 26px; background: var(--bar-bg); border-radius: 4px; display: flex; align-items: center; overflow: hidden; z-index: 10; transition: left 0.3s ease, width 0.3s ease; }}
            .bar-bg:hover {{ filter: brightness(0.95); cursor: pointer; }}
            .bar-fill {{ height: 100%; background: var(--bar-fill); border-radius: 4px; }}
            .delay-bar {{ position: absolute; top: 17px; height: 8px; background: #EF4444; border-radius: 0 4px 4px 0; z-index: 5; transition: left 0.3s ease, width 0.3s ease; }}
            .today-line {{ position: absolute; top: 0; bottom: 0; width: 2px; border-left: 2px dashed #3B82F6; z-index: 15; pointer-events: none; transition: left 0.3s ease; }}
        </style>
    </head>
    <body>
        <div class="controls">
            <button class="btn-view" id="btn-day" onclick="setZoom('day')">День</button>
            <button class="btn-view active" id="btn-week" onclick="setZoom('week')">Неделя</button>
            <button class="btn-view" id="btn-month" onclick="setZoom('month')">Месяц</button>
        </div>
        <div class="gantt-wrapper zoom-week" id="gantt-wrapper">
            <div class="left-panel">
                <div class="left-header"><div style="flex: 1;">Название этапа</div><div style="width: 48px; text-align: right;">Факт</div></div>
                <div class="left-body" id="left-body">{left_rows_html}</div>
            </div>
            <div class="right-panel" id="right-panel">
                <div class="timeline-canvas">
                    <div class="right-header"><div class="months-row">{months_html}</div><div class="days-row">{days_html}</div></div>
                    <div class="right-body">{month_lines_html}{today_html}{right_rows_html}</div>
                </div>
            </div>
        </div>
        <script>
            const rightPanel = document.getElementById('right-panel');
            const leftBody = document.getElementById('left-body');
            rightPanel.addEventListener('scroll', function() {{ leftBody.scrollTop = this.scrollTop; }});
            function setZoom(level) {{
                const wrapper = document.getElementById('gantt-wrapper');
                wrapper.className = 'gantt-wrapper zoom-' + level;
                document.querySelectorAll('.btn-view').forEach(btn => btn.classList.remove('active'));
                document.getElementById('btn-' + level).classList.add('active');
            }}
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=height, scrolling=False)

render_frappe_gantt = render_custom_gantt