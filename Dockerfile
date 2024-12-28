FROM python:3.12.8-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt
COPY ./routers /app/routers
COPY ./static /app/static
COPY ./templates /app/templates
COPY ./utils /app/utils
COPY ./main.py /app/main.py
EXPOSE 8000