FROM python:3.11.7-slim-bullseye

WORKDIR /app

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y git

COPY *.py /app/