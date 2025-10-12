from datetime import datetime, UTC

from sqlalchemy import Integer, Float, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship, Mapped, mapped_column
from src.database import Base


class LastRun(Base):
    __tablename__ = "last_run"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    last_run: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Measurement(Base):
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    run_id: Mapped[int] = mapped_column(nullable=False)

    measure_datetime:  Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, default=datetime.now(UTC))

    t205: Mapped[float] = mapped_column(Float, nullable=False)
    t206: Mapped[float] = mapped_column(Float, nullable=False)
    t207: Mapped[float] = mapped_column(Float, nullable=False)
    t208: Mapped[float] = mapped_column(Float, nullable=False)
    t209: Mapped[float] = mapped_column(Float, nullable=False)
    t210: Mapped[float] = mapped_column(Float, nullable=False)


