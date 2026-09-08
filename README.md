# fedal-r2d2

FastAPI service hosting independent applications alongside reusable email, form,
authentication, and reCAPTCHA modules.

## Requirements

- Docker with Docker Compose, or Python 3.14 and `uv`
- PostgreSQL
- A Resend account and API key
- Google reCAPTCHA secret key

## Project layout

```text
src/
├── apps/
│   └── spanglish/       # Vocabulary, dictionary, quiz, and AI domain
├── modules/
│   ├── ai/              # Reusable provider-independent AI orchestration and usage
│   ├── email/           # Reusable Resend delivery and audit log
│   ├── forms/           # Reusable forms and submission audit log
│   └── recaptcha/       # Reusable reCAPTCHA verification
├── auth/                # Shared users and authentication data
├── core/                # Configuration and database infrastructure
├── alembic/             # Database migrations
└── main.py              # FastAPI composition root
```

New domain applications belong under `src/apps/<application>`. Reusable features
that can be consumed by more than one application belong under `src/modules`.

## Database schemas

One PostgreSQL database is shared, with ownership separated by schema:

| Schema | Data |
| --- | --- |
| `public` | Users, social providers, forms, form submission logs, email logs |
| `spanglish` | Languages, vocabulary, categories, chapters, translations and quizzes |
| `ai` | Shared AI prompt configurations and provider usage audits |

The Spanglish tables reference shared users through schema-qualified foreign keys.
Migration `b51d8c9a4f20` moves existing tables using PostgreSQL `ALTER TABLE ... SET
SCHEMA`, preserving existing data, indexes, and sequences.

Migration `c7d2e4f8a901` moves the existing AI tables from `spanglish` to the
shared `ai` schema without recreating them. PostgreSQL updates the existing
Spanglish example foreign key when its referenced table moves.

## Shared AI service

`src/modules/ai` is provider-independent infrastructure available to Spanglish,
forms, email, and future applications. Applications identify an `application`
and `feature`; the service loads the enabled prompt/model configuration, invokes
a registered provider adapter, and records tokens, cost, latency, and success or
failure in `ai.ai_usage`.

```mermaid
flowchart LR
    Spanglish[Spanglish prompts and learning rules] --> AIService[Shared AI service]
    Forms[Form summarization rules] --> AIService
    Email[Email drafting rules] --> AIService
    AIService --> Config[(ai.ai_agents)]
    AIService --> Adapter[Provider adapter protocol]
    Adapter --> Provider[OpenAI / Anthropic / other]
    AIService --> Usage[(ai.ai_usage)]
```

Provider API keys remain in environment configuration and are never stored in
the database. Provider adapters implement `AIProviderClient`; the shared service
does not import an OpenAI, Anthropic, or Google SDK directly. Domain prompts and
decisions remain in their consuming application rather than being embedded in
the shared module.

## Spanglish backend

Spanglish is a shared backend for terminal, desktop, web, and mobile interfaces.
The interfaces own presentation and local quiz progress. FastAPI owns vocabulary,
question selection, authoritative scoring, result history, and future AI advice.
Authentication is intentionally deferred; reference and vocabulary rows are global
until user identity is introduced.

```mermaid
flowchart LR
    CLI[CLI] --> API[Spanglish HTTP API]
    Desktop[Desktop cards UI] --> API
    Mobile[Mobile UI] --> API
    API --> Vocabulary[Vocabulary service]
    API --> Quiz[Batch quiz service]
    Quiz --> Evaluator[Deterministic answer evaluator]
    Quiz -. future .-> AI[AI advice provider]
    Vocabulary --> Repository[Spanglish repository]
    Quiz --> Repository
    Repository --> DB[(PostgreSQL spanglish schema)]
    API -. reusable later .-> Email[Email module]
    API -. reusable later .-> Forms[Forms module]
```

### Batch quiz lifecycle

The server does not track which question the user is currently viewing. It stores
an immutable quiz snapshot only so a final submission can be verified against the
exact questions that were sent.

