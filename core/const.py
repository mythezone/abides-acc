from dotenv import load_dotenv
import os

load_dotenv()

SERVER_IP = os.getenv("SERVER_IP")
SERVER_NAME = os.getenv("SERVER_NAME")
SHARE_NAME = os.getenv("SHARE_NAME")
SAMPLE_FOLDER = os.getenv("SAMPLE_FOLDER")
SAMPLE_FILE = os.getenv("SAMPLE_FILE")
SAMBA_USERNAME = os.getenv("SAMBA_USERNAME")
SAMBA_PASSWORD = os.getenv("SAMBA_PASSWORD")

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_DB = os.getenv("REDIS_DB")


__all__ = [
    "SERVER_IP",
    "SERVER_NAME",
    "SHARE_NAME",
    "SAMPLE_FOLDER",
    "SAMPLE_FILE",
    "SAMBA_USERNAME",
    "SAMBA_PASSWORD",
    "REDIS_HOST",
    "REDIS_PORT",
    "REDIS_DB",
]
