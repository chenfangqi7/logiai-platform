from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "username", name="uq_users_tenant_username"),
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        {"comment": "系统用户信息表"},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()), comment="用户唯一主键UUID")
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True, comment="所属租户ID")
    username: Mapped[str] = mapped_column(String(80), nullable=False, comment="登录账号/用户名")
    email: Mapped[str] = mapped_column(String(255), nullable=False, comment="电子邮箱地址")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="加密密码散列值")
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="member", comment="用户角色(admin=管理员, member=普通成员)")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", comment="用户状态(active=启用, disabled=禁用)")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="记录创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="最后更新时间")
