# Credit Approval System

A Django REST Framework backend for automated credit approval — built for the **Alemeno Backend Internship Assignment**.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 4.2 + Django REST Framework |
| Database | PostgreSQL 15 |
| Task Queue | Celery + Redis |
| Containerisation | Docker + Docker Compose |
| Language | Python 3.11 |

---

## Project Structure

```
credit_approval/
├── credit_system/          # Django project (settings, urls, celery)
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py
├── customers/              # Customer app
│   ├── models.py           # Customer model
│   ├── views.py            # /register endpoint
│   ├── serializers.py
│   ├── tasks.py            # Celery: ingest customer_data.xlsx
│   └── management/
│       └── commands/
│           └── ingest_data.py
├── loans/                  # Loans app
│   ├── models.py           # Loan model
│   ├── views.py            # /check-eligibility, /create-loan, /view-loan, /view-loans
│   ├── serializers.py
│   ├── credit_service.py   # Credit scoring + EMI calculation logic
│   └── tasks.py            # Celery: ingest loan_data.xlsx
├── data/
│   ├── customer_data.xlsx
│   └── loan_data.xlsx
├── tests.py                # Unit + API tests (15 test cases)
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── entrypoint.sh
```

---

## Quick Start (Docker)

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) ≥ 24
- [Docker Compose](https://docs.docker.com/compose/) ≥ 2.x

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd credit_approval
```

### 2. Run the entire application

```bash
docker compose up --build
```

This single command will:
1. Start **PostgreSQL** and **Redis**
2. Run **Django migrations**
3. Dispatch **background Celery tasks** to ingest `customer_data.xlsx` and `loan_data.xlsx`
4. Start the **Django web server** on `http://localhost:8000`
5. Start the **Celery worker** to process the ingestion tasks

> ⏱️ Data ingestion typically completes within 10–30 seconds after startup. Watch the `celery` container logs for progress.

### 3. Verify it's working

```bash
curl http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"first_name":"John","last_name":"Doe","age":30,"monthly_income":50000,"phone_number":9876543210}'
```

---

## API Reference

All endpoints accept and return **JSON**.  
Base URL: `http://localhost:8000`

---

### POST `/register`
Register a new customer. The approved credit limit is auto-calculated as:
> `approved_limit = round(36 × monthly_salary, nearest lakh)`

**Request Body**

| Field | Type | Description |
|---|---|---|
| `first_name` | string | Customer's first name |
| `last_name` | string | Customer's last name |
| `age` | int | Customer's age |
| `monthly_income` | int | Monthly salary |
| `phone_number` | int | Unique phone number |

**Response Body** `201 Created`

| Field | Type |
|---|---|
| `customer_id` | int |
| `first_name` | string |
| `last_name` | string |
| `age` | int |
| `monthly_income` | int |
| `approved_limit` | int |
| `phone_number` | int |

**Example**
```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Priya",
    "last_name": "Sharma",
    "age": 28,
    "monthly_income": 75000,
    "phone_number": 9876543210
  }'
```

---

### POST `/check-eligibility`
Check loan eligibility without creating a loan. Returns a credit decision and corrected interest rate.

**Credit Score Components (out of 100)**

| Component | Weight |
|---|---|
| Past EMIs paid on time | 35 pts |
| Number of loans taken | 20 pts |
| Loan activity this year | 20 pts |
| Loan approved volume vs limit | 25 pts |
| Current loans > approved limit | Score = 0 |

**Approval Rules**

| Credit Score | Decision |
|---|---|
| > 50 | Approved at requested rate |
| 30 – 50 | Approved only if rate > 12% (else corrected to 12%) |
| 10 – 30 | Approved only if rate > 16% (else corrected to 16%) |
| < 10 | Rejected |
| Current EMIs > 50% salary | Rejected |

**Request Body**

| Field | Type | Description |
|---|---|---|
| `customer_id` | int | |
| `loan_amount` | float | |
| `interest_rate` | float | Annual % |
| `tenure` | int | Months |

**Response Body** `200 OK`

| Field | Type | Description |
|---|---|---|
| `customer_id` | int | |
| `approval` | bool | |
| `interest_rate` | float | Requested rate |
| `corrected_interest_rate` | float | Adjusted rate per slab |
| `tenure` | int | |
| `monthly_installment` | float | EMI using compound interest |

**Example**
```bash
curl -X POST http://localhost:8000/check-eligibility \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "loan_amount": 200000,
    "interest_rate": 10.5,
    "tenure": 24
  }'
```

---

### POST `/create-loan`
Process and create a loan if the customer is eligible.

**Request Body** — same as `/check-eligibility`

**Response Body**

| Field | Type | Description |
|---|---|---|
| `loan_id` | int \| null | Null if rejected |
| `customer_id` | int | |
| `loan_approved` | bool | |
| `message` | string | Reason if rejected |
| `monthly_installment` | float | |

**Example**
```bash
curl -X POST http://localhost:8000/create-loan \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "loan_amount": 200000,
    "interest_rate": 10.5,
    "tenure": 24
  }'
```

---

### GET `/view-loan/<loan_id>`
View full details of a specific loan including embedded customer info.

**Response Body**

| Field | Type |
|---|---|
| `loan_id` | int |
| `customer` | `{customer_id, first_name, last_name, phone_number, age}` |
| `loan_amount` | float |
| `interest_rate` | float |
| `monthly_installment` | float |
| `tenure` | int |

**Example**
```bash
curl http://localhost:8000/view-loan/42
```

---

### GET `/view-loans/<customer_id>`
View all loans associated with a customer.

**Response Body** — Array of loan objects

| Field | Type |
|---|---|
| `loan_id` | int |
| `loan_amount` | float |
| `interest_rate` | float |
| `monthly_installment` | float |
| `repayments_left` | int |

**Example**
```bash
curl http://localhost:8000/view-loans/1
```

---

## EMI Calculation

EMI is calculated using the **compound interest (reducing balance) formula**:

```
EMI = P × r × (1 + r)^n / ((1 + r)^n − 1)

where:
  P = principal (loan amount)
  r = monthly interest rate = annual_rate / 12 / 100
  n = tenure in months
```

---

## Data Ingestion

Data ingestion happens **automatically on startup** via Celery background workers.

The process:
1. `entrypoint.sh` calls `python manage.py ingest_data`
2. Two Celery tasks are dispatched: `ingest_customer_data` and `ingest_loan_data`
3. The Celery worker processes both tasks concurrently
4. Each task uses `update_or_create` — safe to re-run (idempotent)
5. Both tasks have auto-retry (3 attempts) on failure

To manually re-trigger ingestion:
```bash
docker compose exec web python manage.py ingest_data
```

---

## Running Tests

```bash
# Run all tests inside the container
docker compose exec web python manage.py test

# Or run locally (requires DB connection)
python manage.py test --verbosity=2
```

**Test coverage includes:**
- EMI calculation correctness
- Credit score calculation (no history, high debt, good history)
- Loan eligibility logic (EMI cap, interest rate correction)
- All 5 API endpoints (happy path + error cases)
- Duplicate phone detection
- 404 handling for missing customers/loans

---

## Environment Variables

All variables are pre-configured in `docker-compose.yml`. For production, override via `.env`:

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | (insecure default) | Django secret key |
| `DEBUG` | `True` | Set to `False` in production |
| `DB_NAME` | `credit_db` | PostgreSQL database name |
| `DB_USER` | `credit_user` | PostgreSQL user |
| `DB_PASSWORD` | `credit_password` | PostgreSQL password |
| `DB_HOST` | `db` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | Redis URL for Celery |

---

## Stopping the Application

```bash
docker compose down          # Stop containers
docker compose down -v       # Stop + remove volumes (clears DB)
```

---

## Notes

- **No frontend** is included per the assignment spec.
- Unit tests are included as a bonus.
- All services start with a single `docker compose up --build`.
- Code is organised by responsibility: models, views, serializers, services, tasks each live in their own files.
