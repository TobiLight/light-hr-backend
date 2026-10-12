# Light HRMS Backend

## Overview

Organizations often struggle to coordinate personnel workflows and employee lifecycle records when their internal tooling is fragmented across different services. Light HRMS Backend provides a unified server foundation that tracks personnel activity, processes domain events, and exposes dependable operations for company systems. It gives teams a structured, predictable backbone for managing day-to-day organizational operations without unnecessary overhead.

## Architecture

```mermaid
flowchart LR
  Client["Web Dashboard"]
  API["API Router"]
  Core["Application Core"]
  Database[("Database")]

  Client -- "HTTP Requests" --> API
  API --> Core
  Core --> Database

  style Client fill:#1e1b4b,stroke:#6366f1,stroke-width:2px,color:#fff
  style API fill:#2e1065,stroke:#8b5cf6,stroke-width:2px,color:#fff
  style Core fill:#1f2937,stroke:#6b7280,stroke-width:2px,color:#fff
  style Database fill:#0f172a,stroke:#3b82f6,stroke-width:2px,color:#fff
```

## Features

- **Layered Clean Architecture**: Strict separation of concerns between domain rules, presentation endpoints, and infrastructure adapters to keep business logic isolated and maintainable.
- **Production-Ready Health Checks**: Distinct liveness and readiness endpoints designed to work out of the box with orchestrators and load balancers.

```mermaid
sequenceDiagram
  actor Monitor as "Monitoring System"
  participant Health as "Health Route"
  participant App as "Application State"

  Monitor->>Health: GET /api/v1/health/live
  Health->>App: Check process state
  App-->>Health: Process running
  Health-->>Monitor: 200 OK
```

- **Event-Driven Domain Foundation**: Decoupled domain event contracts stamped with UTC timestamps and unique identifiers to simplify auditing and state updates.

```mermaid
flowchart LR
  Action["Personnel Action"]
  Event["Domain Event"]
  Handler["Event Dispatcher"]

  Action -- "Triggers" --> Event
  Event -- "Publishes" --> Handler

  style Action fill:#1f2937,stroke:#6b7280,stroke-width:2px,color:#fff
  style Event fill:#2e1065,stroke:#8b5cf6,stroke-width:2px,color:#fff
  style Handler fill:#1e1b4b,stroke:#6366f1,stroke-width:2px,color:#fff
```

- **Structured JSON Logging**: Standardized JSON-formatted log streams that attach log levels, UTC timestamps, and contextual data for streamlined telemetry.
- **Environment-Driven Configuration**: Centralized settings backed by strict schema validation to catch configuration mistakes before the application boots.

## Technologies Used

