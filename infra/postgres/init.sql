-- Runs once, when the Postgres volume is created.
-- Enables pgvector in the main database and creates a separate database for tests.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE DATABASE faro_test;
\connect faro_test
CREATE EXTENSION IF NOT EXISTS vector;
