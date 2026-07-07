from pathlib import Path

APP_NAME = "Stock & Stir"
APP_CODE = "SNS"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

CKB_DB_NAME = "ckb_seed_001.db"
DB_PATH = DATA_DIR / CKB_DB_NAME

DATA_DIR.mkdir(exist_ok=True)
