import os
import shutil

import time
import json
import requests
from datetime import date, datetime, time as datetime_time, timedelta
# --- НАСТРОЙКИ ПУТЕЙ ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMES_DIR = os.getenv(
    "SMARTBUILD_FRAMES_DIR",
    os.path.join(BASE_DIR, "edge_sim", "timelaps")
)
TARGET_URL = "http://127.0.0.1:8000/api/upload"  # Маршрут для тяжелой аналитики (Celery)

# --- НАСТРОЙКИ ВРЕМЕНИ ---
START_TIME = datetime_time(8, 0)
# FRAME_INTERVAL = timedelta(minutes=6)
FRAME_INTERVAL = timedelta(seconds=6)

def next_daily_start(now):
    start_today = now.replace(
        hour=START_TIME.hour,
        minute=START_TIME.minute,
        second=0,
        microsecond=0,
    )
    if now <= start_today:
        return start_today
    return start_today + timedelta(days=1)


def update_demo_states(simulation_date):
    cv_state_path = os.path.join(os.path.dirname(__file__), "../smartbuild_vps/cv_state.json")

    try:
        with open(cv_state_path, "r", encoding="utf-8") as f:
            cv_state = json.load(f)
    except Exception:
        cv_state = {}

    cv_state["unique_dump_trucks"] = 0
    cv_state["unique_mixers"] = 0
    cv_state.pop("lastday_states", None)
    demo_date = (simulation_date - timedelta(days=1)).strftime("%Y-%m-%d")
    demo_progress = {
        "Подготовительные работы и обустройство площадки": (100, 300.0),
        "Механизированная разработка и выемка грунта котлована": (13, 850.0),
        "Планировка дна котлована": (50, 1000.0),
        "Устройство щебеночного основания / подстилающего слоя под фундамент": (50, 150.0),
        "Укладка бетонной подготовки (подбетонки) толщиной ~100 мм": (50, 100.0),
        "Устройство горизонтальной рулонной гидроизоляции под фундаментную плиту": (30, 660.0),
    }
    remaining_stages = [
        "Монтаж арматурного каркаса фундаментной плиты (вязка сеток, установка поддерживающих каркасов)",
        "Устройство стен, колонн и пилонов подземного этажа",
        "Устройство плиты перекрытия подземного этажа (+0.000)",
        "Устройство монолитных ж/б колонн и пилонов 1-го и 2-го этажей",
        "Устройство монолитных ж/б плит перекрытия/покрытия надземных этажей (установка стоек, монтаж опалубки, армирование, бетонирование)",
        "Подача и распределение стеновых строительных блоков на готовых перекрытиях для последующего возведения стен",
        "Устройство наружных стен и ограждающих конструкций из мелкоштучных материалов (кирпич/блоки)",
        "Формирование оконных и дверных проемов",
        "Монтаж слоя теплоизоляции (утеплителя) на наружные стены",
        "Монтаж навесного вентилируемого фасада или устройство \"мокрого\" оштукатуренного фасада (светлая финишная отделка)",
        "Установка оконных блоков и балконных дверей",
    ]
    cv_state["history"] = {
        task: {demo_date: {"progress": progress, "fact_vol": fact_volume}}
        for task, (progress, fact_volume) in demo_progress.items()
    }

    task = "Механизированная разработка и выемка грунта котлована"
    day2 = (simulation_date - timedelta(days=2)).strftime("%Y-%m-%d")
    day3 = (simulation_date - timedelta(days=3)).strftime("%Y-%m-%d")
    day4 = (simulation_date - timedelta(days=4)).strftime("%Y-%m-%d")
    day5 = (simulation_date - timedelta(days=5)).strftime("%Y-%m-%d")
    day6 = (simulation_date - timedelta(days=6)).strftime("%Y-%m-%d")
    day7 = (simulation_date - timedelta(days=6)).strftime("%Y-%m-%d")
    # Присваиваем словари целиком, сразу создавая нужные ключи
    cv_state["history"][task][day2] = {"progress": 22, "fact_vol": 1100}
    cv_state["history"][task][day3] = {"progress": 20, "fact_vol": 700}
    cv_state["history"][task][day4] = {"progress": 22, "fact_vol": 925}
    cv_state["history"][task][day5] = {"progress": 22, "fact_vol": 1025}
    cv_state["history"][task][day6] = {"progress": 22, "fact_vol": 1025}
    cv_state["history"][task][day7] = {"progress": 22, "fact_vol": 1025}
    
    cv_state["history"].update({task: {} for task in remaining_stages})
    cv_state["progress"] = {
        task: progress for task, (progress, _) in demo_progress.items()
    }
    cv_state["progress"].update({task: 0 for task in remaining_stages})
    cv_state["completed_stages"] = ["Подготовительные работы и обустройство площадки"]
    cv_state["active_stages"] = ["Механизированная разработка и выемка грунта котлована"]

    with open(cv_state_path, "w", encoding="utf-8") as f:
        json.dump(cv_state, f, ensure_ascii=False, indent=2)
        f.write("\n")

    base_dir = os.path.join(os.path.dirname(__file__), "../smartbuild_vps/uploads")
    sub_dir = os.path.join(base_dir, "annotated")  

    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)

    os.makedirs(sub_dir, exist_ok=True)
    print("\n[Очистка] Состояние демо обновлено.")


