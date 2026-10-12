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
Spanglish resources are scoped to the authenticated user. Languages, categories,
chapters, artists, vocabulary, and quiz sessions are ownership roots. Songs and
other dependent records derive their owner through their artist, vocabulary, or
quiz session. The initial references are copied from the first account when a
new account first requests its options.

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
| `GET/POST` | `/api/v1/spanglish/artists` | List or create user-owned artists |
| `GET/POST` | `/api/v1/spanglish/songs` | List or create user-owned songs; GET accepts `artist_id` |
| `GET/POST` | `/api/v1/spanglish/vocabulary` | Browse or create vocabulary cards |
| `GET` | `/api/v1/spanglish/vocabulary/{id}` | Fetch one complete vocabulary card |
| `PUT/DELETE` | `/api/v1/spanglish/vocabulary/{id}` | Replace or delete a vocabulary card |
| `GET/POST` | `/api/v1/spanglish/vocabulary/{id}/conjugations` | List or add verb forms |
| `PUT/DELETE` | `/api/v1/spanglish/vocabulary/{id}/conjugations/{conjugation_id}` | Replace or delete a verb form |
| `POST` | `/api/v1/spanglish/quizzes` | Generate and return a complete quiz |
| `POST` | `/api/v1/spanglish/quizzes/{id}/results` | Submit all answers and receive a score |

When creating vocabulary in the `Songs` category, include a `song_id` from the
authenticated user's song list. Create an artist first with `POST /artists`
(`{"name": "Artist"}`), then a title with `POST /songs`
(`{"title": "Song title", "artist_id": 1}`). Omit `song_id` for all
other categories. Cross-user artist, song, vocabulary, and quiz IDs return 404.
Apply migrations through `e84f6a1c2b90` before using the new endpoints.

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
English, standard categories, structures verb conjugations,
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
PASSWORD_RESET_MINUTES=15
RECAPTCHA_SECRET_KEY=replace-me
RESEND_API_KEY_ZAANSRECHT=re_replace-me
EMAIL_FROM_ZAANSRECHT=Zaansrecht <noreply@zaansrecht.nl>
EMAIL_TO_ZAANSRECHT=owner@example.com
RESEND_API_KEY_SPANGLISH=re_replace-me
EMAIL_FROM_SPANGLISH=Spanglish <noreply@example.com>
EMAIL_TO_SPANGLISH=owner@example.com
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
| `POST` | `/password-reset/request` | Email a short-lived reset token |
| `POST` | `/password-reset/confirm` | Set a new password and revoke sessions |
| `GET` | `/me` | Return the authenticated user |

The access-token `sub` claim is the UUID in `public.users`. Clients never submit
a `user_id`; protected routes derive it from the bearer token. Quiz creation and
result submission require authentication, and result submission is scoped to the
quiz owner. Global languages, categories, and vocabulary remain
readable without authentication.

Creating vocabulary requires authentication. The API derives `user_id` from the
bearer token rather than accepting it from the client, and vocabulary uniqueness
is scoped to `(text, language_id, user_id)`.

Password-reset requests always return the same accepted response, whether or
not the email is registered. Tokens expire after `PASSWORD_RESET_MINUTES`, are
invalid after the password changes, and confirmation revokes all refresh
sessions. Delivery uses the `spanglish` Resend profile.

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

## Email service

