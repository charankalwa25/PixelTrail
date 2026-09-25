import os
import sqlite3
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "pixeltrail.db"

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    """
    Use PostgreSQL when DATABASE_URL is available.
    Otherwise, use local SQLite for development.
    """

    if DATABASE_URL:
        return psycopg2.connect(
            DATABASE_URL,
            cursor_factory=RealDictCursor
        )

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_connection()

    if DATABASE_URL:
        # ==========================================
        # PostgreSQL
        # ==========================================

        cursor = connection.cursor()

        # ------------------------------
        # Users
        # ------------------------------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        # ------------------------------
        # Campaigns
        # ------------------------------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS campaigns (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                name TEXT NOT NULL,
                subject TEXT,
                body TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL
            )
            """
        )

        # ------------------------------
        # Existing emails table
        # ------------------------------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS emails (
                id BIGSERIAL PRIMARY KEY,
                campaign_id BIGINT REFERENCES campaigns(id) ON DELETE CASCADE,
                tracking_id TEXT UNIQUE NOT NULL,
                recipient TEXT NOT NULL,
                subject TEXT,
                body TEXT,
                sent_at TEXT NOT NULL,
                first_opened_at TEXT,
                last_opened_at TEXT,
                open_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'sent',
                message_id TEXT,
                click_count INTEGER NOT NULL DEFAULT 0,
                first_clicked_at TEXT,
                last_clicked_at TEXT,
                confirmed_seen_at TEXT
            )
            """
        )

        # ------------------------------
        # Upgrade existing emails table
        # ------------------------------
        cursor.execute(
            """
            ALTER TABLE emails
            ADD COLUMN IF NOT EXISTS campaign_id BIGINT
            REFERENCES campaigns(id)
            ON DELETE CASCADE
            """
        )
        cursor.execute(
        """
        ALTER TABLE emails
        ADD COLUMN IF NOT EXISTS body TEXT
        """
)
        cursor.execute(
        """
        ALTER TABLE emails
        ADD COLUMN IF NOT EXISTS message_id TEXT
        """
)


        # ------------------------------
        # Indexes
        # ------------------------------
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_campaigns_user_id
            ON campaigns(user_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_emails_campaign_id
            ON emails(campaign_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_emails_recipient
            ON emails(recipient)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_emails_tracking_id
            ON emails(tracking_id)
            """
        )

        connection.commit()
        connection.close()
        return

    # ==========================================
    # SQLite
    # ==========================================

    # ------------------------------
    # Users
    # ------------------------------
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    # ------------------------------
    # Campaigns
    # ------------------------------
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            subject TEXT,
            body TEXT,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
        """
    )

    # ------------------------------
    # Existing emails table
    # ------------------------------
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER,
            tracking_id TEXT UNIQUE NOT NULL,
            recipient TEXT NOT NULL,
            subject TEXT,
            sent_at TEXT NOT NULL,
            first_opened_at TEXT,
            last_opened_at TEXT,
            open_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'sent',
            message_id TEXT,
            click_count INTEGER NOT NULL DEFAULT 0,
            first_clicked_at TEXT,
            last_clicked_at TEXT,
            confirmed_seen_at TEXT
        )
        """
    )

    # ------------------------------
    # Upgrade existing emails table
    # ------------------------------
    existing_columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(emails)"
        ).fetchall()
    }

    if "campaign_id" not in existing_columns:
        connection.execute(
            """
            ALTER TABLE emails
            ADD COLUMN campaign_id INTEGER
            """
        )

    if "click_count" not in existing_columns:
        connection.execute(
            """
            ALTER TABLE emails
            ADD COLUMN click_count INTEGER NOT NULL DEFAULT 0
            """
        )

    if "body" not in existing_columns:
        connection.execute(
        """
        ALTER TABLE emails
        ADD COLUMN body TEXT
        """
        )

    if "message_id" not in existing_columns:
        connection.execute(
        """
        ALTER TABLE emails
        ADD COLUMN message_id TEXT
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

    # ------------------------------
    # Indexes
    # ------------------------------
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_campaigns_user_id
        ON campaigns(user_id)
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_emails_campaign_id
        ON emails(campaign_id)
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_emails_recipient
        ON emails(recipient)
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_emails_tracking_id
        ON emails(tracking_id)
        """
    )

    connection.commit()
    connection.close()


# =========================================================
# EMAIL FUNCTIONS
# =========================================================

def create_email(
    tracking_id,
    recipient,
    subject,
    sent_at,
    campaign_id=None
):
    connection = get_connection()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO emails (
                campaign_id,
                tracking_id,
                recipient,
                subject,
                sent_at
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                campaign_id,
                tracking_id,
                recipient,
                subject,
                sent_at
            )
        )

        email_id = cursor.fetchone()["id"]

    else:
        cursor = connection.execute(
            """
            INSERT INTO emails (
                campaign_id,
                tracking_id,
                recipient,
                subject,
                sent_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                campaign_id,
                tracking_id,
                recipient,
                subject,
                sent_at
            )
        )

        email_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return email_id


def get_email_by_tracking_id(tracking_id):
    connection = get_connection()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM emails
            WHERE tracking_id = %s
            """,
            (tracking_id,)
        )

        email = cursor.fetchone()

    else:
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

    if DATABASE_URL:
        connection.cursor().execute(
            """
            UPDATE emails
            SET
                first_opened_at = COALESCE(first_opened_at, %s),
                last_opened_at = %s,
                open_count = open_count + 1,
                status = 'opened'
            WHERE tracking_id = %s
            """,
            (
                opened_at,
                opened_at,
                tracking_id
            )
        )

    else:
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

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM emails
            ORDER BY sent_at DESC
            """
        )

        emails = cursor.fetchall()

    else:
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

    if DATABASE_URL:
        connection.cursor().execute(
            """
            UPDATE emails
            SET
                first_clicked_at = COALESCE(first_clicked_at, %s),
                last_clicked_at = %s,
                click_count = click_count + 1
            WHERE tracking_id = %s
            """,
            (
                clicked_at,
                clicked_at,
                tracking_id
            )
        )

    else:
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

    if DATABASE_URL:
        connection.cursor().execute(
            """
            UPDATE emails
            SET confirmed_seen_at = %s
            WHERE tracking_id = %s
            """,
            (
                confirmed_at,
                tracking_id
            )
        )

    else:
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


