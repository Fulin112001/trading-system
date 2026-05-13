import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import sessionmaker
from backend.database import Base, init_db
from datetime import datetime

class Journal(Base):
    __tablename__ = "journals"
    id           = Column(Integer, primary_key=True)
    created_at   = Column(DateTime, default=datetime.now)
    date         = Column(String)
    symbol       = Column(String)
    price        = Column(Float, nullable=True)
    score        = Column(Float, nullable=True)
    observation  = Column(Text)
    judgment     = Column(String)
    reason       = Column(Text)
    result       = Column(String, nullable=True)
    result_note  = Column(Text, nullable=True)

def init_journal():
    engine, Session = init_db()
    Base.metadata.create_all(engine)
    return engine, Session

if __name__ == "__main__":
    init_journal()
    print("✅ 交易日記資料表建立完成")
