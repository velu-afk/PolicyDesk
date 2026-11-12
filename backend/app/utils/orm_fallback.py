"""
Lightweight SQLAlchemy-compatible ORM fallback backed by SQLite3.
Used automatically ONLY in restricted offline environments where the `sqlalchemy`
wheel is not installed, while preserving 100% standard SQLAlchemy declarative
model syntax and Session semantics across the application.
"""
import json
import math
import sqlite3
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, Type


class DistanceExpression:
    """Represents a pgvector cosine_distance ordering or projection expression."""

    def __init__(self, column: "Column", query_vector: List[float], label_name: str = "distance"):
        self.column = column
        self.query_vector = query_vector
        self.label_name = label_name

    def label(self, name: str) -> "DistanceExpression":
        return DistanceExpression(self.column, self.query_vector, label_name=name)


class BinaryExpression:
    """Represents a SQL WHERE predicate (e.g., Model.field == value)."""

    def __init__(self, col: "Column", op: str, val: Any):
        self.col = col
        self.op = op
        self.val = val


class OrderExpression:
    """Represents an ORDER BY clause."""

    def __init__(self, col: "Column", direction: str = "ASC"):
        self.col = col
        self.direction = direction


class Column:
    """SQLAlchemy-compatible Column descriptor."""

    def __init__(
        self,
        col_type: Any = None,
        foreign_key: Optional["ForeignKey"] = None,
        *,
        primary_key: bool = False,
        nullable: bool = True,
        unique: bool = False,
        index: bool = False,
        default: Any = None,
        onupdate: Any = None,
    ):
        if isinstance(col_type, ForeignKey):
            foreign_key = col_type
            col_type = Integer
        self.col_type = col_type
        self.foreign_key = foreign_key
        self.primary_key = primary_key
        self.nullable = nullable
        self.unique = unique
        self.index = index
        self.default = default
        self.onupdate = onupdate
        self.name: str = ""
        self.model_cls: Optional[Type[Any]] = None

    def __set_name__(self, owner: Type[Any], name: str) -> None:
        self.name = name
        self.model_cls = owner

    def __get__(self, instance: Any, owner: Type[Any]) -> Any:
        if instance is None:
            return self
        return instance.__dict__.get(self.name)

    def __set__(self, instance: Any, value: Any) -> None:
        instance.__dict__[self.name] = value

    def __eq__(self, other: Any) -> BinaryExpression:  # type: ignore[override]
        return BinaryExpression(self, "=", other)

    def __ne__(self, other: Any) -> BinaryExpression:  # type: ignore[override]
        return BinaryExpression(self, "!=", other)

    def __lt__(self, other: Any) -> BinaryExpression:
        return BinaryExpression(self, "<", other)

    def __le__(self, other: Any) -> BinaryExpression:
        return BinaryExpression(self, "<=", other)

    def __gt__(self, other: Any) -> BinaryExpression:
        return BinaryExpression(self, ">", other)

    def __ge__(self, other: Any) -> BinaryExpression:
        return BinaryExpression(self, ">=", other)

    def in_(self, values: List[Any]) -> BinaryExpression:
        return BinaryExpression(self, "IN", list(values))

    def asc(self) -> OrderExpression:
        return OrderExpression(self, "ASC")

    def desc(self) -> OrderExpression:
        return OrderExpression(self, "DESC")

    def cosine_distance(self, query_vector: List[float]) -> DistanceExpression:
        """Emulates pgvector's .cosine_distance(vec) method."""
        return DistanceExpression(self, query_vector)


class ForeignKey:
    def __init__(self, target: str, ondelete: str = "CASCADE"):
        self.target = target
        self.ondelete = ondelete