# =========================================================
# USER FUNCTIONS
# =========================================================

def create_user(email, password_hash, created_at):
    connection = get_connection()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO users (
                email,
                password_hash,
                created_at
            )
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (
                email,
                password_hash,
                created_at
            )
        )

        user_id = cursor.fetchone()["id"]

    else:
        cursor = connection.execute(
            """
            INSERT INTO users (
                email,
                password_hash,
                created_at
            )
            VALUES (?, ?, ?)
            """,
            (
                email,
                password_hash,
                created_at
            )
        )

        user_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return user_id


def get_user_by_email(email):
    connection = get_connection()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()

    else:
        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

    connection.close()

    return user


def get_user_by_id(user_id):
    connection = get_connection()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )

        user = cursor.fetchone()

    else:
        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        ).fetchone()

    connection.close()

    return user





# =========================================================
# CAMPAIGN FUNCTIONS
# =========================================================

def create_campaign(
    user_id,
    name,
    subject,
    body,
    created_at,
    status="draft"
):
    connection = get_connection()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO campaigns (
                user_id,
                name,
                subject,
                body,
                status,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user_id,
                name,
                subject,
                body,
                status,
                created_at
            )
        )

        campaign_id = cursor.fetchone()["id"]

    else:
        cursor = connection.execute(
            """
            INSERT INTO campaigns (
                user_id,
                name,
                subject,
                body,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                name,
                subject,
                body,
                status,
                created_at
            )
        )

        campaign_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return campaign_id


def get_campaign_by_id(campaign_id):
    connection = get_connection()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM campaigns
            WHERE id = %s
            """,
            (campaign_id,)
        )

        campaign = cursor.fetchone()

    else:
        campaign = connection.execute(
            """
            SELECT *
            FROM campaigns
            WHERE id = ?
            """,
            (campaign_id,)
        ).fetchone()

    connection.close()

    return campaign


def get_campaigns_by_user(user_id):
    connection = get_connection()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM campaigns
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user_id,)
        )

        campaigns = cursor.fetchall()

    else:
        campaigns = connection.execute(
            """
            SELECT *
            FROM campaigns
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,)
        ).fetchall()

    connection.close()

    return campaigns

def get_emails_by_campaign(campaign_id):
    connection = get_connection()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM emails
            WHERE campaign_id = %s
            ORDER BY sent_at DESC
            """,
            (campaign_id,)
        )

        emails = cursor.fetchall()

    else:
        emails = connection.execute(
            """
            SELECT *
            FROM emails
            WHERE campaign_id = ?
            ORDER BY sent_at DESC
            """,
            (campaign_id,)
        ).fetchall()

    connection.close()

    return emails

def create_campaign_email(
    campaign_id,
    tracking_id,
    recipient,
    subject,
    body,
    sent_at,
    status="queued"
):
    connection = get_connection()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO emails (
                campaign_id,
                tracking_id,
                recipient,
                subject,
                body,
                sent_at,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                campaign_id,
                tracking_id,
                recipient,
                subject,
                body,
                sent_at,
                status
            )
        )

        email_id = cursor.fetchone()["id"]

    else:
        cursor = connection.execute(
            """
            INSERT INTO emails (
                campaign_id,
                tracking_id,
                recipient,
                subject,
                body,
                sent_at,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                campaign_id,
                tracking_id,
                recipient,
                subject,
                body,
                sent_at,
                status
            )
        )

        email_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return email_id

def get_campaign_email_by_recipient(campaign_id, recipient):
    connection = get_connection()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM emails
            WHERE campaign_id = %s
              AND recipient = %s
            LIMIT 1
            """,
            (
                campaign_id,
                recipient
            )
        )

        email = cursor.fetchone()

    else:
        email = connection.execute(
            """
            SELECT *
            FROM emails
            WHERE campaign_id = ?
              AND recipient = ?
            LIMIT 1
            """,
            (
                campaign_id,
                recipient
            )
        ).fetchone()

    connection.close()

    return email

def update_campaign_status(campaign_id, status):
    connection = get_connection()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE campaigns
            SET status = %s
            WHERE id = %s
            """,
            (
                status,
                campaign_id
            )
        )

    else:
        connection.execute(
            """
            UPDATE campaigns
            SET status = ?
            WHERE id = ?
            """,
            (
                status,
                campaign_id
            )
        )

    connection.commit()
    connection.close()

def update_campaign_email_message_id(email_id, message_id):
    connection = get_connection()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE emails
            SET message_id = %s
            WHERE id = %s
            """,
            (
                message_id,
                email_id
            )
        )

    else:
        connection.execute(
            """
            UPDATE emails
            SET message_id = ?
            WHERE id = ?
            """,
            (
                message_id,
                email_id
            )
        )

    connection.commit()
    connection.close()

def update_campaign_email_status(email_id, status):
    connection = get_connection()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE emails
            SET status = %s
            WHERE id = %s
            """,
            (
                status,
                email_id
            )
        )

    else:
        connection.execute(
            """
            UPDATE emails
            SET status = ?
            WHERE id = ?
            """,
            (
                status,
                email_id
            )
        )

    connection.commit()
    connection.close()