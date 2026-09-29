import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

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
        # Brevo Accounts
        # ------------------------------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS brevo_accounts (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                account_name TEXT NOT NULL,
                api_key TEXT NOT NULL,
                sender_email TEXT,
                sender_name TEXT,
                status TEXT NOT NULL DEFAULT 'connected',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            )
            """
        )

                # -----------------------------
        # Senders
        # -----------------------------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS senders (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                brevo_sender_id BIGINT,
                verified BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                UNIQUE (user_id, email)
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


            # -----------------------------
        # Upgrade existing campaigns table
        # -----------------------------
        cursor.execute(
            """
            ALTER TABLE campaigns
            ADD COLUMN IF NOT EXISTS sender_id BIGINT
            REFERENCES senders(id)
            ON DELETE SET NULL
            """
        )

        cursor.execute(
            """
            ALTER TABLE campaigns
            ADD COLUMN IF NOT EXISTS brevo_account_id BIGINT
            REFERENCES brevo_accounts(id)
            ON DELETE SET NULL
            """
        )


        # ---------------------------
        # Campaign tracking settings
        # ---------------------------

        cursor.execute(
            """
            ALTER TABLE campaigns
            ADD COLUMN IF NOT EXISTS open_tracking BOOLEAN NOT NULL DEFAULT TRUE
            """
        )

        cursor.execute(
            """
            ALTER TABLE campaigns
            ADD COLUMN IF NOT EXISTS click_tracking BOOLEAN NOT NULL DEFAULT TRUE
            """
        )

        cursor.execute(
            """
            ALTER TABLE campaigns
            ADD COLUMN IF NOT EXISTS confirm_seen BOOLEAN NOT NULL DEFAULT TRUE
            """
        )


        # -----------------------------
        # Indexes
        # -----------------------------
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

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_brevo_accounts_user_id
            ON brevo_accounts(user_id)
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
    # Brevo Accounts
    # ------------------------------
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS brevo_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            account_name TEXT NOT NULL,
            api_key TEXT NOT NULL,
            sender_email TEXT,
            sender_name TEXT,
            status TEXT NOT NULL DEFAULT 'connected',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
        """
    )   

        # -----------------------------
    # Senders
    # -----------------------------
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS senders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            brevo_sender_id INTEGER,
            verified INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,
            UNIQUE (user_id, email)
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

        # -----------------------------
    # Upgrade existing campaigns table
    # -----------------------------
    campaign_columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(campaigns)"
        ).fetchall()
    }

    if "sender_id" not in campaign_columns:
        connection.execute(
            """
            ALTER TABLE campaigns
            ADD COLUMN sender_id INTEGER
            REFERENCES senders(id)
            ON DELETE SET NULL
            """
        )

    # ---------------------------
    # Campaign tracking settings
    # ---------------------------

    if "open_tracking" not in campaign_columns:
        connection.execute(
            """
            ALTER TABLE campaigns
            ADD COLUMN open_tracking INTEGER NOT NULL DEFAULT 1
            """
        )

    if "click_tracking" not in campaign_columns:
        connection.execute(
            """
            ALTER TABLE campaigns
            ADD COLUMN click_tracking INTEGER NOT NULL DEFAULT 1
            """
        )

    if "confirm_seen" not in campaign_columns:
        connection.execute(
            """
            ALTER TABLE campaigns
            ADD COLUMN confirm_seen INTEGER NOT NULL DEFAULT 1
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

        # -----------------------------
    # Upgrade existing campaigns table
    # -----------------------------

    campaign_columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(campaigns)"
        ).fetchall()
    }

    if "sender_id" not in campaign_columns:
        connection.execute(
            """
            ALTER TABLE campaigns
            ADD COLUMN sender_id INTEGER
            REFERENCES senders(id)
            ON DELETE SET NULL
            """
        )        

    if "brevo_account_id" not in campaign_columns:
        connection.execute(
            """
            ALTER TABLE campaigns
            ADD COLUMN brevo_account_id INTEGER
            REFERENCES brevo_accounts(id)
            ON DELETE SET NULL
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

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_brevo_accounts_user_id
        ON brevo_accounts(user_id)
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


# ============================================================
# SENDER FUNCTIONS
# ============================================================

def create_sender(user_id, name, email, brevo_sender_id=None, verified=False):
    connection = get_connection()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO senders (
                user_id,
                name,
                email,
                brevo_sender_id,
                verified,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user_id,
                name,
                email,
                brevo_sender_id,
                verified,
                datetime.now(timezone.utc).isoformat()
            )
        )

        sender_id = cursor.fetchone()["id"]

    else:
        cursor = connection.execute(
            """
            INSERT INTO senders (
                user_id,
                name,
                email,
                brevo_sender_id,
                verified,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                name,
                email,
                brevo_sender_id,
                int(verified),
                datetime.now(timezone.utc).isoformat()
            )
        )

        sender_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return sender_id


def get_senders_by_user(user_id):
    connection = get_connection()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                name,
                email,
                brevo_sender_id,
                verified,
                created_at
            FROM senders
            WHERE user_id = %s
            ORDER BY id DESC
            """,
            (user_id,)
        )

        senders = cursor.fetchall()

    else:
        senders = connection.execute(
            """
            SELECT
                id,
                user_id,
                name,
                email,
                brevo_sender_id,
                verified,
                created_at
            FROM senders
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,)
        ).fetchall()

    connection.close()

    return senders


def get_sender_by_id(sender_id, user_id):
    connection = get_connection()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                name,
                email,
                brevo_sender_id,
                verified,
                created_at
            FROM senders
            WHERE id = %s
              AND user_id = %s
            """,
            (
                sender_id,
                user_id
            )
        )

        sender = cursor.fetchone()

    else:
        sender = connection.execute(
            """
            SELECT
                id,
                user_id,
                name,
                email,
                brevo_sender_id,
                verified,
                created_at
            FROM senders
            WHERE id = ?
              AND user_id = ?
            """,
            (
                sender_id,
                user_id
            )
        ).fetchone()

    connection.close()

    return sender


