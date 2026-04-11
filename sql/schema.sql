-- Star Schema for Stockbit BI Data Mart

-- 1. Time Dimension
CREATE TABLE IF NOT EXISTS dim_date (
    date_id     SERIAL       PRIMARY KEY,
    full_date   DATE         NOT NULL UNIQUE,
    year        INT          NOT NULL,
    quarter     INT          NOT NULL,
    month       INT          NOT NULL,
    month_name  VARCHAR(20)  NOT NULL,
    day_of_week INT          NOT NULL,
    day_name    VARCHAR(20)  NOT NULL
);

-- 2. Stock Identity Dimension
CREATE TABLE IF NOT EXISTS dim_ticker (
    ticker_id    SERIAL       PRIMARY KEY,
    ticker_code  VARCHAR(10)  NOT NULL UNIQUE,
    company_name VARCHAR(100) NOT NULL,
    exchange     VARCHAR(20)  NOT NULL,
    sector       VARCHAR(50)
);

-- 3. Central Fact Table
CREATE TABLE IF NOT EXISTS fact_stock_prices (
    fact_id     SERIAL        PRIMARY KEY,
    date_id     INT           NOT NULL REFERENCES dim_date(date_id),
    ticker_id   INT           NOT NULL REFERENCES dim_ticker(ticker_id),
    open_price  NUMERIC(12,2),
    close_price NUMERIC(12,2),
    high_price  NUMERIC(12,2),
    low_price   NUMERIC(12,2),
    volume      BIGINT,
    change_pct  NUMERIC(6,2),

    CONSTRAINT uq_date_ticker UNIQUE (date_id, ticker_id)
);
