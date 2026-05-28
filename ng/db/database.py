"""
Database initialization and connection management.
"""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

import ng
from ng.db.models import Base


def ensure_schema_current(db_path: str, silent: bool = False) -> bool:
    """
    Ensure database schema is up to date by adding any missing columns.

    Args:
        db_path: Path to the SQLite database file
        silent: If True, suppress print statements

    Returns:
        True if schema was updated or already current, False on error
    """
    import sqlite3

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if papers table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='papers'"
        )
        if not cursor.fetchone():
            # Table doesn't exist yet, will be created by create_all
            conn.close()
            return True

        # Get current columns in papers table
        cursor.execute("PRAGMA table_info(papers)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        columns_added = []

        # Ensure affiliation table and author fields exist (migration 6c2b9a7f1d10)
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='affiliations'"
        )
        if not cursor.fetchone():
            cursor.execute(
                """
                CREATE TABLE affiliations (
                    id INTEGER NOT NULL,
                    institution VARCHAR(255) NOT NULL,
                    department VARCHAR(255),
                    url VARCHAR(500),
                    PRIMARY KEY (id),
                    UNIQUE (institution, department)
                )
                """
            )

        cursor.execute("PRAGMA table_info(authors)")
        author_columns = {row[1] for row in cursor.fetchall()}
        if "affiliation_id" not in author_columns:
            cursor.execute("ALTER TABLE authors ADD COLUMN affiliation_id INTEGER")
            columns_added.append("authors.affiliation_id")
        if "personal_url" not in author_columns:
            cursor.execute("ALTER TABLE authors ADD COLUMN personal_url VARCHAR(500)")
            columns_added.append("authors.personal_url")
        if "scholar_url" not in author_columns:
            cursor.execute("ALTER TABLE authors ADD COLUMN scholar_url VARCHAR(500)")
            columns_added.append("authors.scholar_url")
        if "orcid" not in author_columns:
            cursor.execute("ALTER TABLE authors ADD COLUMN orcid VARCHAR(50)")
            columns_added.append("authors.orcid")
        if "affiliation" in author_columns:
            cursor.execute(
                "SELECT DISTINCT affiliation FROM authors WHERE affiliation IS NOT NULL AND TRIM(affiliation) != ''"
            )
            for (institution,) in cursor.fetchall():
                cursor.execute(
                    "INSERT OR IGNORE INTO affiliations (institution, department, url) VALUES (?, NULL, NULL)",
                    (institution.strip(),),
                )
                cursor.execute(
                    "SELECT id FROM affiliations WHERE institution = ? AND department IS NULL",
                    (institution.strip(),),
                )
                row = cursor.fetchone()
                if row:
                    cursor.execute(
                        "UPDATE authors SET affiliation_id = ? WHERE affiliation = ? AND affiliation_id IS NULL",
                        (row[0], institution),
                    )
            # SQLite cannot drop columns safely on older versions; leave legacy column in fallback path.

        # Add html_snapshot_path column if missing (migration 03b4cd44700f)
        if "html_snapshot_path" not in existing_columns:
            cursor.execute(
                "ALTER TABLE papers ADD COLUMN html_snapshot_path VARCHAR(500)"
            )
            columns_added.append("html_snapshot_path")

        # Add uuid column if missing (migration 10f8534b9062)
        if "uuid" not in existing_columns:
            cursor.execute("ALTER TABLE papers ADD COLUMN uuid VARCHAR(36)")
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_papers_uuid ON papers (uuid)"
            )
            columns_added.append("uuid")

        if columns_added:
            # Update alembic_version to latest if table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
            )
            if cursor.fetchone():
                cursor.execute(
                    "UPDATE alembic_version SET version_num = '6c2b9a7f1d10'"
                )

            conn.commit()
            if not silent:
                print(f"✓ Database schema updated: added {', '.join(columns_added)}")

        conn.close()
        return True
    except Exception as e:
        if not silent:
            print(f"Warning: Failed to ensure schema is current: {e}")
        return False


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")

        # Enable foreign key constraints for SQLite
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=True, bind=self.engine
        )

    def create_tables(self) -> None:
        """Create all database tables using Alembic or fallback to direct creation."""
        # First try to use Alembic if available
        alembic_success = self._try_alembic_upgrade()

        if not alembic_success:
            # Fallback: Create tables directly using SQLAlchemy
            print("Alembic not available, creating tables directly...")
            Base.metadata.create_all(bind=self.engine)

        # Always ensure schema is up to date (adds missing columns if needed)
        ensure_schema_current(self.db_path)

    def _try_alembic_upgrade(self) -> bool:
        """Try to upgrade using Alembic. Returns True if successful."""
        try:
            # Try to find alembic.ini in the current directory first (for development)
            alembic_ini_path: Optional[str | Path] = "alembic.ini"
            alembic_dir: Optional[str | Path] = "alembic"

            if not os.path.exists(str(alembic_ini_path)):
                # Look for it relative to the ng package (installed package)
                ng_path = Path(ng.__file__).parent
                alembic_ini_path = ng_path / "alembic.ini"
                alembic_dir = ng_path / "alembic"

                if not alembic_ini_path.exists():
                    return False

            alembic_cfg = Config(str(alembic_ini_path))
            alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{self.db_path}")
            alembic_cfg.set_main_option("script_location", str(alembic_dir))

            command.upgrade(alembic_cfg, "head")
            return True
        except Exception:
            return False

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def init_database(db_path: str) -> DatabaseManager:
    """Initialize the database manager."""
    global _db_manager
    _db_manager = DatabaseManager(db_path)
    _db_manager.create_tables()
    return _db_manager


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    if _db_manager is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db_manager


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Get a database session."""
    db_manager = get_db_manager()
    with db_manager.get_session() as session:
        yield session


def get_pdf_directory() -> str:
    """Get the global PDF directory path."""
    db_manager = get_db_manager()
    pdf_dir = os.path.join(os.path.dirname(db_manager.db_path), "pdfs")
    os.makedirs(pdf_dir, exist_ok=True)
    return pdf_dir
