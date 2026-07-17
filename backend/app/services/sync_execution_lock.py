from contextlib import contextmanager
import threading

from sqlalchemy import Engine, text


SYNC_ADVISORY_LOCK_NAMESPACE = 0x43485359
SYNC_ADVISORY_LOCK_KEY = 1
_process_lock = threading.Lock()


class SyncExecutionLock:
    """Cross-instance PostgreSQL advisory lock plus local process guard."""

    def __init__(self, engine: Engine):
        self.engine = engine

    @contextmanager
    def acquire(self):
        if not _process_lock.acquire(blocking=False):
            yield False
            return
        connection = None
        acquired = False
        try:
            if self.engine.dialect.name == "postgresql":
                connection = self.engine.connect().execution_options(isolation_level="AUTOCOMMIT")
                acquired = bool(connection.scalar(
                    text("SELECT pg_try_advisory_lock(:namespace, :lock_key)"),
                    {"namespace": SYNC_ADVISORY_LOCK_NAMESPACE, "lock_key": SYNC_ADVISORY_LOCK_KEY},
                ))
            else:
                acquired = True
            yield acquired
        finally:
            if connection is not None:
                if acquired:
                    connection.execute(
                        text("SELECT pg_advisory_unlock(:namespace, :lock_key)"),
                        {"namespace": SYNC_ADVISORY_LOCK_NAMESPACE, "lock_key": SYNC_ADVISORY_LOCK_KEY},
                    )
                connection.close()
            _process_lock.release()
