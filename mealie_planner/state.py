from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any


class PlannerStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                create table if not exists plans (
                  plan_id text primary key,
                  parent_plan_id text,
                  status text not null,
                  request_json text not null,
                  draft_json text not null,
                  created_at text not null,
                  accepted_at text
                );
                create table if not exists feedback (
                  id integer primary key autoincrement,
                  plan_id text not null,
                  text text not null,
                  created_at text not null
                );
                create table if not exists mealie_entries (
                  plan_id text not null,
                  entry_id text not null,
                  date text not null,
                  recipe_id text not null,
                  primary key (plan_id, entry_id)
                );
                """
            )

    def save_plan(
        self,
        plan_id: str,
        *,
        request: dict[str, Any],
        draft: dict[str, Any],
        parent_plan_id: str | None = None,
        status: str = "draft_for_joe",
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            db.execute(
                """
                insert into plans (plan_id, parent_plan_id, status, request_json, draft_json, created_at)
                values (?, ?, ?, ?, ?, ?)
                """,
                (plan_id, parent_plan_id, status, json.dumps(request, default=str), json.dumps(draft, default=str), now),
            )

    def get_plan(self, plan_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute("select * from plans where plan_id = ?", (plan_id,)).fetchone()
        if row is None:
            raise KeyError(plan_id)
        result = dict(row)
        result["request"] = json.loads(result.pop("request_json"))
        result["draft"] = json.loads(result.pop("draft_json"))
        return result

    def record_feedback(self, plan_id: str, text: str) -> None:
        with self._connect() as db:
            db.execute(
                "insert into feedback (plan_id, text, created_at) values (?, ?, ?)",
                (plan_id, text, datetime.now(timezone.utc).isoformat()),
            )

    def list_feedback(self, plan_id: str) -> list[str]:
        with self._connect() as db:
            rows = db.execute("select text from feedback where plan_id = ? order by id", (plan_id,)).fetchall()
        return [str(row["text"]) for row in rows]

    def mark_accepted(self, plan_id: str, entries: list[dict[str, str]], *, status: str = "accepted") -> None:
        with self._connect() as db:
            db.execute(
                "update plans set status = ?, accepted_at = ? where plan_id = ?",
                (status, datetime.now(timezone.utc).isoformat(), plan_id),
            )
            for entry in entries:
                db.execute(
                    "insert or replace into mealie_entries (plan_id, entry_id, date, recipe_id) values (?, ?, ?, ?)",
                    (plan_id, entry["entry_id"], entry["date"], entry["recipe_id"]),
                )

    def mark_dismissed(self, plan_id: str) -> None:
        with self._connect() as db:
            db.execute("update plans set status = ? where plan_id = ?", ("dismissed", plan_id))

    def list_created_entries(self, plan_id: str) -> list[str]:
        with self._connect() as db:
            rows = db.execute("select entry_id from mealie_entries where plan_id = ?", (plan_id,)).fetchall()
        return [str(row["entry_id"]) for row in rows]

    def list_created_entries_for_family(self, plan_id: str) -> list[str]:
        plan_ids = self.plan_family(plan_id)
        if not plan_ids:
            return []
        placeholders = ",".join("?" for _ in plan_ids)
        with self._connect() as db:
            rows = db.execute(
                f"select entry_id from mealie_entries where plan_id in ({placeholders}) order by rowid",
                plan_ids,
            ).fetchall()
        return [str(row["entry_id"]) for row in rows]

    def plan_family(self, plan_id: str) -> list[str]:
        family: list[str] = []
        current: str | None = plan_id
        with self._connect() as db:
            while current:
                family.append(current)
                row = db.execute("select parent_plan_id from plans where plan_id = ?", (current,)).fetchone()
                if row is None:
                    break
                current = row["parent_plan_id"]
        return family
