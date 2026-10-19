import os
import tempfile
from pathlib import Path

# Must be set before app modules read settings: a throwaway SQLite database
# exercises the real migrate -> seed -> load path without Postgres.
_DB = Path(tempfile.mkdtemp()) / "whatsize-test.db"
os.environ["WHATSIZE_DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["WHATSIZE_AUTO_MIGRATE"] = "true"
