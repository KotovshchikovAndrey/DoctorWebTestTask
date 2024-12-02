FROM python:3.12

WORKDIR /app

COPY pyproject.toml poetry.lock ./

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev

COPY ./src ./

EXPOSE 8000