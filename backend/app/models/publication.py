from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.practice import uid


class CaseAuthorization(Base):
    __tablename__ = 'case_authorizations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey('cases.id'), index=True)
    reference: Mapped[str] = mapped_column(String(200))
    scope: Mapped[str] = mapped_column(Text)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TeachingCopy(Base):
    __tablename__ = 'teaching_copies'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    version_id: Mapped[str] = mapped_column(ForeignKey('case_versions.id'), unique=True)
    authorization_id: Mapped[str] = mapped_column(ForeignKey('case_authorizations.id'))
    manifest_key: Mapped[str] = mapped_column(String(512))
    checksum: Mapped[str] = mapped_column(String(64))
    review_note: Mapped[str] = mapped_column(Text)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    published_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
