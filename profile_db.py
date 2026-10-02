from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

# 必备字段（人名、时间、地点）直接是 people 表的列，不属于“自定义字段”，
# 因此既不能被删除，也不允许用同名标签再建一个自定义字段。
CORE_FIELD_LABELS = {
    "人物名称", "人物姓名", "姓名", "名称",
    "出生时间", "时间", "本地时间", "时区", "UTC 时区",
    "纬度", "经度", "地点", "出生地点",
}

MAX_LABEL_LEN = 40
MAX_VALUE_LEN = 20000


class ProfileDB:
    """人物档案库。

    表结构：
      people          必备字段：名称、出生时间、时区、纬度、经度（+ 创建/更新时间）
      profile_fields  自定义字段的“定义”（字段名、是否多行）
      profile_values  每个人在每个自定义字段上的“取值”

    增加字段 = 在 profile_fields 里加一行，所有档案立刻拥有该字段（值为空）。
    删除字段 = 删掉 profile_fields 里的那一行，profile_values 里所有人的这一项
    由外键 ON DELETE CASCADE 一并删除，不需要逐个档案处理。
    """

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    # ------------------------------------------------------------------ 连接

    def _connect(self):
        conn = sqlite3.connect(
            self.path,
            timeout=5.0,
            isolation_level=None,  # 自动提交模式；需要事务时手动 BEGIN/COMMIT
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = DELETE")
        conn.execute("PRAGMA synchronous = NORMAL")
        return conn

    @contextmanager
    def _read(self):
        conn = self._connect()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def _tx(self):
        """写事务：成功则提交，任何异常则整体回滚，并保证连接被关闭。"""
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            else:
                conn.execute("COMMIT")
        finally:
            conn.close()

    # ------------------------------------------------------------ 建表 / 迁移

    _PEOPLE_DDL = """
        CREATE TABLE {name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            display_name TEXT NOT NULL,
            birth_time TEXT NOT NULL,
            timezone_offset TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """

    def _init_db(self):
        legacy_notes = self._read_legacy_notes()
        if legacy_notes is not None:
            self._backup_before_migration()

        with self._tx() as conn:
            if legacy_notes is not None:
                # 旧版 people 表带有固定的 note 列：重建为只含必备字段的新表。
                # 此时 profile_values 还不存在，所以 DROP 旧表不会触发级联删除。
                conn.execute(self._PEOPLE_DDL.format(name="people_new"))
                conn.execute(
                    """
                    INSERT INTO people_new (
                        id, display_name, birth_time, timezone_offset,
                        latitude, longitude, created_at, updated_at
                    )
                    SELECT id, display_name, birth_time, timezone_offset,
                           latitude, longitude, created_at, updated_at
                    FROM people
                    """
                )
                conn.execute("DROP TABLE people")
                conn.execute("ALTER TABLE people_new RENAME TO people")

            conn.execute(
                self._PEOPLE_DDL.format(name="IF NOT EXISTS people")
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_people_display_name
                ON people(display_name COLLATE NOCASE)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS profile_fields (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label TEXT NOT NULL,
                    multiline INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_profile_fields_label
                ON profile_fields(label COLLATE NOCASE)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS profile_values (
                    profile_id INTEGER NOT NULL
                        REFERENCES people(id) ON DELETE CASCADE,
                    field_id INTEGER NOT NULL
                        REFERENCES profile_fields(id) ON DELETE CASCADE,
                    value TEXT NOT NULL,
                    PRIMARY KEY (profile_id, field_id)
                )
                """
            )

            if legacy_notes is not None:
                # 把原来的“备注”变成第一个自定义字段（多行），并迁移已有内容。
                cursor = conn.execute(
                    "INSERT INTO profile_fields (label, multiline, created_at) "
                    "VALUES (?, 1, ?)",
                    ("备注", self._now()),
                )
                field_id = int(cursor.lastrowid)
                for profile_id, note in legacy_notes:
                    if note and str(note).strip():
                        conn.execute(
                            "INSERT INTO profile_values (profile_id, field_id, value) "
                            "VALUES (?, ?, ?)",
                            (profile_id, field_id, str(note)),
                        )

    def _read_legacy_notes(self):
        """旧结构（people 表里有 note 列）返回 [(id, note), ...]；否则返回 None。"""
        with self._read() as conn:
            columns = [row["name"] for row in conn.execute("PRAGMA table_info(people)")]
            if "note" not in columns:
                return None
            rows = conn.execute("SELECT id, note FROM people").fetchall()
            return [(int(row["id"]), row["note"]) for row in rows]

    def _backup_before_migration(self):
        """迁移前把整库另存一份，放在同一个 user_data 目录里。"""
        backup = self.path.with_name(self.path.name + ".before-fields.bak")
        if backup.exists():
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = self.path.with_name(f"{self.path.name}.before-fields.{stamp}.bak")
        source = sqlite3.connect(self.path)
        target = sqlite3.connect(backup)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()

    # --------------------------------------------------------------- 小工具

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _validate(data):
        display_name = str(data.get("display_name", "")).strip()
        birth_time = str(data.get("birth_time", "")).strip()
        timezone_offset = str(data.get("timezone_offset", "")).strip()

        if not display_name:
            raise ValueError("人物名称不能为空。")
        if not birth_time:
            raise ValueError("出生时间不能为空。")
        if not timezone_offset:
            raise ValueError("时区不能为空。")

        try:
            latitude = float(data.get("latitude"))
            longitude = float(data.get("longitude"))
        except (TypeError, ValueError):
            raise ValueError("经纬度必须是数字。")

        if not -90 <= latitude <= 90:
            raise ValueError("纬度必须位于 -90 到 90 之间。")
        if not -180 <= longitude <= 180:
            raise ValueError("经度必须位于 -180 到 180 之间。")

        return {
            "display_name": display_name,
            "birth_time": birth_time,
            "timezone_offset": timezone_offset,
            "latitude": latitude,
            "longitude": longitude,
        }

    @staticmethod
    def _clean_label(label):
        label = " ".join(str(label or "").split())
        if not label:
            raise ValueError("字段名不能为空。")
        if len(label) > MAX_LABEL_LEN:
            raise ValueError(f"字段名不能超过 {MAX_LABEL_LEN} 个字符。")
        if label in CORE_FIELD_LABELS:
            raise ValueError(f"「{label}」是必备字段，不能当作自定义字段名。")
        return label

    @staticmethod
    def _clean_field_values(conn, raw):
        """把前端传来的 {字段id: 值} 整理成 {int: str}；未知字段 id（例如刚在别处被删）直接忽略。"""
        if not raw:
            return {}
        known = {int(r["id"]) for r in conn.execute("SELECT id FROM profile_fields")}
        clean = {}
        for key, value in dict(raw).items():
            try:
                field_id = int(key)
            except (TypeError, ValueError):
                continue
            if field_id not in known:
                continue
            text = "" if value is None else str(value)
            if len(text) > MAX_VALUE_LEN:
                raise ValueError(f"单个字段的内容不能超过 {MAX_VALUE_LEN} 个字符。")
            clean[field_id] = text
        return clean

    @staticmethod
    def _write_field_values(conn, profile_id, values):
        for field_id, text in values.items():
            if text.strip() == "":
                conn.execute(
                    "DELETE FROM profile_values WHERE profile_id = ? AND field_id = ?",
                    (profile_id, field_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO profile_values (profile_id, field_id, value)
                    VALUES (?, ?, ?)
                    ON CONFLICT(profile_id, field_id) DO UPDATE SET value = excluded.value
                    """,
                    (profile_id, field_id, text),
                )

    # ------------------------------------------------------------ 自定义字段

    def list_fields(self):
        with self._read() as conn:
            rows = conn.execute(
                """
                SELECT f.id, f.label, f.multiline,
                       COUNT(v.profile_id) AS used_count
                FROM profile_fields AS f
                LEFT JOIN profile_values AS v ON v.field_id = f.id
                GROUP BY f.id
                ORDER BY f.id
                """
            ).fetchall()
        return [
            {
                "id": int(r["id"]),
                "label": r["label"],
                "multiline": bool(r["multiline"]),
                "used_count": int(r["used_count"]),
            }
            for r in rows
        ]

    def _get_field(self, field_id):
        for item in self.list_fields():
            if item["id"] == int(field_id):
                return item
        return None

    def create_field(self, label, multiline=False):
        label = self._clean_label(label)
        try:
            with self._tx() as conn:
                cursor = conn.execute(
                    "INSERT INTO profile_fields (label, multiline, created_at) "
                    "VALUES (?, ?, ?)",
                    (label, 1 if multiline else 0, self._now()),
                )
                field_id = int(cursor.lastrowid)
        except sqlite3.IntegrityError:
            raise ValueError(f"已经有名为「{label}」的字段了。")
        return self._get_field(field_id)

    def update_field(self, field_id, data):
        current = self._get_field(field_id)
        if current is None:
            return None
        label = self._clean_label(data["label"]) if "label" in data else current["label"]
        multiline = bool(data["multiline"]) if "multiline" in data else current["multiline"]
        try:
            with self._tx() as conn:
                conn.execute(
                    "UPDATE profile_fields SET label = ?, multiline = ? WHERE id = ?",
                    (label, 1 if multiline else 0, int(field_id)),
                )
        except sqlite3.IntegrityError:
            raise ValueError(f"已经有名为「{label}」的字段了。")
        return self._get_field(field_id)

    def delete_field(self, field_id):
        """删除字段，并（通过外键级联）删除所有档案里这个字段的数据。"""
        with self._tx() as conn:
            cursor = conn.execute(
                "DELETE FROM profile_fields WHERE id = ?", (int(field_id),)
            )
        return cursor.rowcount > 0

    # ------------------------------------------------------------------ 档案

    @staticmethod
    def _assemble(people_rows, value_rows):
        values = {}
        for r in value_rows:
            values.setdefault(int(r["profile_id"]), {})[str(int(r["field_id"]))] = r["value"]
        result = []
        for row in people_rows:
            item = dict(row)
            item["fields"] = values.get(int(item["id"]), {})
            result.append(item)
        return result

    def list_profiles(self):
        with self._read() as conn:
            people = conn.execute(
                """
                SELECT id, display_name, birth_time, timezone_offset,
                       latitude, longitude, created_at, updated_at
                FROM people
                ORDER BY display_name COLLATE NOCASE, id
                """
            ).fetchall()
            values = conn.execute(
                "SELECT profile_id, field_id, value FROM profile_values"
            ).fetchall()
        return self._assemble(people, values)

    def get_profile(self, profile_id):
        with self._read() as conn:
            people = conn.execute(
                "SELECT * FROM people WHERE id = ?", (int(profile_id),)
            ).fetchall()
            values = conn.execute(
                "SELECT profile_id, field_id, value FROM profile_values WHERE profile_id = ?",
                (int(profile_id),),
            ).fetchall()
        items = self._assemble(people, values)
        return items[0] if items else None

    def create_profile(self, data):
        clean = self._validate(data)
        now = self._now()
        with self._tx() as conn:
            field_values = self._clean_field_values(conn, data.get("fields"))
            cursor = conn.execute(
                """
                INSERT INTO people (
                    display_name, birth_time, timezone_offset,
                    latitude, longitude, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    clean["display_name"],
                    clean["birth_time"],
                    clean["timezone_offset"],
                    clean["latitude"],
                    clean["longitude"],
                    now,
                    now,
                ),
            )
            profile_id = int(cursor.lastrowid)
            self._write_field_values(conn, profile_id, field_values)
        return self.get_profile(profile_id)

    def update_profile(self, profile_id, data):
        """覆盖保存：必备字段整体覆盖；请求里带了的自定义字段覆盖，没带的保持不变。"""
        if self.get_profile(profile_id) is None:
            return None

        clean = self._validate(data)
        with self._tx() as conn:
            field_values = self._clean_field_values(conn, data.get("fields"))
            conn.execute(
                """
                UPDATE people
                SET display_name = ?,
                    birth_time = ?,
                    timezone_offset = ?,
                    latitude = ?,
                    longitude = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    clean["display_name"],
                    clean["birth_time"],
                    clean["timezone_offset"],
                    clean["latitude"],
                    clean["longitude"],
                    self._now(),
                    int(profile_id),
                ),
            )
            self._write_field_values(conn, int(profile_id), field_values)
        return self.get_profile(profile_id)

    def delete_profile(self, profile_id):
        with self._tx() as conn:
            cursor = conn.execute(
                "DELETE FROM people WHERE id = ?",
                (int(profile_id),),
            )
        return cursor.rowcount > 0
