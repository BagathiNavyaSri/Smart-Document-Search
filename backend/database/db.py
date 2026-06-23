from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


DATABASE_URL = "sqlite:///./smart_search.db"


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


Base = declarative_base()


def ensure_chat_history_schema():
    with engine.begin() as connection:
        info = connection.execute(
            text("PRAGMA table_info(chat_history)")
        ).fetchall()

        columns = {row[1] for row in info}

        if "created_at" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE chat_history ADD COLUMN created_at DATETIME"
                )
            )

        if "source_filename" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE chat_history ADD COLUMN source_filename TEXT"
                )
            )

        if "source_page_number" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE chat_history ADD COLUMN source_page_number TEXT"
                )
            )

        if "sources_json" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE chat_history ADD COLUMN sources_json TEXT"
                )
            )