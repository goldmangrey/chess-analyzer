# Chess AI Teacher

Локальное однопользовательское приложение для импорта партий Chess.com, анализа
каждого полухода нативным Stockfish и просмотра личной статистики. Данные хранятся
только на компьютере пользователя в `backend/data/chess.db`. Firebase, облачные
сервисы и AI/LLM API не используются.

## Требования

- macOS и Homebrew;
- Python 3.11+;
- Node.js 20+ и npm;
- нативный Stockfish.

## Установка Stockfish

```bash
brew install stockfish
which stockfish
stockfish
```

В открывшейся UCI-консоли проверьте движок и завершите его:

```text
uci
quit
```

## Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Проверьте в `backend/.env`:

```env
APP_ENV=development
CHESS_USERNAME=Yeskendir
CHESSCOM_USER_AGENT=ChessAITeacher/1.0 (contact: your-email@example.com)
STOCKFISH_PATH=/opt/homebrew/bin/stockfish
```

User-Agent должен содержать ваш корректный контакт. Для Intel Mac путь Stockfish
может отличаться; используйте результат `which stockfish`.

## Frontend setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
```

Frontend обращается к FastAPI напрямую:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

## Диагностика

Из корня проекта:

```bash
./scripts/check-local.sh
```

После запуска состояние системы доступно через
`GET http://127.0.0.1:8000/api/system/status`. Проверка не обращается к Chess.com
и не запускает процесс Stockfish.

## Запуск

Один терминал:

```bash
./scripts/dev.sh
```

Или два терминала:

```bash
cd backend
source .venv/bin/activate
python run.py
```

```bash
cd frontend
npm run dev
```

Адреса:

```text
Frontend: http://localhost:3000
Backend:  http://127.0.0.1:8000
Swagger:  http://127.0.0.1:8000/docs
```

## Первый сценарий

1. Откройте Dashboard.
2. Введите Chess.com username.
3. Импортируйте 5–10 партий.
4. Оставьте включённым «Сразу анализировать Stockfish».
5. Дождитесь завершения локального анализа.
6. Откройте «Партии».
7. Выберите партию для подробного разбора.

Анализ идёт через FastAPI `BackgroundTasks`. Он последовательный в пределах
процесса и прервётся при остановке backend. Страница открытой анализируемой
партии обновляется с ограниченным интервалом; бесконечного polling нет.

## REST API

- `GET /health` — лёгкая проверка без SQLite/Stockfish probe;
- `GET /api/system/status` — безопасная локальная диагностика;
- `POST /api/import/chess-com`;
- `GET /api/games`;
- `GET /api/games/{game_id}`;
- `GET /api/games/{game_id}/moves`;
- `POST /api/games/{game_id}/analyze`;
- `GET /api/stats/summary`;
- `GET /api/stats/trends`;
- `GET /api/stats/openings`;
- `GET /api/stats/performance`;
- `GET /api/stats/dashboard`.

## Интерфейс

- `/` — Dashboard и импорт Chess.com;
- `/games` — история с URL-фильтрами, backend-сортировкой и пагинацией;
- `/games/{id}` — read-only доска, все ply, лучшие ходы, PV, evaluation bar и timeline;
- `/components-preview` — workbench дизайн-системы.

Навигация по партии поддерживает стрелки, Home и End. Текстовые AI-объяснения
не реализованы: все оценки получены локально от Stockfish.

## Данные и сброс

Production-база создаётся при первом запуске в:

```text
backend/data/chess.db
```

Перед ручным сбросом сделайте резервную копию:

```bash
cp backend/data/chess.db backend/data/chess.backup.db
rm backend/data/chess.db
```

Удаление базы безвозвратно удаляет локальную историю, импорт и анализы. Скрипт
автоматического сброса намеренно не предоставляется.

## Проверки

```bash
cd backend
source .venv/bin/activate
pytest
python -m compileall app scripts
```

```bash
cd frontend
npm run lint
npx tsc --noEmit
npm run build
```

```bash
bash -n scripts/dev.sh
bash -n scripts/check-local.sh
```
