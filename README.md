# Chess AI Teacher

Локальное однопользовательское приложение для синхронизации партий Chess.com, анализа
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

### Database backends and migrations

SQLite остаётся default для локальной разработки:

```env
DATABASE_URL=sqlite:///./data/chess.db
AUTO_CREATE_SCHEMA=true
```

Новая SQLite база может также быть создана миграцией:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

Существующую `backend/data/chess.db`, ранее созданную через `create_all()`, нельзя
накатывать initial migration поверх таблиц. Сначала сделайте backup, затем dry-run
и только после успешной проверки stamp:

```bash
cp data/chess.db data/chess.backup.db
python scripts/adopt_existing_database.py
python scripts/adopt_existing_database.py --apply
```

Stamp добавляет только Alembic revision и не переносит/не изменяет игровые данные.

PostgreSQL поддерживается опционально через синхронный psycopg 3:

```bash
brew install postgresql@17
brew services start postgresql@17
```

```sql
CREATE USER chess_user WITH PASSWORD 'change-me';
CREATE DATABASE chess_ai_teacher OWNER chess_user;
```

```bash
cd backend
source .venv/bin/activate
cp .env.postgresql.example .env
alembic upgrade head
python run.py
```

Production-конфигурация использует:

```env
DATABASE_URL=postgresql+psycopg://chess_user:change-me@127.0.0.1:5432/chess_ai_teacher
AUTO_CREATE_SCHEMA=false
```

Специальные символы в password должны быть URL-encoded. PostgreSQL migration
создаёт только schema и не копирует данные из SQLite; перенос данных, если он
понадобится, будет отдельным этапом. Startup не запускает `alembic upgrade`
автоматически.

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

Указывайте только origin без завершающего `/api`: API routes уже содержат
префикс `/api`.

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
3. Выберите период и загрузите историю — она появится без ожидания Stockfish.
4. При желании оставьте включённым отчёт для самой свежей новой партии.
5. Нажимайте «Получить отчёт» только для нужных партий.
6. Кнопка «Обновить партии» загрузит новые завершённые партии без повторного username.
7. Откройте «Партии» и выберите готовый отчёт.

Пока Dashboard открыт, client-driven sync проверяет новые партии каждые три
минуты и прекращается при закрытии вкладки. На будущем cloud-этапе его заменит
Cloud Scheduler/Jobs. Старые партии автоматически не анализируются: Stockfish
запускается только по запросу или для одной самой свежей новой партии.

Анализ идёт через FastAPI `BackgroundTasks`. Он последовательный в пределах
процесса и прервётся при остановке backend. Страница открытой анализируемой
партии обновляется с ограниченным интервалом; бесконечного polling нет.

## REST API

- `GET /health` — лёгкая проверка без SQLite/Stockfish probe;
- `GET /api/system/status` — безопасная локальная диагностика;
- `GET /api/settings` и `PATCH /api/settings`;
- `POST /api/sync/chess-com` — основной sync flow;
- `POST /api/import/chess-com` — legacy/internal совместимость, без анализа по умолчанию;
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