def send_daily_images(images, simulation_date):
    current_virtual_time = datetime.combine(simulation_date, START_TIME)

    for index, img_name in enumerate(images):
        img_path = os.path.join(FRAMES_DIR, img_name)
        time_str = current_virtual_time.strftime("%Y-%m-%d %H:%M:%S")

        print(f"[{time_str}] Отправка кадра для аналитики ИИ: {img_name}...")

        try:
            with open(img_path, "rb") as image_file:
                new_filename = f"{current_virtual_time.strftime('%Y%m%d_%H_%M_%S')}_frame.jpg"
                files = {"file": (new_filename, image_file, "image/jpeg")}
                response = requests.post(TARGET_URL, files=files)

            if response.status_code == 200:
                print(f"  Успех: FastAPI принял кадр (ID: {response.json().get('frame_id')})")
            else:
                print(f"  Ошибка сервера: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("  Сервер FastAPI недоступен. Прерываю отправку до следующего дневного цикла.")
            return

        current_virtual_time += FRAME_INTERVAL
        if index < len(images) - 1:
            time.sleep(FRAME_INTERVAL.total_seconds())


def run_edge_ai_sender():
    if not os.path.exists(FRAMES_DIR):
        print(f"[!] Ошибка: Папка '{FRAMES_DIR}' не найдена.")
        return

    images = sorted([f for f in os.listdir(FRAMES_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    
    if not images:
        print(f"[!] Ошибка: В папке '{FRAMES_DIR}' нет картинок.")
        return

    print(f"Запуск Edge-узла. Найдено кадров: {len(images)}")
    print(f"Отправка на {TARGET_URL}: ежедневно с 08:00, интервал 6 минут.")

    cycle_number = 0
    while True:
        scheduled_start = next_daily_start(datetime.now())
        wait_seconds = 0
        # wait_seconds = max((scheduled_start - datetime.now()).total_seconds(), 0)
        if wait_seconds:
            print(f"Следующий цикл: {scheduled_start:%Y-%m-%d %H:%M:%S}")
            time.sleep(wait_seconds)

        simulation_date = datetime.now().date() + timedelta(days=cycle_number)
        update_demo_states(simulation_date)
        send_daily_images(images, simulation_date)
        print(f"Цикл симуляции за {simulation_date:%Y-%m-%d} завершён.")
        cycle_number += 1

if __name__ == "__main__":
    run_edge_ai_sender()