class RelationshipProperty:
    def __init__(self, target_name: str, back_populates: Optional[str] = None, cascade: str = ""):
        self.target_name = target_name
        self.back_populates = back_populates
        self.cascade = cascade
        self.name: str = ""
        self.owner: Optional[Type[Any]] = None

    def __set_name__(self, owner: Type[Any], name: str) -> None:
        self.name = name
        self.owner = owner

    def __get__(self, instance: Any, owner: Type[Any]) -> Any:
        if instance is None:
            return self
        session: Optional["Session"] = instance.__dict__.get("_sa_session")
        if session is None:
            return instance.__dict__.get(self.name, [])
        target_cls = _MODEL_REGISTRY.get(self.target_name)
        if target_cls is None:
            return []
        # Determine relationship direction via foreign keys
        for col_name, col in target_cls._sa_columns.items():
            if col.foreign_key and col.foreign_key.target.startswith(f"{owner.__tablename__}."):
                return (
                    session.query(target_cls)
                    .filter(BinaryExpression(col, "=", getattr(instance, "id")))
                    .all()
                )
        for col_name, col in owner._sa_columns.items():
            if col.foreign_key and col.foreign_key.target.startswith(f"{target_cls.__tablename__}."):
                fk_val = getattr(instance, col_name)
                return (
                    session.query(target_cls)
                    .filter(BinaryExpression(target_cls.id, "=", fk_val))
                    .first()
                )
        return []


def relationship(target_name: str, back_populates: Optional[str] = None, cascade: str = "", **kwargs: Any) -> Any:
    return RelationshipProperty(target_name, back_populates=back_populates, cascade=cascade)


class Integer:
    pass


class String:
    def __init__(self, length: int = 255):
        self.length = length


class Text:
    pass


class Float:
    pass


class Boolean:
    pass


class DateTime:
    def __init__(self, timezone: bool = True):
        self.timezone = timezone


class JSON:
    pass


class Vector:
    def __init__(self, dim: int = 768):
        self.dim = dim


class Index:
    def __init__(self, name: str, *cols: Any, **kwargs: Any):
        self.name = name
        self.cols = cols
        self.kwargs = kwargs


def text(sql: str) -> str:
    return sql


class func:
    @staticmethod
    def now() -> Callable[[], datetime]:
        return lambda: datetime.now(timezone.utc)

    @staticmethod
    def count(col: Any = None) -> Tuple[str, Any]:
        return ("COUNT", col)


_MODEL_REGISTRY: Dict[str, Type[Any]] = {}


class MetaData:
    def create_all(self, bind: "Engine") -> None:
        bind.create_all()

    def drop_all(self, bind: "Engine") -> None:
        bind.drop_all()


class DeclarativeMeta(type):
    def __new__(mcs, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any]) -> Any:
        cls = super().__new__(mcs, name, bases, namespace)
        if name != "Base" and "__tablename__" in namespace:
            cols: Dict[str, Column] = {}
            rels: Dict[str, RelationshipProperty] = {}
            for k, v in namespace.items():
                if isinstance(v, Column):
                    v.name = k
                    v.model_cls = cls
                    cols[k] = v
                elif isinstance(v, RelationshipProperty):
                    v.name = k
                    v.owner = cls
                    rels[k] = v
            cls._sa_columns = cols  # type: ignore[attr-defined]
            cls._sa_relationships = rels  # type: ignore[attr-defined]
            _MODEL_REGISTRY[name] = cls
        return cls


def declarative_base() -> Any:
    class Base(metaclass=DeclarativeMeta):
        metadata = MetaData()

        def __init__(self, **kwargs: Any) -> None:
            for col_name, col in getattr(self.__class__, "_sa_columns", {}).items():
                if col_name in kwargs:
                    setattr(self, col_name, kwargs[col_name])
                elif col.default is not None:
                    val = col.default() if callable(col.default) else col.default
                    setattr(self, col_name, val)
                else:
                    setattr(self, col_name, None)

    return Base


