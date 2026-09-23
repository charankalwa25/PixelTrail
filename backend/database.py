import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "pixeltrail.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_id TEXT UNIQUE NOT NULL,
            recipient TEXT NOT NULL,
            subject TEXT,
            sent_at TEXT NOT NULL,
            first_opened_at TEXT,
            last_opened_at TEXT,
            open_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'sent',
            click_count INTEGER NOT NULL DEFAULT 0,
            first_clicked_at TEXT,
            last_clicked_at TEXT,
            confirmed_seen_at TEXT
        )
        """
    )

    # Add new columns to an existing database if they don't exist yet
    existing_columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(emails)"
        ).fetchall()
    }

    if "click_count" not in existing_columns:
        connection.execute(
            """
            ALTER TABLE emails
            ADD COLUMN click_count INTEGER NOT NULL DEFAULT 0
            """
        )

    if "first_clicked_at" not in existing_columns:
        connection.execute(
            """
            ALTER TABLE emails
            ADD COLUMN first_clicked_at TEXT
            """
        )

    if "last_clicked_at" not in existing_columns:
        connection.execute(
            """
            ALTER TABLE emails
            ADD COLUMN last_clicked_at TEXT
            """
        )
        if "confirmed_seen_at" not in existing_columns:
         connection.execute(
        """
        ALTER TABLE emails
        ADD COLUMN confirmed_seen_at TEXT
        """
    )

    connection.commit()
    connection.close()


def create_email(tracking_id, recipient, subject, sent_at):
    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO emails (
            tracking_id,
            recipient,
            subject,
            sent_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            tracking_id,
            recipient,
            subject,
            sent_at
        )
    )

    connection.commit()

    email_id = cursor.lastrowid

    connection.close()

    return email_id


def get_email_by_tracking_id(tracking_id):
    connection = get_connection()

    email = connection.execute(
        """
        SELECT *
        FROM emails
        WHERE tracking_id = ?
        """,
        (tracking_id,)
    ).fetchone()

    connection.close()

    return email


def record_open(tracking_id, opened_at):
    connection = get_connection()

    connection.execute(
        """
        UPDATE emails
        SET
            first_opened_at = COALESCE(first_opened_at, ?),
            last_opened_at = ?,
            open_count = open_count + 1,
            status = 'opened'
        WHERE tracking_id = ?
        """,
        (
            opened_at,
            opened_at,
            tracking_id
        )
    )

    connection.commit()
    connection.close()


def get_all_emails():
    connection = get_connection()

    emails = connection.execute(
        """
        SELECT *
        FROM emails
        ORDER BY sent_at DESC
        """
    ).fetchall()

    connection.close()

    return emails
def record_click(tracking_id, clicked_at):
    connection = get_connection()

    connection.execute(
        """
        UPDATE emails
        SET
            first_clicked_at = COALESCE(first_clicked_at, ?),
            last_clicked_at = ?,
            click_count = click_count + 1
        WHERE tracking_id = ?
        """,
        (
            clicked_at,
            clicked_at,
            tracking_id
        )
    )

    connection.commit()
    connection.close()
def record_confirmed_seen(tracking_id, confirmed_at):
    connection = get_connection()

    connection.execute(
        """
        UPDATE emails
        SET confirmed_seen_at = ?
        WHERE tracking_id = ?
        """,
        (
            confirmed_at,
            tracking_id
        )
    )

    connection.commit()
    connection.close()