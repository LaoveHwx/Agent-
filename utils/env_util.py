import os
from dotenv import load_dotenv
load_dotenv()

model_name = os.getenv("MODEL_NAME")
api_key = os.getenv("API_KEY")
base_url = os.getenv("BASE_URL")

ps_dsn = os.getenv("PS_DSN")
