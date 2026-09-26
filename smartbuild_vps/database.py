from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# Ссылка для подключения к нашему Docker-контейнеру Postgres
DATABASE_URL = "postgresql://admin:secretpassword@localhost:5432/smartbuild_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Описание нашей таблицы в базе данных
class FrameLog(Base):
    __tablename__ = "frame_logs"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    filepath = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending") # Статусы: pending, processed, error
    ai_result = Column(JSON, nullable=True)    # Сюда нейросеть потом положит JSON с техникой

# Автоматически создаем таблицу при запуске
Base.metadata.create_all(bind=engine)