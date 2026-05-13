from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Signal(Base):
    __tablename__ = "signals"
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.now)
    symbol = Column(String)
    direction = Column(String)
    confidence = Column(Float)
    reason = Column(Text)
    strategy = Column(String)
    market_state = Column(String)
    price = Column(Float)
    executed = Column(Boolean, default=False)

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.now)
    symbol = Column(String)
    direction = Column(String)
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Float)
    pnl = Column(Float, nullable=True)
    status = Column(String, default="open")
    broker = Column(String)
    strategy = Column(String)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)

class RiskState(Base):
    __tablename__ = "risk_states"
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.now)
    mode = Column(String, default="NORMAL")
    daily_pnl = Column(Float, default=0)
    consecutive_losses = Column(Integer, default=0)
    total_drawdown = Column(Float, default=0)
    available_capital = Column(Float, default=0)

class PersonalFinance(Base):
    __tablename__ = "personal_finance"
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.now)
    category = Column(String)
    sub_category = Column(String)
    type = Column(String)
    amount = Column(Float)
    note = Column(Text, nullable=True)
    venture = Column(String, nullable=True)

class Watchlist(Base):
    __tablename__ = "watchlist"
    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    name = Column(String)
    market = Column(String)
    score = Column(Float, default=0)
    fundamental_score = Column(Float, default=0)
    technical_score = Column(Float, default=0)
    status = Column(String, default="watching")
    note = Column(Text, nullable=True)
    added_at = Column(DateTime, default=datetime.now)

def init_db():
    engine = create_engine("sqlite:///database/trading.db")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session

if __name__ == "__main__":
    engine, Session = init_db()
    print("資料庫建立成功！")
