from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Interval
from sqlalchemy.orm import relationship, backref, Mapped
from sqlalchemy.ext.declarative import declarative_base
from typing import List, Dict, Union, Optional, Any
from datetime import datetime, timedelta

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)

    balance = Column(Integer, default=0, nullable=False)
    last_daily = Column(DateTime, default=datetime.utcnow() - timedelta(days=1), nullable=False)

    subscription_id = Column(Integer, ForeignKey("subscriptions.id"))
    subscription:Mapped["Subscription"] = relationship("Subscription", back_populates="users")
    expire_at = Column(DateTime, nullable=True)

    refferal_id = Column(Integer, ForeignKey("users.id"))
    refferal:Mapped["User"] = relationship("User", back_populates="refferals", remote_side=[id])
    refferals:Mapped[List["User"]] = relationship("User", back_populates="refferal")

    created_at = Column(DateTime, default=datetime.utcnow(), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow(), nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, is_admin={self.is_admin}, is_banned={self.is_banned}, balance={self.balance}, last_daily={self.last_daily}, subscription_id={self.subscription_id}, expire_at={self.expire_at})>"

class ReferalLevel(Base):
    __tablename__ = "referal_levels"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    lvl = Column(Integer, default=0, nullable=False)
    count = Column(Integer, default=0, nullable=False)
    bonus_time:Mapped[timedelta] = Column(Interval, nullable=False)

    def __repr__(self):
        return f"<ReferalLevel(id={self.id}, name={self.name}, lvl={self.lvl}, bonus_time={self.bonus_time})>"

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=False)
    price:Mapped[int] = Column(Integer, default=0, nullable=False)
    duration:Mapped[timedelta] = Column(Interval, nullable=False)

    users:Mapped[List["User"]] = relationship("User", back_populates="subscription")
    
    logs:Mapped[List["Log"]] = relationship("Log", back_populates="subscriptions",secondary="logs_subscriptions")


    def __repr__(self):
        return f"<Subscription(id={self.id}, name={self.name}, price={self.price}, duration={self.duration}, user_id={self.user_id})>"

class Log(Base):
    __tablename__ = "logs"
    id: Mapped[int] = Column(Integer, primary_key=True)
    subscriptions: Mapped[List["Subscription"]] = relationship("Subscription", back_populates="logs",secondary="logs_subscriptions")
    file_id: Mapped[str] = Column(String, nullable=False)
    count: Mapped[int] = Column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow(), nullable=False)
    updated_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow(), onupdate=datetime.utcnow(), nullable=False)
    send_at: Mapped[datetime] = Column(DateTime, nullable=False)
    is_sended: Mapped[bool] = Column(Boolean, default=False, nullable=False)


    def __init__(self, file_id:str, send_at:datetime, count:int=0):
        self.file_id = file_id
        self.send_at = send_at
        self.count = count


class LogsSubscriptions(Base):
    __tablename__ = "logs_subscriptions"
    log_id: Mapped[int] = Column(Integer, ForeignKey("logs.id"), primary_key=True)
    subscription_id: Mapped[int] = Column(Integer, ForeignKey("subscriptions.id"), primary_key=True)

    def __init__(self, log_id:int, subscription_id:int):
        self.log_id = log_id
        self.subscription_id = subscription_id