```mermaid
sequenceDiagram
    participant Client as CLI / desktop / mobile
    participant API as FastAPI
    participant DB as PostgreSQL
    Client->>API: GET /api/v1/spanglish/quiz-options
    API-->>Client: Languages, categories, types and modes
    Client->>API: POST /api/v1/spanglish/quizzes
    API->>DB: Select vocabulary and save question snapshot
    API-->>Client: Complete quiz with questions and accepted answers
    Note over Client: Quiz runs completely locally
    Client->>API: POST /quizzes/{quiz_id}/results
    API->>API: Normalize and recalculate every answer
    API->>DB: Save attempts, score and advice
    API-->>Client: Score, evaluations and advice
```

The available endpoints are:

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/spanglish/quiz-options` | Build quiz selection menus and cards |
| `GET/POST` | `/api/v1/spanglish/languages` | List or create languages |
| `GET/POST` | `/api/v1/spanglish/categories` | List or create quiz categories |
| `GET/POST` | `/api/v1/spanglish/chapters` | List or create optional lesson chapters |
| `GET/POST` | `/api/v1/spanglish/vocabulary-types` | List or create content types |
| `GET/POST` | `/api/v1/spanglish/vocabulary` | Browse or create vocabulary cards |
| `GET` | `/api/v1/spanglish/vocabulary/{id}` | Fetch one complete vocabulary card |
| `PUT/DELETE` | `/api/v1/spanglish/vocabulary/{id}` | Replace or delete a vocabulary card |
| `GET/POST` | `/api/v1/spanglish/vocabulary/{id}/conjugations` | List or add verb forms |
| `PUT/DELETE` | `/api/v1/spanglish/vocabulary/{id}/conjugations/{conjugation_id}` | Replace or delete a verb form |
| `POST` | `/api/v1/spanglish/quizzes` | Generate and return a complete quiz |
| `POST` | `/api/v1/spanglish/quizzes/{id}/results` | Submit all answers and receive a score |

Quiz creation accepts source and target languages, zero or more category IDs,
zero or more chapter IDs, zero or more vocabulary type IDs, a question count,
`random` or `sequential`
selection, and translation/conjugation question types. An empty category list
means all categories, and an empty chapter list means all chapters (including
vocabulary without a chapter). If fewer matching questions exist, the API returns those
questions with a warning.

Accepted answers are deliberately included so clients can provide immediate local
feedback. The client does not submit or control correctness: the backend
normalizes and scores the submitted answers again. Current advice is deterministic
fallback guidance with `generated_by_ai: false`; an AI provider can later replace
it without changing the response contract.

### Managing verb conjugations

A verb is ordinary vocabulary, normally associated with the `Verb` category.
Conjugations may be included in the original `POST /vocabulary` request or
managed later through the nested conjugation endpoints. For example:

```http
POST /api/v1/spanglish/vocabulary/42/conjugations
Content-Type: application/json

