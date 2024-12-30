from fastapi import FastAPI, Header, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional
from routers.open_routes import router as open_routes
from routers.protected_routes import router as protected_routes
from routers.user_routes import router as user_routes
from routers.limiter import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel
from tasks import copyFile
import redis
import json

cache = redis.Redis(decode_responses=True)


ROOT_PATH = "/api"

users = [
    {"id": 0, "name": "Joe Smith", "email": "joe@smith.org", "status": "Active"},
    {
        "id": 1,
        "name": "Angie MacDowell",
        "email": "angie@macdowell.org",
        "status": "Active",
    },
    {
        "id": 2,
        "name": "Fuqua Tarkenton",
        "email": "fuqua@tarkenton.org",
        "status": "Active",
    },
    {"id": 3, "name": "Kim Yee", "email": "kim@yee.org", "status": "Inactive"},
]

tasks = [
    {"id": 123, "name": "one-two-three"},
    {"id": 456, "name": "four-five-six"},
    {"id": 789, "name": "seven-eight-nine"},
]

app = FastAPI(root_path=ROOT_PATH)

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
        "tasks": tasks,
        "users": users,
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
    context = {"request": request, "id": id}
    return templates.TemplateResponse("running.html", context)


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
        context = {"request": request, "progress": progress, "id": id}
        return templates.TemplateResponse("progress.html", context)
    if progress == 100:
        context = {"request": request, "progress": progress, "id": id}
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
    context = {"request": request, "id": id}
    return templates.TemplateResponse("complete.html", context)


@app.post("/post")
@limiter.limit("1/second")
async def post(request: Request, data):
    return data


@app.delete("/delete/{id}")
@limiter.limit("1/second")
async def delete(request: Request, id: str, response: Response):
    response.status_code = status.HTTP_200_OK
    return response


class Data(BaseModel):
    filename: str


@app.post("/copy")
async def copy(data: Data, response: Response):
    response.status_code = status.HTTP_200_OK
    print(data)
    filename = data.filename
    res = copyFile.delay(filename)
    id = res.task_id
    progress = {"transferred": 0, "total": 0}
    cache.set(id, json.dumps(progress))
    return id


@app.get("/progress/{id}")
async def progress(request: Request):
    result = cache.get(id)
    data = json.loads(result)
    transferred, total = data.values()
    progress = 0 if total == 0 else round((transferred / total) * 100)
    context = {"request": request, "progress": progress}
    return templates.TemplateResponse("partials/progressbar.html", context)
