from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_database_connection():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            print("✅ CONEXIÓN A MYSQL EXITOSA")
            return True
    except Exception as e:
        print("❌ ERROR DE CONEXIÓN A MYSQL")
        print(e)
        return False