def update_sender_verification(sender_id, user_id, verified):
    connection = get_connection()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE senders
            SET verified = %s
            WHERE id = %s
              AND user_id = %s
            """,
            (
                verified,
                sender_id,
                user_id
            )
        )

    else:
        connection.execute(
            """
            UPDATE senders
            SET verified = ?
            WHERE id = ?
              AND user_id = ?
            """,
            (
                int(verified),
                sender_id,
                user_id
            )
        )

    connection.commit()
    connection.close()





# =========================================================
# CAMPAIGN FUNCTIONS
# =========================================================

def create_campaign(
    user_id,
    name,
    subject,
    body,
    created_at,
    status="draft",
    sender_id=None,
    brevo_account_id=None,
    open_tracking=True,
    click_tracking=True,
    confirm_seen=True
):
    connection = get_connection()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO campaigns (
                user_id,
                sender_id,
                brevo_account_id,
                name,
                subject,
                body,
                open_tracking,
                click_tracking,
                confirm_seen,
                status,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user_id,
                sender_id,
                brevo_account_id,
                name,
                subject,
                body,
                open_tracking,
                click_tracking,
                confirm_seen,
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
                sender_id,
                brevo_account_id,
                name,
                subject,
                body,
                open_tracking,
                click_tracking,
                confirm_seen,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                sender_id,
                brevo_account_id,
                name,
                subject,
                body,
                open_tracking,
                click_tracking,
                confirm_seen,
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


# =========================================================
# BREVO ACCOUNT FUNCTIONS
# =========================================================

def create_brevo_account(
    user_id,
    account_name,
    api_key,
    sender_email=None,
    sender_name=None,
    status="connected"
):
    connection = get_connection()

    created_at = datetime.now(timezone.utc).isoformat()
    updated_at = created_at

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO brevo_accounts (
                user_id,
                account_name,
                api_key,
                sender_email,
                sender_name,
                status,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user_id,
                account_name,
                api_key,
                sender_email,
                sender_name,
                status,
                created_at,
                updated_at
            )
        )

        account_id = cursor.fetchone()["id"]

    else:
        cursor = connection.execute(
            """
            INSERT INTO brevo_accounts (
                user_id,
                account_name,
                api_key,
                sender_email,
                sender_name,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                account_name,
                api_key,
                sender_email,
                sender_name,
                status,
                created_at,
                updated_at
            )
        )

        account_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return account_id


def get_brevo_accounts_by_user(user_id):
    connection = get_connection()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                user_id,
                account_name,
                sender_email,
                sender_name,
                status,
                created_at,
                updated_at
            FROM brevo_accounts
            WHERE user_id = %s
            ORDER BY id DESC
            """,
            (user_id,)
        )

        accounts = cursor.fetchall()

    else:
        accounts = connection.execute(
            """
            SELECT
                id,
                user_id,
                account_name,
                sender_email,
                sender_name,
                status,
                created_at,
                updated_at
            FROM brevo_accounts
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,)
        ).fetchall()

    connection.close()

    return accounts


def get_brevo_account_by_id(account_id, user_id):
    connection = get_connection()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM brevo_accounts
            WHERE id = %s
              AND user_id = %s
            """,
            (
                account_id,
                user_id
            )
        )

        account = cursor.fetchone()

    else:
        account = connection.execute(
            """
            SELECT *
            FROM brevo_accounts
            WHERE id = ?
              AND user_id = ?
            """,
            (
                account_id,
                user_id
            )
        ).fetchone()

    connection.close()

    return account


def update_brevo_account(
    account_id,
    user_id,
    account_name=None,
    api_key=None,
    sender_email=None,
    sender_name=None,
    status=None
):
    connection = get_connection()

    updated_at = datetime.now(timezone.utc).isoformat()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE brevo_accounts
            SET
                account_name = COALESCE(%s, account_name),
                api_key = COALESCE(%s, api_key),
                sender_email = COALESCE(%s, sender_email),
                sender_name = COALESCE(%s, sender_name),
                status = COALESCE(%s, status),
                updated_at = %s
            WHERE id = %s
              AND user_id = %s
            """,
            (
                account_name,
                api_key,
                sender_email,
                sender_name,
                status,
                updated_at,
                account_id,
                user_id
            )
        )

    else:
        connection.execute(
            """
            UPDATE brevo_accounts
            SET
                account_name = COALESCE(?, account_name),
                api_key = COALESCE(?, api_key),
                sender_email = COALESCE(?, sender_email),
                sender_name = COALESCE(?, sender_name),
                status = COALESCE(?, status),
                updated_at = ?
            WHERE id = ?
              AND user_id = ?
            """,
            (
                account_name,
                api_key,
                sender_email,
                sender_name,
                status,
                updated_at,
                account_id,
                user_id
            )
        )

    connection.commit()
    connection.close()


def delete_brevo_account(account_id, user_id):
    connection = get_connection()

    if DATABASE_URL:
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM brevo_accounts
            WHERE id = %s
              AND user_id = %s
            """,
            (
                account_id,
                user_id
            )
        )

        deleted = cursor.rowcount > 0

    else:
        cursor = connection.execute(
            """
            DELETE FROM brevo_accounts
            WHERE id = ?
              AND user_id = ?
            """,
            (
                account_id,
                user_id
            )
        )

        deleted = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return deleted    