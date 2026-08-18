cd ~/chess-ai-teacher/frontend

rm -rf .next
rm -rf node_modules

npm ci
npm run dev

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

## Очередь анализа

Локальный режим по умолчанию использует FastAPI `BackgroundTasks` только как
адаптер очереди:

```env
ANALYSIS_QUEUE_BACKEND=local
```

Cloud Tasks режим настраивается через `ANALYSIS_QUEUE_BACKEND=cloud_tasks`,
`GCP_PROJECT_ID`, `GCP_REGION`, `CLOUD_TASKS_QUEUE`, `ANALYSIS_WORKER_URL` и
`CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL`. Поток выполнения: API → Cloud Tasks →
`POST /internal/tasks/analyze-game` → Stockfish → PostgreSQL. Одна task всегда
соответствует одной партии; worker идемпотентен, а повторная доставка безопасна.
Приложение не создаёт Cloud Tasks queue автоматически. Queue и production
OIDC/IAM deployment будут настроены на следующем этапе.

Рекомендуемые параметры queue: 5 попыток, backoff 10–300 секунд, 1–2
одновременных dispatch и 1 dispatch/second. Локальная задача прервётся при
остановке backend. Страница открытой анализируемой партии обновляется с
ограниченным интервалом; бесконечного polling нет.

## Google Cloud deployment

Production foundation uses a public Next.js Cloud Run frontend, a public API,
a separate private worker running the same backend image, Cloud Tasks with OIDC,
Cloud SQL PostgreSQL, Secret Manager, Artifact Registry, and an Alembic Cloud Run
Job. The worker image contains Stockfish and one task analyzes one game. Cloud
SQL persists data independently of Cloud Run restarts.

Exact dry-run-first provisioning and cleanup commands are in
[`docs/deployment/google-cloud.md`](docs/deployment/google-cloud.md). No GCP
resource is created by application startup. В production новые завершённые
партии обнаруживает Cloud Scheduler: private sync service выполняет incremental
polling каждые 3–5 минут и при необходимости ставит только одну latest game в
Cloud Tasks. Manual refresh остаётся доступным, а local development сохраняет
browser-driven fallback. Chess.com webhook не используется.

Cloud SQL создаёт постоянный платный ресурс. Low-cost shared-core tier
`db-f1-micro` требует `CLOUD_SQL_EDITION=enterprise`; более дорогой Enterprise
Plus по умолчанию не используется. Сначала запускайте `deploy-all.sh` без
`--apply` и проверяйте dry-run. Tier и edition можно переопределить через env;
явно экспортированные переменные имеют приоритет над `deploy/gcp.env`, а файл —
над безопасными defaults.

Единственный рекомендуемый production entrypoint:

```bash
cp deploy/gcp.env.example deploy/gcp.env
# заполнить ignored env без secrets
./scripts/gcp/production-deploy.sh --preflight
./scripts/gcp/production-deploy.sh --apply
```

Orchestrator сам вычисляет полные Artifact Registry image references, получает
Cloud Run URLs, обновляет CORS и сохраняет resume state в ignored
`deploy/.deployment-state`. Старые отдельные GCP scripts считаются внутренними
implementation details. При ошибке deployment можно продолжить через
`--resume-from STEP`; существующие secrets не ротируются без явного
`ROTATE_SECRETS=true`.

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
