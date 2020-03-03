# Base image
FROM python:3.6-buster

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
                    build-essential \
                    locales \
                    libssl-dev \
                    libxrender-dev \
                    libxml2-dev \
                    libxslt1-dev \
                    sqlite3 \
                    wget \
                    curl \
                    git

RUN pip install pip --upgrade

# Create main code folder
RUN mkdir /code
WORKDIR /code

# Install dev dependencies
COPY ./requirements-dev.txt requirements-dev.txt
RUN pip install -r requirements-dev.txt

ENTRYPOINT ["/bin/bash", "-c"]
