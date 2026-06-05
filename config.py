import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "expotecnica-secret-key")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(25 * 1024 * 1024)))
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://expotecnica_user:expotecnica123@localhost/expotecnica_db?charset=utf8mb4",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

