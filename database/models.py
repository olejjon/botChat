from datetime import datetime
from sqlite3 import Row


class User:
    def __init__(self, row: Row):
        self.user_id = row["user_id"]
        self.first_name = row["first_name"]
        self.last_name = row["last_name"]
        self.company = row["company"]
        self.phone = row["phone"]
        self.market = row["market"]
        self.confirmed = bool(row["confirmed"])


class Ticket:
    def __init__(self, row: Row):
        self.ticket_id = row["ticket_id"]
        self.user_id = row["user_id"]
        self.created_at = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
        self.status = row["status"]
        self.last_updated = datetime.strptime(row["last_updated"], "%Y-%m-%d %H:%M:%S")
