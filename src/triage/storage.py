"""Small read-only Postgres boundary; Connect owns all result writes."""

import json
from collections.abc import Mapping, Sequence
from typing import Annotated, Any, Literal, Self

import psycopg
from psycopg.rows import dict_row
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, SecretStr

from triage.limits import MAX_TCP_PORT
from triage.reasoning import ReasonedEdit
from triage.schema import Contract

Decision = Literal["routine", "review", "insufficient_evidence"]


class DatabaseSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)
    host: str = Field(
        default="postgres", min_length=1, max_length=253, pattern=r"^[A-Za-z0-9_.-]+$"
    )
    port: int = Field(default=5432, ge=1, le=MAX_TCP_PORT)
    password: SecretStr = Field(default=SecretStr("local-reader-only"), repr=False)

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Self:
        return cls.model_validate(
            {
                "host": env.get("PGHOST", "postgres"),
                "port": env.get("PGPORT", "5432"),
                "password": env.get("PGPASSWORD", "local-reader-only"),
            }
        )


class ResultQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(default=20, ge=1, le=100)
    before_id: int | None = Field(default=None, ge=1, le=9_223_372_036_854_775_807)
    decision: Decision | None = None
    analysis_version: str | None = Field(default=None, min_length=1, max_length=512, pattern=r"\S")


class StoredResult(Contract):
    id: Annotated[int, Field(gt=0)]
    created_at: AwareDatetime
    updated_at: AwareDatetime
    source_url: str
    result: ReasonedEdit


class ResultSummary(Contract):
    id: int
    wiki: Literal["enwiki"]
    revision_id: int
    analysis_version: str
    title: str
    decision: Decision
    confidence: float
    explanation: str
    occurred_at: AwareDatetime
    created_at: AwareDatetime
    updated_at: AwareDatetime
    source_url: str


class ResultPage(Contract):
    items: tuple[ResultSummary, ...]
    next_before_id: int | None


class StorageUnavailable(Exception):
    """Do not expose credentials, SQL errors, or corrupt stored content to clients."""


class Store:
    def __init__(self, settings: DatabaseSettings) -> None:
        self.settings = settings

    def query(self, sql: str, params: Sequence[object] = ()) -> list[dict[str, Any]]:
        try:
            with psycopg.connect(
                host=self.settings.host,
                port=self.settings.port,
                dbname="triage",
                user="triage_reader",
                password=self.settings.password.get_secret_value(),
                sslmode="disable",
                connect_timeout=3,
                options=(
                    "-c default_transaction_read_only=on "
                    "-c statement_timeout=3000 -c lock_timeout=1000"
                ),
                autocommit=True,
                row_factory=dict_row,
            ) as connection:
                return connection.execute(sql, params).fetchall()
        except psycopg.Error:
            raise StorageUnavailable("storage unavailable") from None

    def ready(self) -> bool:
        # Verify both migration marker and actual table readability.
        self.query("SELECT id FROM triage_results LIMIT 0")
        return self.query("SELECT version FROM schema_migrations WHERE version = 2") == [
            {"version": 2}
        ]

    @staticmethod
    def stored(row: dict[str, Any]) -> StoredResult:
        try:
            result = ReasonedEdit.model_validate_json(json.dumps(row["payload"]))
            return StoredResult(
                id=row["id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                source_url=result.analysis.event.source_url,
                result=result,
            )
        except (ValueError, KeyError, TypeError, RecursionError):
            raise StorageUnavailable("stored result is invalid") from None

    def get(self, wiki: str, revision_id: int, analysis_version: str) -> StoredResult | None:
        rows = self.query(
            "SELECT id, payload, created_at, updated_at FROM triage_results "
            "WHERE wiki = %s AND revision_id = %s AND analysis_version = %s",
            (wiki, revision_id, analysis_version),
        )
        return self.stored(rows[0]) if rows else None

    def list(self, query: ResultQuery) -> ResultPage:
        rows = self.query(
            "SELECT id, payload, created_at, updated_at FROM triage_results "
            "WHERE (%s::text IS NULL OR decision = %s) "
            "AND (%s::bigint IS NULL OR id < %s) "
            "AND (%s::text IS NULL OR analysis_version = %s) "
            "ORDER BY id DESC LIMIT %s",
            (
                query.decision,
                query.decision,
                query.before_id,
                query.before_id,
                query.analysis_version,
                query.analysis_version,
                query.limit + 1,
            ),
        )
        stored = [self.stored(row) for row in rows[: query.limit]]
        items = []
        for row in stored:
            analysis = row.result.analysis
            items.append(
                ResultSummary(
                    id=row.id,
                    wiki=analysis.event.wiki,
                    revision_id=analysis.event.revision_id,
                    analysis_version=analysis.analysis_version,
                    title=analysis.event.title,
                    decision=analysis.decision,
                    confidence=analysis.confidence,
                    explanation=analysis.explanation,
                    occurred_at=analysis.event.occurred_at,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    source_url=row.source_url,
                )
            )
        return ResultPage(
            items=tuple(items), next_before_id=stored[-1].id if len(rows) > query.limit else None
        )
