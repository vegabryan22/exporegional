import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "exporegional-secret-key")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(25 * 1024 * 1024)))
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://exporegional_user:exporegional123@localhost/exporegional?charset=utf8mb4",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTO_INIT_DB = os.getenv("AUTO_INIT_DB", "1").strip().lower() in {"1", "true", "yes", "on"}

