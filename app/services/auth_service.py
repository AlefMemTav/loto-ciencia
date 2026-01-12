# app/services/auth_service.py
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

DB_PATH = Path("data/users.db")
DB_PATH.parent.mkdir(exist_ok=True)


class AuthService:

    LIMITS = {"validator": 3, "generator": 1}

    def _get_conn(self):
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                plan TEXT DEFAULT 'free',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                upgraded_at TIMESTAMP,
                validator_last_used DATE,
                generator_last_used DATE,
                validator_count_today INTEGER DEFAULT 0,
                generator_count_today INTEGER DEFAULT 0
            )
        """
        )

        # Tabela Guest
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS guest_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                browser_id TEXT NOT NULL,
                resource TEXT NOT NULL,
                used_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(browser_id, resource, used_date)
            )
        """
        )

        # Usuário Demo
        try:
            demo_hash = hashlib.sha256("demo123".encode()).hexdigest()
            cursor.execute(
                "INSERT INTO users (email, password_hash, plan) VALUES (?, ?, ?)",
                ("demo@lotoscience.com", demo_hash, "pro"),
            )
            conn.commit()
        except:
            pass
        conn.close()

    def get_user_by_email(self, email: str) -> Optional[dict]:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None
        return dict(row)  # Converte sqlite Row para dict

    def create_user(self, email: str, password_hash: str) -> dict:
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (email, password_hash, plan) VALUES (?, ?, ?)",
                (email, password_hash, "free"),
            )
            conn.commit()
            return {
                "email": email,
                "plan": "free",
                "created_at": datetime.now().isoformat(),
            }
        finally:
            conn.close()

    def upgrade_user(self, email: str):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET plan = 'pro', upgraded_at = ? WHERE email = ?",
            (datetime.now().isoformat(), email),
        )
        conn.commit()
        conn.close()

    def check_usage(self, email: str, resource: str):
        user = self.get_user_by_email(email)
        if not user:
            return False

        # Se for PRO, libera tudo
        if user["plan"] == "pro":
            return True

        today = datetime.now().date().isoformat()
        last_used = user.get(f"{resource}_last_used")
        count_today = user.get(f"{resource}_count_today", 0)

        # Se a data for diferente de hoje, reseta mentalmente (liberado)
        if last_used != today:
            return True

        # Se for hoje, verifica se o contador é menor que o limite
        limit = self.LIMITS.get(resource, 1)
        return count_today < limit

    def get_usage_count(self, email: str, resource: str) -> int:
        """Retorna quantas vezes o recurso foi usado hoje"""
        conn = self._get_conn()
        cursor = conn.cursor()
        today = datetime.now().date().isoformat()

        cursor.execute(
            f"SELECT {resource}_last_used, {resource}_count_today FROM users WHERE email = ?",
            (email,),
        )
        row = cursor.fetchone()
        conn.close()

        if row and row[0] == today:
            return row[1]  # Retorna a contagem atual (ex: 1, 2...)

        return 0  # Se data diferente ou null, uso é 0

    def register_usage(self, email: str, resource: str):
        conn = self._get_conn()
        cursor = conn.cursor()

        # Busca estado atual para incrementar
        cursor.execute(
            f"SELECT {resource}_last_used, {resource}_count_today FROM users WHERE email = ?",
            (email,),
        )
        row = cursor.fetchone()

        today = datetime.now().date().isoformat()

        if row and row[0] == today:
            # Já usou hoje: Incrementa +1
            new_count = row[1] + 1
        else:
            # Primeiro uso do dia: Reseta para 1
            new_count = 1

        cursor.execute(
            f"UPDATE users SET {resource}_last_used = ?, {resource}_count_today = ? WHERE email = ?",
            (today, new_count, email),
        )
        conn.commit()
        conn.close()


# Singleton
auth_service = AuthService()
auth_service.init_db()
