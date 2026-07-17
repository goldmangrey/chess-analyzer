import pytest

from app.models import AnalysisStatus, Color, Game, GameResult
from app.queues.errors import PermanentAnalysisTaskError
from app.services.analysis_queue_service import mark_enqueue_failed, reserve_analysis


def game(status=AnalysisStatus.PENDING):
    return Game(external_id=f"queue-{status.value}", white_username="User", black_username="Opponent", user_color=Color.WHITE, result=GameResult.WIN, pgn="1. e4", analysis_status=status)


@pytest.mark.parametrize("status", [AnalysisStatus.PENDING, AnalysisStatus.FAILED])
def test_reserve_pending_or_failed(db_session, status):
    item = game(status); db_session.add(item); db_session.commit()
    result = reserve_analysis(db_session, item.id)
    assert result.status == "queued" and item.analysis_status is AnalysisStatus.ANALYZING


def test_completed_force_and_restore(db_session):
    item = game(AnalysisStatus.COMPLETED); db_session.add(item); db_session.commit()
    assert reserve_analysis(db_session, item.id).status == "already_completed"
    reserved = reserve_analysis(db_session, item.id, force=True)
    assert reserved.status == "queued"
    mark_enqueue_failed(db_session, item.id, reserved.previous_status)
    assert item.analysis_status is AnalysisStatus.COMPLETED


def test_analyzing_and_missing(db_session):
    item = game(AnalysisStatus.ANALYZING); db_session.add(item); db_session.commit()
    assert reserve_analysis(db_session, item.id).status == "already_analyzing"
    with pytest.raises(PermanentAnalysisTaskError):
        reserve_analysis(db_session, 9999)
