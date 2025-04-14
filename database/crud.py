import logging
import sqlite3

from aiogram import Bot

from .models import Ticket


class Database:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        """Инициализация таблиц в базе данных"""
        self.cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            company TEXT,
            phone TEXT,
            market TEXT,
            is_admin BOOLEAN DEFAULT FALSE,
            confirmed BOOLEAN DEFAULT FALSE
        );

        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'open',
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER,
            user_id INTEGER,
            text TEXT,
            photo_path TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_from_support BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id),
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        );

        CREATE TABLE IF NOT EXISTS photos (
            photo_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER,
            file_path TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id)
        );
        """)
        self.conn.commit()

    def create_ticket(self, user_id: int) -> int:
        """Создает новую заявку и возвращает её ID"""
        self.cursor.execute("INSERT INTO tickets (user_id) VALUES (?)", (user_id,))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_active_ticket(self, user_id: int):
        """Возвращает активную заявку как словарь"""
        self.cursor.execute(
            """
        SELECT * FROM tickets 
        WHERE user_id = ? AND status != 'closed'
        ORDER BY last_updated DESC LIMIT 1
        """,
            (user_id,),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None  # Преобразуем в словарь

        row = self.cursor.fetchone()
        return Ticket(row) if row else None

    def update_ticket_timestamp(self, ticket_id: int):
        """Обновляет время последнего изменения заявки"""
        self.cursor.execute(
            "UPDATE tickets SET last_updated = CURRENT_TIMESTAMP WHERE ticket_id = ?",
            (ticket_id,),
        )
        self.conn.commit()

    def get_user(self, user_id: int):
        """Получает пользователя по ID"""
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        return row if row else None

    def get_active_tickets(self, user_id: int):
        """Получает активные задачи пользователя"""
        self.cursor.execute(
            """
        SELECT t.ticket_id, t.created_at, t.status, t.last_updated, 
               GROUP_CONCAT(p.file_path, ';;') as photos
        FROM tickets t
        LEFT JOIN photos p ON t.ticket_id = p.ticket_id
        WHERE t.user_id = ? AND t.status != 'closed'
        GROUP BY t.ticket_id
        ORDER BY t.last_updated DESC
        """,
            (user_id,),
        )
        return self.cursor.fetchall()

    def add_photo_to_ticket(self, ticket_id: int, file_path: str):
        """Добавляет фото к заявке"""
        logging.info(f"Добавление фото {file_path} к заявке #{ticket_id}")

        self.cursor.execute(
            "INSERT INTO photos (ticket_id, file_path) VALUES (?, ?)",
            (ticket_id, file_path),
        )
        self.conn.commit()

    def add_message_to_ticket(
        self, ticket_id: int, user_id: int, text: str, photo_path: str = None
    ):
        """Добавляет сообщение к заявке"""
        logging.info(f"Добавление сообщения к заявке #{ticket_id}")

        self.cursor.execute(
            "INSERT INTO messages (ticket_id, user_id, text, photo_path) VALUES (?, ?, ?, ?)",
            (ticket_id, user_id, text, photo_path),
        )
        self.conn.commit()
        self.update_ticket_timestamp(ticket_id)

    def update_ticket_timestamp(self, ticket_id: int):
        """Обновляет время изменения заявки"""
        self.cursor.execute(
            "UPDATE tickets SET last_updated = CURRENT_TIMESTAMP WHERE ticket_id = ?",
            (ticket_id,),
        )
        self.conn.commit()

    def get_ticket_details(self, ticket_id: int):
        """Получает детали заявки с проверкой"""
        self.cursor.execute(
            """
        SELECT * FROM tickets WHERE ticket_id = ?
        """,
            (ticket_id,),
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_ticket_messages(self, ticket_id: int):
        """Получает сообщения заявки"""
        self.cursor.execute(
            """
        SELECT text FROM messages WHERE ticket_id = ? ORDER BY sent_at
        """,
            (ticket_id,),
        )
        return [dict(row) for row in self.cursor.fetchall()]

    def update_ticket_status(self, ticket_id: int, new_status: str, bot: Bot = None):
        old_status = self.get_ticket_details(ticket_id)["status"]
        self.cursor.execute(
            """
        UPDATE tickets SET status = ?, last_updated = CURRENT_TIMESTAMP
        WHERE ticket_id = ?
        """,
            (new_status, ticket_id),
        )
        self.conn.commit()

        if bot:
            import asyncio
            from handlers.notifications import notify_status_change

            asyncio.create_task(
                notify_status_change(bot, ticket_id, old_status, new_status)
            )

    def get_user_tickets(self, user_id):
        """Получает все задачи пользователя"""
        self.cursor.execute(
            """
        SELECT t.*, 
               COUNT(m.message_id) as messages_count,
               COUNT(p.photo_id) as photos_count
        FROM tickets t
        LEFT JOIN messages m ON t.ticket_id = m.ticket_id
        LEFT JOIN photos p ON t.ticket_id = p.ticket_id
        WHERE t.user_id = ?
        GROUP BY t.ticket_id
        ORDER BY t.created_at DESC
        """,
            (user_id,),
        )
        return self.cursor.fetchall()

    def get_ticket_photos(self, ticket_id):
        """Получает все фото задачи"""
        self.cursor.execute(
            """
        SELECT file_path FROM photos 
        WHERE ticket_id = ?
        ORDER BY uploaded_at
        """,
            (ticket_id,),
        )
        return self.cursor.fetchall()

    def get_ticket_by_id(self, ticket_id: int, user_id: int = None):
        """Получает заявку с проверкой владельца"""
        if user_id:
            self.cursor.execute(
                """
            SELECT * FROM tickets 
            WHERE ticket_id = ? AND user_id = ?
            """,
                (ticket_id, user_id),
            )
        else:
            self.cursor.execute(
                """
            SELECT * FROM tickets 
            WHERE ticket_id = ?
            """,
                (ticket_id,),
            )

        return self.cursor.fetchone()

    def get_user_by_ticket(self, ticket_id: int):
        """Получает пользователя по ID заявки"""
        self.cursor.execute(
            """
        SELECT u.user_id FROM users u
        JOIN tickets t ON u.user_id = t.user_id
        WHERE t.ticket_id = ?
        """,
            (ticket_id,),
        )
        row = self.cursor.fetchone()
        return row["user_id"] if row else None

    def ticket_exists(self, ticket_id: int) -> bool:
        """Проверяет существование заявки"""
        self.cursor.execute("SELECT 1 FROM tickets WHERE ticket_id = ?", (ticket_id,))
        return self.cursor.fetchone() is not None

    # В класс Database добавляем:
    def is_admin(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь админом"""
        self.cursor.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result and result["is_admin"] == 1

    def add_admin(self, user_id: int):
        """Добавляет пользователя в админы"""
        self.cursor.execute(
            """
        INSERT OR REPLACE INTO users (user_id, is_admin)
        VALUES (?, TRUE)
        """,
            (user_id,),
        )
        self.conn.commit()

    def get_admins(self):
        """Возвращает список админов"""
        self.cursor.execute("SELECT user_id FROM users WHERE is_admin = TRUE")
        return [row["user_id"] for row in self.cursor.fetchall()]

    def sync_admins(self, admin_ids: list[int]):
        """Синхронизирует список админов с базой данных"""
        self.cursor.execute('UPDATE users SET is_admin = FALSE')

        for admin_id in admin_ids:
            self.cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, is_admin) 
            VALUES (?, TRUE)
            ''', (admin_id,))

        self.conn.commit()