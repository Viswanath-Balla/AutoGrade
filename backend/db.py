import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Load env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Read env vars
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USERNAME = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_SSL_CA = os.getenv("DB_SSL_CA")
# CA_PATH = os.getenv("CA")
# CA_PATH = os.path.join(BASE_DIR, "certs", "isrgrootx1.pem")

if not all([DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_NAME]):
    raise RuntimeError("Database environment variables missing")

# Encode password safely
encoded_password = quote_plus(DB_PASSWORD)

# SSL support (optional)
ssl_query = ""
if DB_SSL_CA:
    ssl_path = os.path.join(BASE_DIR, DB_SSL_CA)
    ssl_query = f"?ssl_ca={ssl_path}"

# DATABASE URL
DATABASE_URL = (
    f"mysql+pymysql://{DB_USERNAME}:{encoded_password}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}{ssl_query}"
)

# Engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=True
)

# Session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base
Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()