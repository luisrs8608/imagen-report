import os

# SQLite existe exclusivamente como base efímera y aislada para la suite de tests.
# La aplicación normal no permite iniciarse con SQLite.
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"
