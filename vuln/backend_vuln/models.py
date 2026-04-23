from database import Base
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship

class UserTable(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    disabled = Column(Boolean, default=False)
    hashed_password = Column(String)

    user_lock = relationship("UserLockTable", back_populates="user")

class LockTable(Base):
    __tablename__ = "locks"
    lock_id = Column(Integer, primary_key=True, index=True)
    status = Column(String, default="Locked")

    user_lock = relationship("UserLockTable", back_populates="lock")

class UserLockTable(Base):
    __tablename__ = "user_locks"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    lock_id = Column(Integer, ForeignKey("locks.lock_id"), primary_key=True)
    role = Column(String, default="guest")

    user = relationship("UserTable", back_populates="user_lock")
    lock = relationship("LockTable", back_populates="user_lock")