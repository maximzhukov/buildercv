import os
import shutil
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, FrameLog
from tasks import process_frame

app = FastAPI(title="SmartBuild MVP API")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Функция для очистки директории
def cleanup_upload_dir(directory: str, max_files: int = 80):
    try:
        # Получаем список только файлов (игнорируем вложенные папки, если они вдруг появятся)
        files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
        
        # Если файлов больше лимита, удаляем их все
        if len(files) > max_files:
            for file_name in files:
                file_path = os.path.join(directory, file_name)
                file_path_annotated = os.path.join(directory + '/annotated', file_name)
                try:
                    os.remove(file_path)
                    os.remove(file_path_annotated)
                except Exception as e:
                    print(f"Ошибка при удалении файла {file_path}: {e}")
            print(f"Папка {directory} очищена. Удалено {len(files)} файлов.")
    except Exception as e:
        print(f"Ошибка при проверке директории {directory}: {e}")

# Функция для безопасного подключения к БД для каждого запроса
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/api/upload")
async def upload_frame(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Эндпоинт принимает фото с камеры, сохраняет и кидает задачу ИИ"""
    
    # --- 0. Проверяем и очищаем папку перед загрузкой ---
    cleanup_upload_dir(UPLOAD_DIR, max_files=98)
    
    # 1. Генерируем уникальное имя файла, чтобы они не перезаписали друг друга
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, safe_filename)

    # 2. Сохраняем файл на диск (имитация S3 хранилища)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 3. Делаем запись в БД, что кадр получен
    db_log = FrameLog(
        filename=safe_filename,
        filepath=filepath,
        status="pending"
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)

    # 4. Отправляем асинхронную задачу в очередь! 
    # Сервер не ждет ответа от нейросети, а мгновенно отвечает камере "Ок"
    process_frame.delay(db_log.id, filepath)

    return {
        "status": "success", 
        "frame_id": db_log.id, 
        "message": "Кадр сохранен и передан в очередь ИИ"
    }


@app.get("/api/frames/{frame_id}")
def get_frame_status(frame_id: int, db: Session = Depends(get_db)):
    frame_log = db.query(FrameLog).filter(FrameLog.id == frame_id).first()
    if frame_log is None:
        raise HTTPException(status_code=404, detail="Кадр не найден")
    return {"frame_id": frame_log.id, "status": frame_log.status}