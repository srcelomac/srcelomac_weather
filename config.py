from dotenv import load_dotenv
import os
from pathlib import Path


env_path = Path("venv") / ".env"
load_dotenv(dotenv_path=env_path)

ACCUWEATHER_API_KEY = os.getenv('ACCUWEATHER_API_KEY')
YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')
TG_TOKEN = os.getenv('TG_TOKEN')