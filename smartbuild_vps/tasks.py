import os
import cv2
from celery import Celery
from ultralytics import YOLO
from database import SessionLocal, FrameLog
from cv_engine import BuilderCVEngine  # <--- ПОДКЛЮЧАЕМ ДВИЖОК


# 1. Настройка брокера задач Celery
celery_app = Celery(
    "smartbuild_tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

# 2. Инициализация моделей
MODEL_PATH = os.getenv("SMARTBUILD_MODEL_PATH", "../model/best.pt")
print(f"[*] Загрузка AI-модели {MODEL_PATH} в память воркера...")
model = YOLO(MODEL_PATH)
class_names = model.names

# Инициализируем бизнес-логику один раз на уровне воркера
cv_logic_engine = BuilderCVEngine()

ROI_COORDS = None #[0, 420, 1920, 1080]
ANNOTATED_DIR = os.getenv("SMARTBUILD_ANNOTATED_DIR", "uploads/annotated")
os.makedirs(ANNOTATED_DIR, exist_ok=True)

@celery_app.task
def process_frame(frame_id: int, filepath: str):
    print(f"[AI Worker] Начало обработки кадра ID:{frame_id}")
    
    db = SessionLocal()
    frame_log = db.query(FrameLog).filter(FrameLog.id == frame_id).first()
    
    if not frame_log:
        print(f"[!] Кадр ID:{frame_id} не найден в БД!")
        db.close()
        return False

    try:
        results = model.predict(source=filepath, conf=0.2, device='mps', verbose=False)
        result = results[0]

        if ROI_COORDS and len(result.boxes) > 0:
            xywh = result.boxes.xywh
            center_x, center_y = xywh[:, 0], xywh[:, 1]
            mask = (center_x >= ROI_COORDS[0]) & (center_x <= ROI_COORDS[2]) & \
                   (center_y >= ROI_COORDS[1]) & (center_y <= ROI_COORDS[3])
            result.boxes = result.boxes[mask]

        annotated_frame = result.plot()
        filename = os.path.basename(filepath)
        annotated_path = os.path.join(ANNOTATED_DIR, filename)
        cv2.imwrite(annotated_path, annotated_frame)

        detections = []
        counts = {name: 0 for name in class_names.values()}

        for box in result.boxes:
            class_id = int(box.cls[0].item())
            conf = round(box.conf[0].item(), 2)
            xyxy = [int(x) for x in box.xyxy[0].tolist()]
            label = class_names[class_id]
            counts[label] += 1
            detections.append({"class": label, "confidence": conf, "bbox": xyxy})

        active_counts = {k: v for k, v in counts.items() if v > 0}
        detected_classes = list(active_counts.keys())

        # === 💥 МАГИЯ БИЗНЕС-ЛОГИКИ ===
        # Для хакатона: если грузовик есть в кадре, условно считаем, что приехал новый 
        # (в проде здесь берутся данные из ByteTrack)
        new_trucks = 1 if "dump_truck" in detected_classes else 0
        new_mixers = 1 if "mixer" in detected_classes else 0
        
        # Движок сам рассчитает параллельные этапы, каскадные 100/0 и вернет словарь прогресса
        active_stages, progress_metrics = cv_logic_engine.process_classes(
            detected_classes=detected_classes,
            new_trucks=new_trucks,
            new_mixers=new_mixers
        )

        # print(f"[AI Worker] ID:{frame_id} - Детекции: {active_counts}, Этапы: {active_stages}, Прогресс: {progress_metrics}")

        # 5. Запись расширенных метаданных в PostgreSQL
        frame_log.status = "processed"
        frame_log.ai_result = {
            "summary": active_counts,
            "details": detections,
            "annotated_image": annotated_path,
            "roi_applied": ROI_COORDS is not None,
            "business_logic": {                     # <--- Сохраняем выводы ИИ прямо в БД
                "active_stages": active_stages,
                "progress": progress_metrics
            }
        }
        db.commit()

        print(f"[AI Worker] Успех ID:{frame_id}. Этапы: {active_stages}")

    except Exception as e:
        print(f"[AI Worker] Ошибка обработки ID:{frame_id}: {e}")
        frame_log.status = "error"
        db.commit()
    finally:
        db.close()

    return True