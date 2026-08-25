CREATE EXTENSION IF NOT EXISTS vector;

-- Dedicated test database, kept separate from the app's real dev data.
-- tests/conftest.py's db_session fixture wipes documents/document_chunks/
-- users after every test that uses it — it must never point at the same
-- database as local dev/demo data. See docs/release-gate/PROGRESS.md,
-- Block 4/Sprint 15, for the real incident this fixes.
CREATE DATABASE cka_test;
\connect cka_test
CREATE EXTENSION IF NOT EXISTS vector;