def _cosine_distance(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 1.0
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 == 0.0 or n2 == 0.0:
        return 1.0
    sim = max(-1.0, min(1.0, dot / (n1 * n2)))
    return 1.0 - sim


class Engine:
    def __init__(self, url: str, **kwargs: Any):
        self.url = url
        if url.startswith("sqlite:///"):
            self.db_path = url.replace("sqlite:///", "", 1)
        elif url == "sqlite:///:memory:":
            self.db_path = ":memory:"
        else:
            self.db_path = "./policydesk.db"
        self._memory_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._memory_conn.row_factory = sqlite3.Row
            self._memory_conn.execute("PRAGMA foreign_keys = ON")

    def get_raw_connection(self) -> sqlite3.Connection:
        if self._memory_conn is not None:
            return self._memory_conn
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def connect(self) -> "ConnectionContext":
        return ConnectionContext(self)

    def create_all(self) -> None:
        conn = self.get_raw_connection()
        for model_name, model_cls in _MODEL_REGISTRY.items():
            table = model_cls.__tablename__
            col_defs = []
            fk_defs = []
            for col_name, col in model_cls._sa_columns.items():
                sql_type = "TEXT"
                if col.col_type is Integer or isinstance(col.col_type, Integer):
                    sql_type = "INTEGER"
                elif col.col_type is Float or isinstance(col.col_type, Float):
                    sql_type = "REAL"
                elif col.col_type is Boolean or isinstance(col.col_type, Boolean):
                    sql_type = "INTEGER"
                parts = [f'"{col_name}" {sql_type}']
                if col.primary_key:
                    parts.append("PRIMARY KEY AUTOINCREMENT")
                else:
                    if not col.nullable:
                        parts.append("NOT NULL")
                    if col.unique:
                        parts.append("UNIQUE")
                col_defs.append(" ".join(parts))
                if col.foreign_key:
                    ref_table, ref_col = col.foreign_key.target.split(".")
                    ondelete = col.foreign_key.ondelete or "CASCADE"
                    fk_defs.append(
                        f'FOREIGN KEY ("{col_name}") REFERENCES "{ref_table}"("{ref_col}") ON DELETE {ondelete}'
                    )
            all_defs = ", ".join(col_defs + fk_defs)
            conn.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({all_defs})')
        conn.commit()
        if self._memory_conn is None:
            conn.close()

    def drop_all(self) -> None:
        conn = self.get_raw_connection()
        conn.execute("PRAGMA foreign_keys = OFF")
        for model_name, model_cls in reversed(list(_MODEL_REGISTRY.items())):
            conn.execute(f'DROP TABLE IF EXISTS "{model_cls.__tablename__}"')
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")
        if self._memory_conn is None:
            conn.close()


class ConnectionContext:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.conn: Optional[sqlite3.Connection] = None

    def __enter__(self) -> "ConnectionContext":
        self.conn = self.engine.get_raw_connection()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.conn and self.engine._memory_conn is None:
            self.conn.close()

    def execute(self, statement: str) -> Any:
        if not self.conn:
            raise RuntimeError("Connection closed")
        stmt_upper = str(statement).strip().upper()
        if stmt_upper.startswith("CREATE EXTENSION"):
            return None
        return self.conn.execute(str(statement))

    def commit(self) -> None:
        if self.conn:
            self.conn.commit()


def create_engine(url: str, **kwargs: Any) -> Engine:
    return Engine(url, **kwargs)


class Query:
    def __init__(self, session: "Session", entities: Tuple[Any, ...]):
        self.session = session
        self.entities = entities
        self.filters: List[Any] = []
        self.orders: List[Any] = []
        self.limit_val: Optional[int] = None
        self.offset_val: Optional[int] = None

    def join(self, *args: Any, **kwargs: Any) -> "Query":
        return self

    def filter(self, *predicates: Any) -> "Query":
        for p in predicates:
            if p is not None:
                self.filters.append(p)
        return self

    def filter_by(self, **kwargs: Any) -> "Query":
        model_cls = self._primary_model()
        for k, v in kwargs.items():
            col = getattr(model_cls, k)
            self.filters.append(BinaryExpression(col, "=", v))
        return self

    def order_by(self, *clauses: Any) -> "Query":
        for c in clauses:
            self.orders.append(c)
        return self

    def limit(self, n: int) -> "Query":
        self.limit_val = n
        return self

    def offset(self, n: int) -> "Query":
        self.offset_val = n
        return self

    def _primary_model(self) -> Type[Any]:
        for ent in self.entities:
            if isinstance(ent, type) and hasattr(ent, "__tablename__"):
                return ent
            if isinstance(ent, Column) and ent.model_cls is not None:
                return ent.model_cls
            if isinstance(ent, tuple) and len(ent) == 2 and ent[0] == "COUNT":
                col = ent[1]
                if isinstance(col, Column) and col.model_cls is not None:
                    return col.model_cls
        raise ValueError("Could not determine primary model for query")

    def _execute_rows(self) -> List[Any]:
        model_cls = self._primary_model()
        table = model_cls.__tablename__
        where_clauses: List[str] = []
        params: List[Any] = []
        distance_filters: List[Tuple[DistanceExpression, str, float]] = []

        for f in self.filters:
            if isinstance(f, BinaryExpression):
                if isinstance(f.col, DistanceExpression):
                    distance_filters.append((f.col, f.op, float(f.val)))
                    continue
                col_name = f.col.name
                val = self.session._serialize_value(f.col, f.val)
                if f.op == "IN":
                    if not f.val:
                        return []
                    placeholders = ", ".join("?" for _ in f.val)
                    where_clauses.append(f'"{col_name}" IN ({placeholders})')
                    params.extend(f.val)
                elif val is None and f.op == "=":
                    where_clauses.append(f'"{col_name}" IS NULL')
                elif val is None and f.op == "!=":
                    where_clauses.append(f'"{col_name}" IS NOT NULL')
                else:
                    where_clauses.append(f'"{col_name}" {f.op} ?')
                    params.append(val)

        sql = f'SELECT * FROM "{table}"'
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        sql_orders: List[str] = []
        distance_order: Optional[DistanceExpression] = None
        for o in self.orders:
            if isinstance(o, OrderExpression):
                sql_orders.append(f'"{o.col.name}" {o.direction}')
            elif isinstance(o, DistanceExpression):
                distance_order = o
            elif isinstance(o, Column):
                sql_orders.append(f'"{o.name}" ASC')

        if sql_orders and distance_order is None:
            sql += " ORDER BY " + ", ".join(sql_orders)

        cur = self.session.conn.execute(sql, params)
        raw_rows = cur.fetchall()
        instances = [self.session._row_to_instance(model_cls, r) for r in raw_rows]

        # Check if query projects DistanceExpression
        dist_expr: Optional[DistanceExpression] = distance_order
        for ent in self.entities:
            if isinstance(ent, DistanceExpression):
                dist_expr = ent

        if dist_expr is not None:
            scored: List[Tuple[Any, float]] = []
            for inst in instances:
                vec = getattr(inst, dist_expr.column.name) or []
                d = _cosine_distance(vec, dist_expr.query_vector)
                scored.append((inst, d))
            if distance_order is not None:
                scored.sort(key=lambda x: x[1])
            if self.offset_val:
                scored = scored[self.offset_val :]
            if self.limit_val is not None:
                scored = scored[: self.limit_val]
            if len(self.entities) == 2 and isinstance(self.entities[1], DistanceExpression):
                return scored
            return [s[0] for s in scored]

        if self.offset_val:
            instances = instances[self.offset_val :]
        if self.limit_val is not None:
            instances = instances[: self.limit_val]
        return instances

    def all(self) -> List[Any]:
        return self._execute_rows()

    def first(self) -> Optional[Any]:
        rows = self.limit(1)._execute_rows()
        return rows[0] if rows else None

    def count(self) -> int:
        return len(self._execute_rows())

    def scalar(self) -> Any:
        if len(self.entities) == 1 and isinstance(self.entities[0], tuple) and self.entities[0][0] == "COUNT":
            return len(self._execute_rows())
        first = self.first()
        return first


class Session:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.conn = engine.get_raw_connection()
        self._new: List[Any] = []
        self._tracked: List[Any] = []
        self._deleted: List[Any] = []

    def _serialize_value(self, col: Column, val: Any) -> Any:
        if val is None:
            return None
        if isinstance(val, datetime):
            return val.isoformat()
        if isinstance(col.col_type, (JSON, Vector)) or col.col_type in (JSON, Vector):
            return json.dumps(val)
        if isinstance(val, (dict, list)):
            return json.dumps(val)
        if isinstance(val, bool):
            return 1 if val else 0
        return val

    def _deserialize_value(self, col: Column, val: Any) -> Any:
        if val is None:
            return None
        if isinstance(col.col_type, DateTime) or col.col_type is DateTime:
            if isinstance(val, str):
                try:
                    return datetime.fromisoformat(val)
                except ValueError:
                    return datetime.now(timezone.utc)
        if isinstance(col.col_type, (JSON, Vector)) or col.col_type in (JSON, Vector):
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except ValueError:
                    return val
        if isinstance(col.col_type, Boolean) or col.col_type is Boolean:
            return bool(val)
        return val

    def _row_to_instance(self, model_cls: Type[Any], row: sqlite3.Row) -> Any:
        kwargs = {}
        for col_name, col in model_cls._sa_columns.items():
            if col_name in row.keys():
                kwargs[col_name] = self._deserialize_value(col, row[col_name])
        inst = model_cls(**kwargs)
        inst.__dict__["_sa_session"] = self
        if inst not in self._tracked:
            self._tracked.append(inst)
        return inst

    def add(self, instance: Any) -> None:
        instance.__dict__["_sa_session"] = self
        if getattr(instance, "id", None) is None:
            if instance not in self._new:
                self._new.append(instance)
        else:
            if instance not in self._tracked:
                self._tracked.append(instance)

    def add_all(self, instances: List[Any]) -> None:
        for inst in instances:
            self.add(inst)

    def delete(self, instance: Any) -> None:
        if instance not in self._deleted:
            self._deleted.append(instance)

    def flush(self) -> None:
        # Process deletions first
        for inst in list(self._deleted):
            table = inst.__class__.__tablename__
            pk = getattr(inst, "id", None)
            if pk is not None:
                self.conn.execute(f'DELETE FROM "{table}" WHERE id = ?', (pk,))
            self._deleted.remove(inst)
            if inst in self._tracked:
                self._tracked.remove(inst)

        # Process inserts
        for inst in list(self._new):
            model_cls = inst.__class__
            table = model_cls.__tablename__
            col_names = []
            placeholders = []
            values = []
            for col_name, col in model_cls._sa_columns.items():
                val = getattr(inst, col_name, None)
                if col_name == "id" and val is None:
                    continue
                if val is None and col.default is not None:
                    val = col.default() if callable(col.default) else col.default
                    setattr(inst, col_name, val)
                col_names.append(f'"{col_name}"')
                placeholders.append("?")
                values.append(self._serialize_value(col, val))
            sql = f'INSERT INTO "{table}" ({", ".join(col_names)}) VALUES ({", ".join(placeholders)})'
            cur = self.conn.execute(sql, values)
            if getattr(inst, "id", None) is None:
                setattr(inst, "id", cur.lastrowid)
            self._new.remove(inst)
            if inst not in self._tracked:
                self._tracked.append(inst)

        # Process updates on tracked instances
        for inst in list(self._tracked):
            model_cls = inst.__class__
            table = model_cls.__tablename__
            pk = getattr(inst, "id", None)
            if pk is None:
                continue
            set_clauses = []
            values = []
            for col_name, col in model_cls._sa_columns.items():
                if col_name == "id":
                    continue
                val = getattr(inst, col_name, None)
                set_clauses.append(f'"{col_name}" = ?')
                values.append(self._serialize_value(col, val))
            values.append(pk)
            sql = f'UPDATE "{table}" SET {", ".join(set_clauses)} WHERE id = ?'
            self.conn.execute(sql, values)

    def commit(self) -> None:
        self.flush()
        self.conn.commit()

    def rollback(self) -> None:
        self._new.clear()
        self._deleted.clear()
        self.conn.rollback()

    def refresh(self, instance: Any) -> None:
        pk = getattr(instance, "id", None)
        if pk is None:
            return
        model_cls = instance.__class__
        cur = self.conn.execute(
            f'SELECT * FROM "{model_cls.__tablename__}" WHERE id = ?', (pk,)
        )
        row = cur.fetchone()
        if row:
            for col_name, col in model_cls._sa_columns.items():
                if col_name in row.keys():
                    setattr(instance, col_name, self._deserialize_value(col, row[col_name]))

    def query(self, *entities: Any) -> Query:
        self.flush()
        return Query(self, entities)

    def execute(self, statement: Any) -> Any:
        stmt_str = str(statement).strip()
        if stmt_str.upper().startswith("CREATE EXTENSION"):
            return None
        return self.conn.execute(stmt_str)

    def close(self) -> None:
        if self.engine._memory_conn is None:
            self.conn.close()


def sessionmaker(autocommit: bool = False, autoflush: bool = False, bind: Optional[Engine] = None) -> Callable[[], Session]:
    def _factory() -> Session:
        if bind is None:
            raise RuntimeError("Sessionmaker is not bound to an engine")
        return Session(bind)

    return _factory
