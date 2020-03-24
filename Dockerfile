# Base image
FROM python:3.6

# Update system
RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get -y autoremove

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
                    build-essential \
                    sqlite3

# Create main code folder
RUN mkdir /code
WORKDIR /code

# Install dependencies (simulates `make install` in the live dockerfile)
RUN pip install -U pip==19.3.1
RUN pip install -U pip-tools
COPY ./requirements.txt requirements.txt
RUN pip-sync requirements.txt

# Install dev dependencies
COPY ./requirements-dev.txt requirements-dev.txt
RUN pip install -r requirements-dev.txt

ENTRYPOINT ["/bin/bash", "-c"]
