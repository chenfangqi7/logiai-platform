from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = {"comment": "租户信息表"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()), comment="租户唯一主键UUID")
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="租户企业名称")
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True, comment="租户唯一英文编码标识")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", comment="租户状态(active=启用, disabled=禁用)")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="记录创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="最后更新时间")