{
  "tense": "present",
  "mood": "indicative",
  "pronoun": "yo",
  "form": "hablo"
}
```

The `(vocabulary_id, tense, mood, pronoun)` combination is unique. Creating or
updating a duplicate returns `409 Conflict`. Updating uses `PUT` and therefore
expects all four fields. Deleting a conjugation returns `204 No Content` and
does not delete the vocabulary item. A conjugation identifier cannot be used
under a different vocabulary identifier; that request returns `404 Not Found`.

Migration `8c4a1f2d9b70` evolves the existing Spanglish tables, seeds Spanish,
English, standard vocabulary types and categories, structures verb conjugations,
and adds batch quiz snapshots and results. It does not change the email, forms,
or reCAPTCHA tables.

When adding an application, give its SQLAlchemy models an explicit schema and add
a data-preserving Alembic migration that creates that schema.

## Configuration

Create `.env` with these variables:

```dotenv
DATABASE_URL=postgresql://user:password@host:5432/database
API_TOKEN=replace-me
JWT_SECRET_KEY=generate-a-long-random-value
JWT_ISSUER=fedal-r2d2
JWT_AUDIENCE=fedal-r2d2-api
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=30
RECAPTCHA_SECRET_KEY=replace-me
RESEND_API_KEY_ZAANSRECHT=re_replace-me
EMAIL_FROM_ZAANSRECHT=Zaansrecht <noreply@zaansrecht.nl>
EMAIL_TO_ZAANSRECHT=owner@example.com
```

Generate a development signing secret with `openssl rand -hex 32`. Access tokens
are short-lived JWTs; refresh tokens are opaque, stored only as SHA-256 hashes in
the database, rotated on refresh, and revocable on logout. Changing
`JWT_SECRET_KEY` invalidates every outstanding access token.

## Local authentication

Local authentication is available at `/api/v1/auth`:

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/register` | Create a user with an Argon2-hashed password |
| `POST` | `/login` | Obtain an access token and refresh token |
| `POST` | `/refresh` | Rotate a refresh token and obtain a new pair |
| `POST` | `/logout` | Revoke a refresh session |
| `GET` | `/me` | Return the authenticated user |

The access-token `sub` claim is the UUID in `public.users`. Clients never submit
a `user_id`; protected routes derive it from the bearer token. Quiz creation and
result submission require authentication, and result submission is scoped to the
quiz owner. Global languages, categories, vocabulary types, and vocabulary remain
readable without authentication.

Run the database migration before using authentication:

```bash
uv run alembic upgrade head
```

### CLI authentication test

The repository includes `scripts/r2d2_cli.py`, a dependency-free test client.
Start the API, then run:

```bash
python scripts/r2d2_cli.py register --username fedal --email fedal@example.com
python scripts/r2d2_cli.py login --email fedal@example.com
python scripts/r2d2_cli.py me
python scripts/r2d2_cli.py refresh
python scripts/r2d2_cli.py logout
```

Set `R2D2_API_URL` to use another API URL. The demonstration client stores tokens
in `~/.config/r2d2/tokens.json` with mode `0600`; a distributable CLI should use
the operating-system credential store instead. A later Keycloak integration can
map Keycloak's `(issuer, sub)` to the same local user without changing resource
ownership.

Each frontend selects a server-side email profile through the request's
`application` field. The identifier is converted to an uppercase environment
suffix. For example, `zaansrecht` uses `RESEND_API_KEY_ZAANSRECHT`,
`EMAIL_FROM_ZAANSRECHT`, and `EMAIL_TO_ZAANSRECHT`. Add another frontend by
configuring the same three variables with its uppercase identifier. Application
identifiers may contain lowercase letters, numbers, and underscores.

The frontend never sends the API key, sender, or recipient. `EMAIL_FROM_*` must
be a sender allowed by the corresponding Resend account.

Example request:

```http
POST /api/v1/email/send-email
Authorization: Bearer <API_TOKEN>
Content-Type: application/json

{
  "application": "zaansrecht",
  "reply_to": "visitor@example.com",
  "subject": "New contact request",
  "html": "<p>Hello from the contact form</p>"
}
```

The body may contain `html`, `text`, or both. At least one is required.

Email is submitted directly to Resend. There is no SMTP configuration and no
email-delivery cron job. Every attempt is stored in `public.email_logs` with its
application, provider message ID, status, and any provider error.

reCAPTCHA remains required for form submission. Full tokens are never logged or
stored; only a shortened audit representation is saved.

## Run with Docker

```bash
docker compose up -d postgres
make upgrade
docker compose up
```

The development Compose configuration rebuilds the API image when it starts, so
new dependencies from `pyproject.toml` and `uv.lock` are installed automatically.
The equivalent Make command is `make up`.

The development Compose stack includes PostgreSQL 18 with a persistent
`postgres_data` volume. The `.env` `DATABASE_URL` uses `localhost`, allowing
host-side Alembic commands such as `make upgrade` to connect to it. Inside
Compose, the API receives an override using the `postgres` service hostname.

