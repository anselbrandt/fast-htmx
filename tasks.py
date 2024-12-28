import os
from celery import Celery
from dotenv import load_dotenv
import paramiko
import redis
import json

load_dotenv()

cache = redis.Redis(decode_responses=True)

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")
SSH_USERNAME = os.getenv("SSH_USERNAME")
SSH_PASSWORD = os.getenv("SSH_PASSWORD")
REMOTE_HOST = os.getenv("REMOTE_HOST")
REMOTE_ROOT_PATH = os.getenv("REMOTE_ROOT_PATH")
LOCAL_ROOT_PATH = os.getenv("LOCAL_ROOT_PATH")

celery = Celery("tasks", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)


def updateProgress(id):
    def update(transferred, total):
        cache.set(id, json.dumps({"transferred": transferred, "total": total}))

    return update


@celery.task(bind=True)
def copyFile(self, filename):
    id = self.request.id
    transport = paramiko.Transport((REMOTE_HOST, 22))
    inpath = f"{REMOTE_ROOT_PATH}/{filename}"
    outpath = filename
    transport.connect(None, SSH_USERNAME, SSH_PASSWORD)
    sftp = paramiko.SFTPClient.from_transport(transport)
    sftp.get(
        inpath,
        outpath,
        callback=updateProgress(id),
    )
    sftp.close()
    transport.close()
