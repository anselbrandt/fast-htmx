import json
import os

from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown
from dotenv import load_dotenv
import paramiko
from psycopg_pool import ConnectionPool
import redis

from db_ops import createTable, insert, delete

load_dotenv()


def get_conn_str():
    return f"""
    dbname={os.getenv('POSTGRES_DB')}
    user={os.getenv('POSTGRES_USER')}
    password={os.getenv('POSTGRES_PASSWORD')}
    host={os.getenv('POSTGRES_HOST')}
    port={os.getenv('POSTGRES_PORT')}
    """


CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")
SSH_USERNAME = os.getenv("SSH_USERNAME")
SSH_PASSWORD = os.getenv("SSH_PASSWORD")
REMOTE_HOST = os.getenv("REMOTE_HOST")
REMOTE_ROOT_PATH = os.getenv("REMOTE_ROOT_PATH")
LOCAL_ROOT_PATH = os.getenv("LOCAL_ROOT_PATH")

pool = None

cache = redis.Redis(decode_responses=True)

celery = Celery(
    "tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    broker_connection_retry_on_startup=True,
)


@worker_process_init.connect
def init_worker(**kwargs):
    global pool
    pool = ConnectionPool(conninfo=get_conn_str())
    try:
        createTable(pool)
        print("Creating tasks table")
    except Exception as error:
        print("Tasks table already exists")


def updateProgress(id):
    def update(transferred, total):
        cache.set(id, json.dumps({"transferred": transferred, "total": total}))

    return update


@celery.task(bind=True)
def copyFile(self, filename):
    id = self.request.id
    insert(pool, id, filename)
    transport = paramiko.Transport((REMOTE_HOST, 22))
    inpath = f"{REMOTE_ROOT_PATH}/{filename}"
    outpath = f"{LOCAL_ROOT_PATH}/{filename}"
    transport.connect(None, SSH_USERNAME, SSH_PASSWORD)
    sftp = paramiko.SFTPClient.from_transport(transport)
    sftp.get(
        inpath,
        outpath,
        callback=updateProgress(id),
    )
    sftp.close()
    transport.close()
    delete(pool, id)


@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    global pool
    if pool:
        pool.close()
