import logging
from datetime import datetime, UTC

from sqlalchemy import Integer, Float, ForeignKey, TIMESTAMP, event
from sqlalchemy.orm import relationship, Mapped, mapped_column
from src.database import Base

logger = logging.getLogger(__name__)

class LastRun(Base):
    __tablename__ = "last_run"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, default=1)
    last_run: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

# @event.listens_for(LastRun, 'before_insert')
# def prevent_inserts(mapper, connection, target):
#
#     logger.error("Only update id=1 is available!")
#     # raise Exception("Only update id=1 is available!")

class Measurement(Base):
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    run_id: Mapped[int] = mapped_column(nullable=False)

    measure_datetime:  Mapped[TIMESTAMP] = mapped_column(TIMESTAMP, default=datetime.now())
    t201: Mapped[float] = mapped_column(Float, nullable=True)
    t202: Mapped[float] = mapped_column(Float, nullable=True)
    t203: Mapped[float] = mapped_column(Float, nullable=True)

    t204: Mapped[float] = mapped_column(Float, nullable=True)
    t205: Mapped[float] = mapped_column(Float, nullable=True)

    t206: Mapped[float] = mapped_column(Float, nullable=True)

    t207: Mapped[float] = mapped_column(Float, nullable=True)
    t208: Mapped[float] = mapped_column(Float, nullable=True)
    t209: Mapped[float] = mapped_column(Float, nullable=True)
    t210: Mapped[float] = mapped_column(Float, nullable=True)