| Technology | Purpose | Documentation |
| :--- | :--- | :--- |
| Python 3.13 | Core programming language | [python.org](https://www.python.org/) |
| FastAPI | Web framework and routing | [fastapi.tiangolo.com](https://fastapi.tiangolo.com/) |
| Uvicorn | ASGI web server implementation | [uvicorn.org](https://www.uvicorn.org/) |
| Pydantic Settings | Environment configuration and validation | [docs.pydantic.dev](https://docs.pydantic.dev/) |
| Structlog | Structured logging processor | [structlog.org](https://www.structlog.org/) |
| SQLAlchemy | Asynchronous persistence mappings and engine setup | [sqlalchemy.org](https://www.sqlalchemy.org/) |
| PyTest | Automated testing framework | [pytest.org](https://docs.pytest.org/) |
| Ruff | Linting and code formatting | [docs.astral.sh/ruff](https://docs.astral.sh/ruff/) |

## Environment Variables

The application reads configuration values directly from the host environment or a local `.env` file located at the project root.

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `APP_NAME` | string | `LIGHT_HRMS BACKEND ` | Application identifier used in logs and API metadata. |
| `APP_ENV` | string | `dev` | Current deployment stage (`dev`, `test`, `staging`, `production`). |
| `DEBUG` | boolean | `false` | Enables verbose error handling and development tooling. |
| `API_V1_PREFIX` | string | `/api/v1` | URL prefix prepended to all version 1 endpoints. |
| `DATABASE_URL` | string | `postgresql+asyncpg://app:app@localhost:5432/app` | Asynchronous database connection string. |
| `LOG_LEVEL` | string | `INFO` | Minimum severity level for structured logger output. Accepts `CRITICAL`, `DEBUG`, `ERROR`, `FATAL`, `INFO`, `NOTSET`, `WARN`, or `WARNING`, case-insensitive. An unrecognized value fails at startup. |

### Setting Environment Variables at the System Level

Windows (PowerShell):
```powershell
setx APP_ENV "production"
```

macOS / Linux:
```bash
echo 'export APP_ENV="production"' >> ~/.bashrc
source ~/.bashrc
```

## Installation

### Prerequisites

- Python 3.13 or newer
- `pip` or `uv` package manager

### Steps

1. Clone the repository:
```bash
git clone git@github.com:TobiLight/light-hr-backend.git
cd light-hr-backend
```

2. Install [uv](https://docs.astral.sh/uv/) and sync the project:

`uv sync` is the only supported install path. The project declares no
`[build-system]`, so `pip install -e .` cannot work.

```bash
uv sync
```

This creates `.venv/` and installs runtime and development dependencies
(including the test runner). Run subsequent commands through `uv run ...` or
activate the environment with `source .venv/bin/activate`.

3. Configure your environment file:
```bash
cp .env.example .env
```

If an example file isn't present, create a `.env` file containing:
```env
APP_NAME=LIGHT_HRMS BACKEND
APP_ENV=dev
DEBUG=True
API_V1_PREFIX=/api/v1
DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/app
LOG_LEVEL=INFO
```

## Usage

### Running the Development Server

Start the application with live reload enabled using the entry script:
```bash
python start.py
```

Alternatively, launch the server directly using Uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
```text
http://localhost:8000
```

Interactive OpenAPI documentation will be accessible at:
```text
http://localhost:8000/docs
```

### Running Tests

Execute the test suite using PyTest:
```bash
pytest
```

Run code quality and style checks using Ruff:
```bash
ruff check .
```

## API Documentation

All routes listed below are prefixed with `/api/v1`.

### Health Endpoints

#### GET /api/v1/health/live

**Description**: Liveness probe that confirms the server process is alive and accepting traffic. Does not query downstream services.

**Authentication**: None required

**Request**:
```text
GET /api/v1/health/live HTTP/1.1
Host: localhost:8000
```

**Response**:
```json
{
  "status": "ok"
}
```

**Errors**:
- 500: Process state is unrecoverable or an internal runtime error occurred.

---

#### GET /api/v1/health/ready

**Description**: Readiness probe that indicates whether the application is fully initialized and prepared to handle requests.

**Authentication**: None required

**Request**:
```text
GET /api/v1/health/ready HTTP/1.1
Host: localhost:8000
```

**Response**:
```json
{
  "status": "ok"
}
```

**Errors**:
- 503: Service is temporarily unable to handle incoming requests.

## Contributing

Contributions, issue reports, and suggestions are welcome.

1. Fork the repository.
2. Create a feature branch:
```bash
git checkout -b feature/your-feature-name
```
3. Commit your changes with descriptive commit messages.
4. Push your branch to your remote fork:
```bash
git push origin feature/your-feature-name
```
5. Open a Pull Request detailing the changes you made and any testing conducted.

## Author Info

- Oluwatobiloba Light Agunloye
- X (Twitter): https://x.com/0xTobii

---

[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![PyTest](https://img.shields.io/badge/PyTest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Ruff](https://img.shields.io/badge/Ruff-D7FF64?style=for-the-badge&logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)

[![Readme was generated by Dokugen](https://img.shields.io/badge/Readme%20was%20generated%20by-Dokugen-brightgreen)](https://dokugen.samueltuoyo.com)