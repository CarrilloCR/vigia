# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Vigía** is a multi-tenant SaaS platform for clinic KPI monitoring and intelligent alerting. It analyzes clinical metrics (cancellation rates, no-shows, revenue, NPS, etc.), detects anomalies against 30-day historical baselines, generates AI-powered recommendations via Claude API, and delivers grouped email alerts.

## Common Commands

### Development Startup
All three services must run simultaneously:
```bash
# Activate virtual environment (fish shell)
source env/bin/activate.fish

# Celery worker (background)
celery -A vigia_backend worker --loglevel=info

# Celery beat scheduler (background)
celery -A vigia_backend beat --loglevel=info

# Django dev server
python manage.py runserver
```

Or use `./start.sh` which detaches Celery processes to `/tmp/celery_worker.log` and `/tmp/celery_beat.log`.

### Database
```bash
python manage.py migrate
python manage.py makemigrations
python manage.py createsuperuser
```

### Tests
```bash
python manage.py test core
python manage.py test core.tests.TestClassName.test_method_name
```

### Celery Monitoring
```bash
celery -A vigia_backend inspect active
celery -A vigia_backend purge   # CAUTION: clears all pending tasks
```

## Architecture

### Single-App Structure
All business logic lives in `core/`. The `vigia_backend/` directory contains only project configuration (settings, urls, wsgi/asgi, celery).

### Key Files
| File | Purpose |
|------|---------|
| `core/models.py` | 15+ models for clinics, appointments, KPIs, alerts, notifications |
| `core/motor.py` | KPI analysis engine — calculates metrics, detects anomalies, calls Claude API |
| `core/tasks.py` | Celery tasks for async execution of motor and notifications |
| `core/generador.py` | Synthetic test data generation with configurable anomaly rates |
| `core/auth.py` | Custom JWT auth — registration, login, password validation |
| `core/views.py` | DRF ViewSets + custom action endpoints |
| `core/serializers.py` | DRF serializers |

### Multi-Tenant Data Model
Every entity is scoped to a `Clinica`. A clinic has one or more `Sede` (branches), `Medico` (doctors), `Paciente` (patients), and `Cita` (appointments). `Usuario` is separate from Django's `User` — Django `User` handles auth, `Usuario` carries the clinic-specific role (admin/viewer).

### Analytics Engine Flow (`motor.py`)
```
correr_motor(clinica_id)
  ├─ Calculate 8 KPI values from recent Cita/Encuesta records
  ├─ Compare against 30-day RegistroKPI history to detect anomalies
  ├─ Determine severity: baja / media / alta / critica
  ├─ For alta/critica: call Claude API (claude-sonnet-4-20250514) for 2-sentence recommendation
  ├─ Create Alerta records
  └─ Optionally trigger grouped email notification via Celery
```

The anomaly threshold defaults to 20% deviation from historical average. The `detectar_anomalia()` function returns `(is_anomaly, expected_value, deviation_percent)`.

### Celery Beat Schedule
A single recurring task runs every 5 minutes (`settings.py`):
- `generar_datos_falsos_task` — generates test appointments + KPIs for all clinics, then triggers motor analysis

### Notification System
Alerts from a single analysis run are batched into one email per recipient via SendGrid. `Notificacion` tracks delivery status (pendiente → enviada → entregada/leida/fallida). Additional email recipients per clinic are stored in `EmailNotificacion`.

### Status Workflows
- **Alerta**: active → revisada → resuelta (custom DRF actions: `marcar_revisada`, `marcar_resuelta`, `resolver_todas`)
- **Cita**: agendada → completada / cancelada / no_show / reagendada

## Infrastructure Prerequisites

- **PostgreSQL**: `vigia_user` / `vigia_pass_2024` @ `localhost:5432/vigia_db`
- **Redis**: `localhost:6379` (Celery broker and result backend)
- **Environment variables** in `.env`:
  - `ANTHROPIC_API_KEY` — for AI recommendations in `motor.py`
  - `SENDGRID_API_KEY` + `SENDGRID_FROM_EMAIL` — for email notifications

## API Overview

Base URL: `http://localhost:8000/api/`

**Auth:** `POST /api/auth/register/` creates a clinic + admin user in one transaction. All other endpoints require `Authorization: Bearer <access_token>`.

**Key custom endpoints:**
- `POST /api/motor/ejecutar/` — trigger KPI analysis for a clinic
- `POST /api/generador/ejecutar/` — generate synthetic test data for a clinic

The DRF router registers 14 standard ViewSets (clinicas, sedes, usuarios, medicos, pacientes, citas, kpis, alertas, notificaciones, configuraciones, integraciones, planes, emails-notificacion, feedback-alertas).
