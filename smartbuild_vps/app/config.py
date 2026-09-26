import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]


def _project_path(env_name, default):
    value = os.getenv(env_name)
    path = Path(value).expanduser() if value else Path(default)
    return str(path if path.is_absolute() else PROJECT_DIR / path)


ANNOTATED_DIR = str(PROJECT_DIR / "uploads" / "annotated")
TIMELAPSE_PATH = str(PROJECT_DIR / "uploads" / "timelapse.mp4")
LIVE_PATH = _project_path(
    "LIVE_PATH", PROJECT_DIR.parent / "edge_sim" / "live" / "camera.mp4"
)
if Path(LIVE_PATH).is_dir():
    LIVE_PATH = str(Path(LIVE_PATH) / "camera.mp4")
if not Path(LIVE_PATH).is_file():
    LIVE_PATH = str(PROJECT_DIR.parent / "edge_sim" / "live" / "camera.mp4")

# Мы жестко связываем государственные нормативы с алгоритмами компьютерного зрения.
GESN_TO_AI_STRATEGY = {
    "Выбрать норму...": "Не отслеживать",
    "ГЭСН 01: Земляные работы (Разработка котлованов)": "Подсчет самосвалов (Вывоз грунта)",
    "ГЭСН 05: Свайные работы (Устройство свай)": "Трекинг буровых/сваебоев",
    "ГЭСН 06: Бетонные и железобетонные монолитные конструкции": "Подсчет автобетоносмесителей",
    "ГЭСН 07: Бетонные и железобетонные сборные конструкции": "Анализ циклов башенного крана",
    "ГЭСН 09: Строительные металлические конструкции": "Анализ циклов башенного крана",
    "Иное / Внутренние работы": "Не отслеживать"
}