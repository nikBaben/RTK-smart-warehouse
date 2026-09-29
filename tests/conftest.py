"""Tests never load the developer's credentials or connect to their databases."""

import os

os.environ["DB_URL"] = "postgresql+asyncpg://unused:unused@127.0.0.1:1/unused"
os.environ["KEYCLOAK_URL"] = "http://127.0.0.1:1/"
