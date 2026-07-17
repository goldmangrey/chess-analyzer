from fastapi import BackgroundTasks
from sqlalchemy.orm import sessionmaker

from app.models import AnalysisStatus, Color, Game, GameResult
from app.queues.local import LocalAnalysisQueue


def test_local_queue_reserves_and_adds_one_task(test_engine):
    factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    session = factory(); item = Game(external_id="local-q", white_username="U", black_username="O", user_color=Color.WHITE, result=GameResult.WIN, pgn="1. e4"); session.add(item); session.commit(); game_id=item.id; session.close()
    tasks = BackgroundTasks()
    queue = LocalAnalysisQueue(tasks, lambda: object(), session_factory=factory)
    result = queue.enqueue_game_analysis(game_id=game_id)
    assert result.status == "queued" and len(tasks.tasks) == 1
    check=factory(); assert check.get(Game, game_id).analysis_status is AnalysisStatus.ANALYZING; check.close()


def test_local_duplicate_is_not_added(test_engine):
    factory=sessionmaker(bind=test_engine, expire_on_commit=False); s=factory(); item=Game(external_id="busy-q", white_username="U", black_username="O", user_color=Color.WHITE, result=GameResult.WIN, pgn="1. e4", analysis_status=AnalysisStatus.ANALYZING); s.add(item); s.commit(); game_id=item.id; s.close()
    tasks=BackgroundTasks(); result=LocalAnalysisQueue(tasks, lambda: object(), session_factory=factory).enqueue_game_analysis(game_id=game_id)
    assert result.status == "already_analyzing" and tasks.tasks == []