The email API provides application-specific transactional delivery through
[Resend](https://resend.com). It is suitable for contact forms, notifications,
confirmations, and other messages where each customer needs an isolated sender,
recipient, API key, and HTML design.

### Features

- Separate Resend configuration for every customer or application.
- Server-controlled sender addresses, fixed-recipient delivery for forms, and
  application-token-protected dynamic recipients for trusted backend APIs.
- HTML, plain text, or multipart-style requests containing both versions.
- Customer-owned HTML templates: render the template in the customer
  application and submit the resulting HTML.
- A validated `Reply-To` address, allowing the configured recipient to reply
  directly to the person who submitted a form.
- Direct delivery through the Resend SDK without SMTP or a delivery cron job.
- A database audit record for every attempt, including its status, Resend
  message ID, error, application, sender, recipient, subject, and body.
- Status and history endpoints for operational inspection.

### Customer onboarding

1. Choose a lowercase application identifier. It must start with a letter and
   may contain lowercase letters, numbers, and underscores, for example
   `acme`, `customer_portal`, or `website2`.
2. Create or select a Resend account and verify the sending domain in Resend.
3. Create a Resend API key with permission to send from that domain.
4. Add the customer's profile to the API environment. The application
   identifier is converted to an uppercase suffix:

   ```dotenv
   RESEND_API_KEY_ACME=re_customer_api_key
   EMAIL_FROM_ACME=Acme Website <noreply@mail.acme.example>
   EMAIL_TO_ACME=contact@acme.example
   ```

5. Restart or redeploy the API after changing its environment.
6. Give the customer's trusted backend the email API URL, its application
   identifier, and the shared `API_TOKEN` using a secure secret channel.

`EMAIL_FROM_*` must use a sender accepted by the corresponding Resend account.
`EMAIL_TO_*` is the fixed destination for that customer. Resend credentials,
`API_TOKEN`, sender, and recipient must never be embedded in browser JavaScript
or another public client. A website should call this endpoint from its backend
or server-side function.

The unsuffixed variables `RESEND_API_KEY`, `EMAIL_FROM`, and `EMAIL_TO` are used
only when the application identifier is `general`.

For an API such as AI Central Hub that sends transactional email to its own
registered users, configure an application-specific bearer token and omit the
fixed recipient:

```dotenv
AICENTRALHUB_TOKEN=generate-with-openssl-rand-hex-32
RESEND_API_KEY_AICENTRALHUB=re_customer_api_key
EMAIL_FROM_AICENTRALHUB=AI Central Hub <noreply@mail.aicentralhub.example>
```

### Using a custom template

The public endpoint accepts rendered content; it does not accept a template
filename or template variables. This keeps the customer's template lifecycle
independent from the API. Render the customer's template in their application,
then send the completed HTML in the `html` property. User-provided values must
be HTML-escaped by that renderer.

For example, a customer can render the following template before calling the
API:

```html
<!doctype html>
<html lang="en">
  <body>
    <h1>New website enquiry</h1>
    <p><strong>Name:</strong> {{ escaped_name }}</p>
    <p><strong>Message:</strong></p>
    <p>{{ escaped_message }}</p>
  </body>
</html>
```

Applications implemented inside this repository can alternatively store Jinja
templates below `src` and render them with `EmailTemplateRenderer`. The bundled
renderer supports template inheritance and automatically escapes HTML/XML
values. Rendering is an application concern; the email endpoint still receives
the resulting HTML.

### Send an email

```http
POST /api/v1/email/send-email
Authorization: Bearer <API_TOKEN>
Content-Type: application/json

{
  "application": "acme",
  "reply_to": "visitor@example.com",
  "subject": "New website enquiry",
  "html": "<h1>New website enquiry</h1><p>Hello from the contact form.</p>",
  "text": "New website enquiry\n\nHello from the contact form."
}
```

Equivalent `curl` request:

```bash
curl --request POST "https://api.example.com/api/v1/email/send-email" \
  --header "Authorization: Bearer ${API_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{
    "application": "acme",
    "reply_to": "visitor@example.com",
    "subject": "New website enquiry",
    "html": "<h1>New website enquiry</h1><p>Hello from the contact form.</p>",
    "text": "New website enquiry\n\nHello from the contact form."
  }'
```

The body may contain `html`, `text`, or both; at least one non-empty body is
required. `reply_to` must be a valid email address, and `subject` is required.

A successful API call returns the audit-log identifier and delivery result:

```json
{
  "id": 123,
  "status": "SENT"
}
```

If Resend rejects delivery, the request is still recorded and the response has
status `FAILED`. The provider error is stored in the email log for diagnostics.
A missing customer profile returns `400`, invalid request data returns `422`,
and a missing or incorrect bearer token returns `401`.

### Send to a registered application user

Trusted backend APIs use the dynamic-recipient endpoint. The application name
selects both `{APPLICATION}_TOKEN` and the matching Resend profile; a token for
one application cannot authenticate another application's request.

```bash
curl --request POST "http://localhost:8000/api/v1/email/send-user-email" \
  --header "Authorization: Bearer ${AICENTRALHUB_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{
    "application": "aicentralhub",
    "to": "registered-user@example.com",
    "reply_to": "support@aicentralhub.example",
    "subject": "Your AI Central Hub notification",
    "html": "<h1>Your notification</h1><p>Rendered customer HTML.</p>",
    "text": "Your AI Central Hub notification"
  }'
```

The caller must render the complete HTML before sending it. The email API
validates `to` and `reply_to`, authenticates with `AICENTRALHUB_TOKEN`, and then
uses `RESEND_API_KEY_AICENTRALHUB` and `EMAIL_FROM_AICENTRALHUB`. It does not
require `EMAIL_TO_AICENTRALHUB` because the authenticated backend supplies the
registered user's address.

### Delivery and audit endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/email/send-email` | Send rendered HTML/text using an application profile |
| `POST` | `/api/v1/email/send-user-email` | Send to a dynamic recipient using an application token |
| `GET` | `/api/v1/email/email-status/{email_id}` | Read one audit record's current status |
| `GET` | `/api/v1/email/sent-emails?status=SENT` | List records filtered by delivery status |
| `GET` | `/api/v1/email/all-emails` | List all email audit records |

The send endpoint requires `Authorization: Bearer <API_TOKEN>`. In API v1, the
three read endpoints do not require that token. Their records may contain
message content and personal data, so restrict them with private networking or
an authenticated API gateway and never expose them through a public frontend.

Every delivery attempt is stored in `public.email_logs`. The states used by the
service include `SENDING`, `SENT`, and `FAILED`; successful records also contain
the Resend message ID.

### Production checklist

- Verify the customer's sending domain in Resend.
- Store all API keys and tokens in the deployment's secret manager.
- Use a different Resend API key for each customer where possible.
- Keep `EMAIL_TO_*` and `EMAIL_FROM_*` under server control.
- Render and HTML-escape all customer-supplied template values.
- Send both HTML and text bodies for better email-client compatibility.
- Monitor failed audit records and API logs.
- Do not log or expose the bearer token.

## Form security

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
runs `alembic upgrade head` from that image, and then starts it in detached mode
using `docker-compose.prod.yaml`. If migration fails, Make stops and does not
start the API with an incompatible database schema. Production does not mount
source files and does not enable Uvicorn reload. The container still listens on
port 8000 internally, but production publishes it on `127.0.0.1:8001` by default
to avoid conflicts with other containers.

To apply production migrations without restarting the API, run:

```bash
make prod-upgrade
```

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
