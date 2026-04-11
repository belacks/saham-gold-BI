# BI Dashboard — Stockbit (Kelompok 8)

Business Intelligence dashboard untuk analisis historis pergerakan saham EMAS dan GOLD di Bursa Efek Indonesia (IDX), dibangun sebagai proyek mata kuliah Business Intelligence, Telkom University.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Environment | Miniconda + uv |
| Database | PostgreSQL 16 (Docker) |
| ETL | Python (pandas, SQLAlchemy) |
| Visualization | Power BI Desktop |

---

## Struktur Repo

```
bi-stockbit/
├── data/
│   └── raw/                  # File CSV sumber (EMAS & GOLD)
├── etl/
│   └── etl.py                # ETL pipeline utama
├── sql/
│   └── schema.sql            # DDL star schema
├── docker/
│   └── docker-compose.yml    # Konfigurasi PostgreSQL container
├── .env.example              # Template environment variables
├── .gitignore
└── README.md
```

---

## Prerequisites

Pastikan tools berikut sudah terinstall sebelum memulai:

- Python 3.11+ (atau [Miniconda](https://docs.conda.io/en/latest/miniconda.html) sebagai alternatif)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) dengan WSL2 backend aktif
- [Power BI Desktop](https://www.microsoft.com/en-us/download/details.aspx?id=58494)

---

## Setup & Menjalankan Proyek

### 1. Clone repo

```bash
git clone <repo-url>
cd bi-stockbit
```

### 2. Siapkan environment Python

**Opsi A: Menggunakan standard Python venv (Rekomendasi)**
```bash
python -m venv .venv
source .venv/bin/activate  # Untuk Windows: .venv\Scripts\activate
pip install uv
uv init
uv add pandas sqlalchemy psycopg2-binary python-dotenv
```

**Opsi B: Menggunakan Miniconda**
```bash
conda create -n bi-stockbit python=3.11 -y
conda activate bi-stockbit
pip install uv  # Install uv jika belum ada
uv init
uv add pandas sqlalchemy psycopg2-binary python-dotenv
```

### 3. Konfigurasi environment variables

```bash
# Mac/Linux/WSL
cp .env.example .env

# Windows (CMD / PowerShell)
copy .env.example .env
```

Buka `.env` dan isi nilai berikut:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=stockbit
DB_USER=stockbit
DB_PASSWORD=your_password_here
```

### 4. Jalankan PostgreSQL via Docker

```bash
cd docker
docker compose up -d
```

Verifikasi container berjalan:

```bash
docker ps
```

Pastikan container `stockbit-pg` berstatus `healthy`.

### 5. Buat skema database

```bash
# Mac/Linux/WSL/Windows CMD
docker exec -i stockbit-pg psql -U stockbit -d stockbit < sql/schema.sql

# Windows PowerShell khusus
Get-Content sql\schema.sql | docker exec -i stockbit-pg psql -U stockbit -d stockbit
```

Verifikasi ketiga tabel berhasil dibuat:

```bash
docker exec stockbit-pg psql -U stockbit -d stockbit -c "\dt"
```

Output yang diharapkan:

```
 Schema |       Name        | Type  |  Owner
--------+-------------------+-------+----------
 public | dim_date          | table | stockbit
 public | dim_ticker        | table | stockbit
 public | fact_stock_prices | table | stockbit
```

### 6. Jalankan ETL pipeline

Pastikan file CSV sudah ada di `data/raw/` sebelum menjalankan ETL.

```bash
# Aktifkan environment (jika belum) sesuai opsi yang dipilih di Langkah 2
python etl/etl.py
```

Verifikasi data berhasil dimuat:

```bash
# Mac/Linux/WSL
docker exec stockbit-pg psql -U stockbit -d stockbit -c \
  "SELECT ticker_code, COUNT(*) FROM fact_stock_prices f JOIN dim_ticker t ON f.ticker_id = t.ticker_id GROUP BY ticker_code;"

# Windows (CMD / PowerShell)
docker exec stockbit-pg psql -U stockbit -d stockbit -c "SELECT ticker_code, COUNT(*) FROM fact_stock_prices f JOIN dim_ticker t ON f.ticker_id = t.ticker_id GROUP BY ticker_code;"
```

Output yang diharapkan:

```
 ticker_code | count
-------------+-------
 GOLD        |  1420
 EMAS        |   108
```

### 7. Koneksi Power BI ke PostgreSQL

1. Buka Power BI Desktop
2. Home → Get Data → PostgreSQL database
3. Isi koneksi:
   - Server: `localhost` (atau `127.0.0.1`)
   - Database: `stockbit`
   - Data Connectivity mode: **Import**
4. Masukkan credentials sesuai `.env` saat diminta
5. Di Navigator, pilih ketiga tabel: `dim_date`, `dim_ticker`, `fact_stock_prices`
6. Klik Load
7. Buka Model view dan pastikan dua relasi terdeteksi otomatis:
   - `fact_stock_prices.date_id` → `dim_date.date_id`
   - `fact_stock_prices.ticker_id` → `dim_ticker.ticker_id`

---

## Skema Database

Proyek ini menggunakan pola **star schema** dengan satu fact table dan dua dimension table.

### fact_stock_prices
Tabel utama yang menyimpan seluruh record harga harian. Satu baris mewakili satu hari perdagangan untuk satu saham.

| Kolom | Tipe | Deskripsi |
|---|---|---|
| fact_id | serial PK | Identitas unik, di-generate otomatis |
| date_id | int FK | Referensi ke dim_date |
| ticker_id | int FK | Referensi ke dim_ticker |
| open_price | numeric | Harga pembukaan |
| close_price | numeric | Harga penutupan |
| high_price | numeric | Harga tertinggi hari itu |
| low_price | numeric | Harga terendah hari itu |
| volume | bigint | Jumlah lembar saham diperdagangkan |
| change_pct | numeric | Persentase perubahan dari hari sebelumnya |

### dim_date
Menyimpan atribut waktu yang diturunkan dari kolom tanggal selama proses ETL.

| Kolom | Tipe | Deskripsi |
|---|---|---|
| date_id | serial PK | Identitas unik, di-generate otomatis |
| full_date | date | Tanggal lengkap format YYYY-MM-DD |
| year | int | Tahun |
| quarter | int | Kuartal (1-4) |
| month | int | Nomor bulan (1-12) |
| month_name | varchar | Nama bulan (January, February, ...) |
| day_of_week | int | Hari dalam minggu (1=Senin, 7=Minggu) |
| day_name | varchar | Nama hari (Monday, Friday, ...) |

### dim_ticker
Menyimpan informasi identitas masing-masing emiten.

| Kolom | Tipe | Deskripsi |
|---|---|---|
| ticker_id | serial PK | Identitas unik, di-generate otomatis |
| ticker_code | varchar | Kode saham IDX (EMAS atau GOLD) |
| company_name | varchar | Nama lengkap perusahaan |
| exchange | varchar | Bursa efek (IDX) |
| sector | varchar | Sektor industri emiten |

---

## Troubleshooting

**Port 5432 sudah dipakai proses lain di Windows**

Cek proses yang memakai port tersebut via PowerShell:

```powershell
netstat -ano | findstr :5432
Get-Process -Id <PID>
```

Jika ditemukan proses yang tidak diperlukan, hentikan prosesnya atau ganti host port Docker ke `5433` di `docker-compose.yml` dan sesuaikan di koneksi Power BI.

**Power BI tidak bisa authenticate ke PostgreSQL**

Buka File → Options and settings → Data source settings → pilih `localhost` → Clear Permissions. Tutup Power BI sepenuhnya lalu coba koneksi ulang.

**Container PostgreSQL tidak bisa diakses dari Windows**

Pastikan `docker-compose.yml` menggunakan binding `5432:5432` atau `0.0.0.0:5432:5432` (catatan: Docker Desktop secara native me-mapping `5432:5432` secara global) dan restart container:

```bash
docker compose down && docker compose up -d
```

**ETL gagal karena tabel belum ada**

Pastikan `schema.sql` sudah dijalankan terlebih dahulu sebelum menjalankan `etl.py`.

---

## Catatan untuk Tim

Setelah ETL selesai dijalankan dan Power BI sudah terhubung, simpan file `.pbix` dan bagikan ke anggota tim. Data sudah tersimpan di dalam file tersebut sehingga anggota lain tidak perlu menjalankan Docker atau ETL ulang untuk mulai membangun visualisasi dashboard.

Docker hanya perlu berjalan kembali jika ingin me-refresh data dengan dataset yang diperbarui.