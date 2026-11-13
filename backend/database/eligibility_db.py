from pathlib import Path
import sqlite3
from contextlib import contextmanager

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "eligibility" / "eligibility.db"


@contextmanager
def get_connection(db_path=None):
    path = Path(db_path or DEFAULT_DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(db_path=None):
    with get_connection(db_path) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS schemes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scheme_id TEXT NOT NULL UNIQUE,
            scheme_name TEXT NOT NULL,
            government_level TEXT,
            department TEXT,
            official_url TEXT,
            verification_status TEXT NOT NULL DEFAULT 'unverified'
                CHECK (verification_status IN ('verified', 'unverified', 'needs_review')),
            last_verified_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS eligibility_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scheme_id TEXT NOT NULL,
            rule_name TEXT NOT NULL,
            condition_json TEXT NOT NULL,
            is_mandatory INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (scheme_id) REFERENCES schemes(scheme_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS rule_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id INTEGER NOT NULL,
            document_name TEXT NOT NULL,
            page_number INTEGER,
            url TEXT,
            excerpt TEXT,
            FOREIGN KEY (rule_id) REFERENCES eligibility_rules(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_rules_scheme_id ON eligibility_rules(scheme_id);
        CREATE INDEX IF NOT EXISTS idx_schemes_status ON schemes(verification_status);
        """)
