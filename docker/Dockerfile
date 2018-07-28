# Docker file for EP2017 python container
FROM python:2.7.9

ENV PYTHONUNBUFFERED 1
ENV PIP_NO_CACHE_DIR 0

RUN mkdir /website /website/data /website/data/site
WORKDIR /website

# Upgrade System:
RUN apt-get update && apt-get -y upgrade && apt-get -y autoremove && apt-get install -qq build-essential libssl-dev libxrender-dev wget git wkhtmltopdf libpango1.0-0 libcairo2 libpq-dev && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip && pip install greenlet eventlet

ADD requirements.txt requirements.txt
RUN  pip install -r requirements.txt

ADD . /website
ENTRYPOINT ["./docker/entrypoint.sh" ]
