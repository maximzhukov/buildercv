import os
import time
import requests
from datetime import datetime, timedelta

# --- НАСТРОЙКИ ПУТЕЙ ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMES_DIR = os.getenv(
    "SMARTBUILD_FRAMES_DIR",
    os.path.join(BASE_DIR, "edge_sim", "timelaps")
)
TARGET_URL = "http://127.0.0.1:8000/api/upload"  # Маршрут для тяжелой аналитики (Celery)

# --- НАСТРОЙКИ ВРЕМЕНИ ---
START_TIME = datetime.strptime("08:00:00", "%H:%M:%S")
INTERVAL_MINUTES = 6      # Шаг виртуального времени (в БД будет 08:00, 08:06...)
REAL_DELAY_SEC = 5       # Для демо ждем 30 секунд. В продакшене тут будет 360 сек.

def run_edge_ai_sender():
    if not os.path.exists(FRAMES_DIR):
        print(f"[!] Ошибка: Папка '{FRAMES_DIR}' не найдена.")
        return

    images = sorted([f for f in os.listdir(FRAMES_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    
    if not images:
        print(f"[!] Ошибка: В папке '{FRAMES_DIR}' нет картинок.")
        return

    print(f"🚀 Запуск Edge-узла (AI Поток). Найдено кадров: {len(images)}")
    print(f"📡 Отправка на: {TARGET_URL} каждые {REAL_DELAY_SEC} сек.\n")
    
    current_virtual_time = START_TIME

    for img_name in images:
        img_path = os.path.join(FRAMES_DIR, img_name)
        time_str = current_virtual_time.strftime("%H:%M:%S")
        
        print(f"[{time_str}] 🧠 Отправка кадра для аналитики ИИ: {img_name}...")
        
        try:
            with open(img_path, 'rb') as f:
                new_filename = f"{current_virtual_time.strftime('%H_%M_%S')}_frame.jpg"
                files = {'file': (new_filename, f, 'image/jpeg')}
                
                # Инициируем PUSH-запрос на сервер
                response = requests.post(TARGET_URL, files=files)
                
                if response.status_code == 200:
                    print(f"  ✅ Успех: FastAPI принял кадр (ID: {response.json().get('frame_id')})")
                else:
                    print(f"  ❌ Ошибка сервера: {response.status_code}")
                    
        except requests.exceptions.ConnectionError:
            print("  [!] Сервер FastAPI недоступен. Убедитесь, что он запущен.")
            break
            
        current_virtual_time += timedelta(minutes=INTERVAL_MINUTES)
        
        # --- ВАЖНО: Задержка ---
        # Скрипт "засыпает". В реальной жизни в этот момент Edge-компьютер 
        # раздает WebRTC-видео всем желающим, но сеть не нагружает передачей картинок.
        time.sleep(REAL_DELAY_SEC)

    print("\n🏁 Все кадры отправлены.")

if __name__ == "__main__":
    # В будущем здесь можно запустить параллельный процесс WebRTC
    run_edge_ai_sender()