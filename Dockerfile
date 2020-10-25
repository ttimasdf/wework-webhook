FROM python:3-alpine as base

# Use separate image to build modules with C extensions
FROM base as builder

RUN mkdir /install
WORKDIR /install

RUN apk add gcc musl-dev libffi-dev openssl-dev \
    && pip install --prefix=/install gunicorn

COPY requirements.txt /requirements.txt
RUN pip install --prefix=/install -r /requirements.txt

FROM base

COPY --from=builder /install /usr/local
COPY . /app
WORKDIR /app

EXPOSE 8000
CMD ["gunicorn", "-b=0.0.0.0:8000", "--log-level=info", "--access-logfile=-", "app"]
