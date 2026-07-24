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
| `spanglish` | Languages, vocabulary, categories, chapters, translations, quizzes, AI agents and usage |

The Spanglish tables reference shared users through schema-qualified foreign keys.
Migration `b51d8c9a4f20` moves existing tables using PostgreSQL `ALTER TABLE ... SET
SCHEMA`, preserving existing data, indexes, and sequences.

When adding an application, give its SQLAlchemy models an explicit schema and add
a data-preserving Alembic migration that creates that schema.

## Configuration

Create `.env` with these variables:

```dotenv
DATABASE_URL=postgresql://user:password@host:5432/database
API_TOKEN=replace-me
RECAPTCHA_SECRET_KEY=replace-me
RESEND_API_KEY_ZAANSRECHT=re_replace-me
EMAIL_FROM_ZAANSRECHT=Zaansrecht <noreply@zaansrecht.nl>
EMAIL_TO_ZAANSRECHT=owner@example.com
```

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

## API compatibility

Existing shared routes remain under `/api/v1`:

- `/api/v1/forms`
- `/api/v1/email`
- `/health`

The deprecated cron email endpoint was removed because delivery now happens
through the Resend SDK as part of the email service flow.
