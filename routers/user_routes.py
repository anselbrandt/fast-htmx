from fastapi import APIRouter, Request, Response, status
from .limiter import limiter
from utils import fruitname

router = APIRouter(prefix="/user")


@router.get("/")
@limiter.limit("1/second")
def get(request: Request, response: Response):
    response.status_code = status.HTTP_200_OK
    return f"Hello, {fruitname()}!"
