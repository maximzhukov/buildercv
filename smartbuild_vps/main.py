import os
import shutil
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Depends
from sqlalchemy.orm import Session
from buildercv.smartbuild_vps.database import SessionLocal, FrameLog
from buildercv.smartbuild_vps.tasks import process_frame

app = FastAPI(title="SmartBuild MVP API")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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