# BI Dashboard — Stockbit (Group 8)

A Business Intelligence dashboard for historical analysis of EMAS and GOLD stock movements on the Indonesia Stock Exchange (IDX), built as a Business Intelligence course project at Telkom University.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Environment | Miniconda + uv |
| Database | PostgreSQL 16 (Docker) |
| ETL | Python (pandas, SQLAlchemy) |
| Visualization | Power BI Desktop |

---

## Repository Structure

```
bi-stockbit/
├── data/
│   └── raw/                  # Source CSV files (EMAS & GOLD)
├── etl/
│   └── etl.py                # Main ETL pipeline
├── sql/
│   └── schema.sql            # Star schema DDL
├── docker/
│   └── docker-compose.yml    # PostgreSQL container configuration
├── .env.example              # Environment variables template
├── .gitignore
└── README.md
```

---

## Prerequisites

Please ensure the following tools are installed before starting:

- Python 3.11+ (or [Miniconda](https://docs.conda.io/en/latest/miniconda.html))
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with WSL2 backend enabled
- [Power BI Desktop](https://www.microsoft.com/en-us/download/details.aspx?id=58494)

---

## Setup & Running the Project

### 1. Clone the repository

```bash
git clone <repo-url>
cd bi-stockbit
```

### 2. Prepare the Python environment

**Option A: Using standard Python venv (Recommended)**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install uv
uv init
uv add pandas sqlalchemy psycopg2-binary python-dotenv
```

**Option B: Using Miniconda**
```bash
conda create -n bi-stockbit python=3.11 -y
conda activate bi-stockbit
pip install uv  # Install uv if missing
uv init
uv add pandas sqlalchemy psycopg2-binary python-dotenv
```

### 3. Configure environment variables

```bash
# Mac/Linux/WSL
cp .env.example .env

# Windows (CMD / PowerShell)
copy .env.example .env
```

Open `.env` and fill in the following values:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=stockbit
DB_USER=stockbit
DB_PASSWORD=your_password_here
```

### 4. Run PostgreSQL via Docker

```bash
cd docker
docker compose up -d
```

Verify that the container is running:

```bash
docker ps
```

Ensure the `stockbit-pg` container has a `healthy` status.

### 5. Create the database schema

```bash
# Mac/Linux/WSL/Windows CMD
docker exec -i stockbit-pg psql -U stockbit -d stockbit < sql/schema.sql

# Windows PowerShell specific
Get-Content sql\schema.sql | docker exec -i stockbit-pg psql -U stockbit -d stockbit
```

Verify that the three tables have been successfully created:

```bash
docker exec stockbit-pg psql -U stockbit -d stockbit -c "\dt"
```

Expected output:

```
 Schema |       Name        | Type  |  Owner
--------+-------------------+-------+----------
 public | dim_date          | table | stockbit
 public | dim_ticker        | table | stockbit
 public | fact_stock_prices | table | stockbit
```

### 6. Run the ETL pipeline

Ensure the CSV files are present in `data/raw/` before running the ETL sequence.

```bash
conda activate bi-stockbit
python etl/etl.py
```

Verify the data has been loaded successfully:

```bash
# Mac/Linux/WSL
docker exec stockbit-pg psql -U stockbit -d stockbit -c \
  "SELECT ticker_code, COUNT(*) FROM fact_stock_prices f JOIN dim_ticker t ON f.ticker_id = t.ticker_id GROUP BY ticker_code;"

# Windows (CMD / PowerShell)
docker exec stockbit-pg psql -U stockbit -d stockbit -c "SELECT ticker_code, COUNT(*) FROM fact_stock_prices f JOIN dim_ticker t ON f.ticker_id = t.ticker_id GROUP BY ticker_code;"
```

Expected output:

```
 ticker_code | count
-------------+-------
 GOLD        |  1420
 EMAS        |   108
```

### 7. Connect Power BI to PostgreSQL

1. Open Power BI Desktop
2. Home → Get Data → PostgreSQL database
3. Fill in the connection details:
   - Server: `localhost` (or `127.0.0.1`)
   - Database: `stockbit`
   - Data Connectivity mode: **Import**
4. Enter your credentials according to the `.env` file when prompted
5. In the Navigator, select all three tables: `dim_date`, `dim_ticker`, `fact_stock_prices`
6. Click Load
7. Open the Model view and ensure the following two relationships are detected automatically:
   - `fact_stock_prices.date_id` → `dim_date.date_id`
   - `fact_stock_prices.ticker_id` → `dim_ticker.ticker_id`

---

## Database Schema

This project utilizes a **star schema** pattern consisting of one fact table and two dimension tables.

### fact_stock_prices
The central table storing all daily price records. One row represents one trading day for a single stock.

| Column | Type | Description |
|---|---|---|
| fact_id | serial PK | Unique identifier, auto-generated |
| date_id | int FK | Reference to dim_date |
| ticker_id | int FK | Reference to dim_ticker |
| open_price | numeric | Opening price |
| close_price | numeric | Closing price |
| high_price | numeric | Highest price of the day |
| low_price | numeric | Lowest price of the day |
| volume | bigint | Volume of shares traded |
| change_pct | numeric | Percentage change from the previous day |

### dim_date
Stores time attributes derived from the date column during the ETL process.

| Column | Type | Description |
|---|---|---|
| date_id | serial PK | Unique identifier, auto-generated |
| full_date | date | Full date in YYYY-MM-DD format |
| year | int | Year |
| quarter | int | Quarter (1-4) |
| month | int | Month number (1-12) |
| month_name | varchar | Month name (January, February, ...) |
| day_of_week | int | Day of the week (1=Monday, 7=Sunday) |
| day_name | varchar | Day name (Monday, Friday, ...) |

### dim_ticker
Stores identity information for each stock issuer.

| Column | Type | Description |
|---|---|---|
| ticker_id | serial PK | Unique identifier, auto-generated |
| ticker_code | varchar | IDX stock code (EMAS or GOLD) |
| company_name | varchar | Full company name |
| exchange | varchar | Stock exchange (IDX) |
| sector | varchar | Industry sector |

---

## Troubleshooting

**Port 5432 is already in use by another process in Windows**

Check the process using that port via PowerShell:

```powershell
netstat -ano | findstr :5432
Get-Process -Id <PID>
```

If it is an unnecessary process, stop it or change the Docker host port to `5433` in `docker-compose.yml` and adjust the Power BI connection accordingly.

**Power BI fails to authenticate to PostgreSQL**

Go to File → Options and settings → Data source settings → select `localhost` → Clear Permissions. Close Power BI completely and try reconnecting.

**PostgreSQL container is inaccessible from Windows**

Ensure `docker-compose.yml` uses the `5432:5432` or `0.0.0.0:5432:5432` binding (note: Docker Desktop natively maps `5432:5432` globally) and restart the container:

```bash
docker compose down && docker compose up -d
```

**ETL fails because tables do not exist**

Make sure `schema.sql` has been executed before running `etl.py`.

---

## Notes for the Team

After the ETL process is completed and Power BI is connected, save the `.pbix` file and share it with the team. The imported data will be stored within the file itself, meaning other members won't need to run Docker or execute the ETL pipeline again to start building dashboard visualizations.

Docker only needs to be run again when you intend to refresh the dashboard specifically with an updated underlying dataset.