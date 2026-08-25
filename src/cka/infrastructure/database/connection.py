import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

logger = structlog.get_logger(__name__)


def make_engine(database_url: str, connect_timeout_seconds: int = 3) -> Engine:
    return create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": connect_timeout_seconds},
    )


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def check_database_connection(engine: Engine) -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("database_health_check_failed", error=str(exc))
        return False
