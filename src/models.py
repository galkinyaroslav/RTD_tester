from datetime import datetime, UTC

from sqlalchemy import Integer, Float, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship, Mapped, mapped_column
from src.database import Base


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    run_number: Mapped[int] = mapped_column(Integer, nullable=False)

    measurements: Mapped[list["Measurement"]] = relationship(
        back_populates="run", cascade="all, delete"
    )


class Measurement(Base):
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))

    measure_datetime:  Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, default=datetime.now(UTC))

    t205: Mapped[float] = mapped_column(Float)
    t206: Mapped[float] = mapped_column(Float)
    t207: Mapped[float] = mapped_column(Float)
    t208: Mapped[float] = mapped_column(Float)
    t209: Mapped[float] = mapped_column(Float)
    t210: Mapped[float] = mapped_column(Float)

    run: Mapped["Run"] = relationship(back_populates="measurements")

