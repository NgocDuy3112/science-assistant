from dotenv import load_dotenv
import os


load_dotenv("configs/.env", override=True)


MAX_RESULTS = 5
CHAT_MODEL_NAME = os.getenv("CHAT_MODEL_NAME")

PAPERS_DIR = os.getenv("PAPERS_DIR")
SQLITE_CHECKPOINTS_URI = os.getenv("SQLITE_CHECKPOINTS_URI")