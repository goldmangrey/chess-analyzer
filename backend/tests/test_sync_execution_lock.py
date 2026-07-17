from app.services.sync_execution_lock import SyncExecutionLock


def test_sqlite_process_lock_rejects_second_execution(test_engine):
    lock = SyncExecutionLock(test_engine)
    with lock.acquire() as first:
        with SyncExecutionLock(test_engine).acquire() as second:
            assert first is True and second is False
    with lock.acquire() as released:
        assert released is True


class FakeConnection:
    def __init__(self): self.statements = []; self.closed = False
    def execution_options(self, **_kwargs): return self
    def scalar(self, statement, params): self.statements.append((str(statement), params)); return True
    def execute(self, statement, params): self.statements.append((str(statement), params))
    def close(self): self.closed = True


class FakePostgresEngine:
    class Dialect: name = "postgresql"
    dialect = Dialect()
    def __init__(self): self.connection = FakeConnection()
    def connect(self): return self.connection


def test_postgresql_advisory_lock_released_on_same_connection():
    engine = FakePostgresEngine()
    with SyncExecutionLock(engine).acquire() as acquired:
        assert acquired is True
    sql = " ".join(item[0] for item in engine.connection.statements)
    assert "pg_try_advisory_lock" in sql and "pg_advisory_unlock" in sql
    assert engine.connection.closed is True
