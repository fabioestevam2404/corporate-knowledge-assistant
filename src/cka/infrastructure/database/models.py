from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

EMBEDDING_DIMENSION = 384


class Base(DeclarativeBase):
    pass


class DocumentModel(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChunkModel(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), index=True, nullable=False
    )
    source_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=False)


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