To start only the database and apply migrations:

```bash
docker compose up -d postgres
make current
make upgrade
```

To remove the local database data as well as its container, run
`docker compose down --volumes`. This permanently deletes the development data.

## Production deployment

Successful pushes to `main` publish two images to GitHub Container Registry:

- `ghcr.io/fedal-nl/fedal-r2d2:latest`
- `ghcr.io/fedal-nl/fedal-r2d2:<commit-sha>`

Create `.env.prod` on the production host, then deploy the latest image:

```bash
make deploy
```

The deployment command stops the existing production stack, pulls the image,
and starts it in detached mode using `docker-compose.prod.yaml`. Production does
not mount source files and does not enable Uvicorn reload. The container still
listens on port 8000 internally, but production publishes it on
`127.0.0.1:8001` by default to avoid conflicts with other containers.

To use another host port:

```bash
API_HOST_PORT=8010 make deploy
```

Deploy a specific immutable image version with:

```bash
IMAGE_TAG=<commit-sha> make deploy
```

If the GHCR package is private, authenticate the production host once with a
GitHub token that has `read:packages` permission:

```bash
docker login ghcr.io
```

With the default production port, the API is available internally on the host at
<http://127.0.0.1:8001>, with interactive documentation at
<http://127.0.0.1:8001/docs>.

The container uses Python 3.14.

## Run locally

```bash
uv sync --python 3.14
uv run alembic upgrade head
uv run uvicorn src.main:app --reload
```

## Database migrations

Apply all migrations:

```bash
make upgrade
```

Generate a migration after changing models:

```bash
make migrate MESSAGE="describe the change"
```

Other commands include `make current`, `make history`,
`make downgrade REVISION=<revision>`, and `make stamp REVISION=<revision>`.

Back up production data before applying schema-changing migrations.

## Tests and linting

```bash
make test
make lint
```

Tests mock Resend and Google reCAPTCHA, so they do not send messages or make
external verification requests. The suite enforces at least 95% branch-aware
coverage and writes `coverage.xml` for the CI artifact.

Run `make` without arguments to list all available commands.

### Pre-commit checks

Install the Git hook once after syncing development dependencies:

```bash
uv sync --group dev
uv run pre-commit install
```

Each commit formats staged Python files with Black and then checks them with
Flake8. Mypy checks application code; tests and generated Alembic revisions are
excluded from static type checking. Run the same checks manually across the
repository with:

```bash
uv run pre-commit run --all-files
```

Black and Flake8 share an 88-character line limit. Generated Alembic revisions
are excluded from these formatting and type-checking hooks.

## API compatibility

All public business endpoints are explicitly composed in `src/api/v1/router.py`
and remain under `/api/v1`:

- `/api/v1/forms`
- `/api/v1/email`
- `/health`

Root and health endpoints are operational endpoints and are intentionally not
versioned. Spanglish, email, and forms endpoints are never exposed without an
API version prefix.

### Adding API v2

API versions protect HTTP contracts, not database tables. SQLAlchemy models,
repositories, and internal services may evolve as long as the v1 schemas and
behavior remain compatible. Do not edit a v1 request or response incompatibly
after clients depend on it.

To introduce a breaking contract, create a separate composition package:

```text
src/api/
├── v1/
│   └── router.py       # Frozen existing contracts
└── v2/
    ├── router.py       # /api/v2 composition
    └── schemas/        # v2-only request and response shapes when needed
```

Then register both routers in `src/main.py`:

```python
app.include_router(api_v1_router)
app.include_router(api_v2_router)
```

V2 can reuse the same services when only the HTTP representation changes. If
business behavior also changes, add a v2 service or strategy without changing
the implementation used by v1. Database migrations remain global and forward
moving; a new database schema is not required for every API version.

The deprecated cron email endpoint was removed because delivery now happens
through the Resend SDK as part of the email service flow.
