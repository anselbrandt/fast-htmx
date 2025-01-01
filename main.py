from contextlib import asynccontextmanager
import json
from typing import Optional
import os

from fastapi import FastAPI, Header, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from pydantic import BaseModel
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import redis

from db_ops import getTasks
from sampledata import sampleusers, sampletasks, samplefiles
from routers.limiter import limiter
from routers.open_routes import router as open_routes
from routers.protected_routes import router as protected_routes
from routers.user_routes import router as user_routes
from tasks import copyFile


def get_conn_str():
    return f"""
    dbname={os.getenv('POSTGRES_DB')}
    user={os.getenv('POSTGRES_USER')}
    password={os.getenv('POSTGRES_PASSWORD')}
    host={os.getenv('POSTGRES_HOST')}
    port={os.getenv('POSTGRES_PORT')}
    """


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.pool = AsyncConnectionPool(
        conninfo=get_conn_str(), open=False, kwargs={"row_factory": dict_row}
    )
    await app.pool.open()
    yield
    await app.pool.close()


cache = redis.Redis(decode_responses=True)

ROOT_PATH = "/api"

app = FastAPI(root_path=ROOT_PATH, lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(open_routes)
app.include_router(protected_routes)
app.include_router(user_routes)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
@limiter.limit("1/second")
async def index(request: Request, hx_request: Optional[str] = Header(None)):
    context = {
        "request": request,
        "rootPath": ROOT_PATH,
        "tasks": sampletasks,
        "users": sampleusers,
        "files": samplefiles,
    }
    return templates.TemplateResponse("index.html", context)


@app.post("/start/{id}")
async def start(
    request: Request,
    response: Response,
    id: str,
    hx_request: Optional[str] = Header(None),
):
    cache.set(f"progress_{id}", 0)
    context = {"request": request, "rootPath": ROOT_PATH, "id": id}
    return templates.TemplateResponse("running.html", context)


class Data(BaseModel):
    filename: str


@app.post("/copy")
async def copy(request: Request, data: Data, response: Response):
    response.status_code = status.HTTP_200_OK
    filename = data.filename
    res = copyFile.delay(filename)
    id = res.task_id
    progress = {"transferred": 0, "total": 0}
    cache.set(id, json.dumps(progress))
    context = {"request": request, "rootPath": ROOT_PATH, "id": id}
    return templates.TemplateResponse("copying.html", context)


@app.get("/job/progress/{id}")
async def job(
    request: Request,
    response: Response,
    id: str,
    hx_request: Optional[str] = Header(None),
):
    current = cache.get(f"progress_{id}")
    progress = int(current)
    if progress < 100:
        progress = progress + 10
        cache.set(f"progress_{id}", progress)
        context = {
            "request": request,
            "rootPath": ROOT_PATH,
            "progress": progress,
            "id": id,
        }
        return templates.TemplateResponse("progress.html", context)
    if progress == 100:
        context = {
            "request": request,
            "rootPath": ROOT_PATH,
            "progress": progress,
            "id": id,
        }
        response.headers["HX-Trigger"] = "done"
        return templates.TemplateResponse(
            "progress.html", context, headers=response.headers
        )


@app.get("/tasks")
async def alltasks(
    request: Request,
    response: Response,
    hx_request: Optional[str] = Header(None),
):
    results = await getTasks(request.app.pool)
    context = {
        "request": request,
        "rootPath": ROOT_PATH,
        "inprogress": results,
    }
    print(results)
    return templates.TemplateResponse("inprogress.html", context)


@app.get("/task/progress/{id}")
async def task(
    request: Request,
    response: Response,
    id: str,
    hx_request: Optional[str] = Header(None),
):
    result = cache.get(id)
    data = json.loads(result)
    transferred, total = data.values()
    progress = 0 if total == 0 else round((transferred / total) * 100)
    if progress < 100:
        context = {
            "request": request,
            "rootPath": ROOT_PATH,
            "progress": progress,
            "id": id,
        }
        return templates.TemplateResponse("progress.html", context)
    if progress == 100:
        context = {
            "request": request,
            "rootPath": ROOT_PATH,
            "progress": progress,
            "id": id,
        }
        response.headers["HX-Trigger"] = "done"
        return templates.TemplateResponse(
            "progress.html", context, headers=response.headers
        )


@app.get("/job/{id}")
async def job(
    request: Request,
    response: Response,
    id: str,
    hx_request: Optional[str] = Header(None),
):
    context = {"request": request, "rootPath": ROOT_PATH, "id": id}
    return templates.TemplateResponse("complete.html", context)


@app.get("/task/{id}")
async def task(
    request: Request,
    response: Response,
    id: str,
    hx_request: Optional[str] = Header(None),
):
    context = {"request": request, "rootPath": ROOT_PATH, "id": id}
    return templates.TemplateResponse("copycomplete.html", context)


@app.post("/post")
@limiter.limit("1/second")
async def post(request: Request, data):
    return data


@app.delete("/delete/{id}")
@limiter.limit("1/second")
async def delete(request: Request, id: str, response: Response):
    response.status_code = status.HTTP_200_OK
    return response
