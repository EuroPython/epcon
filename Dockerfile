# Base image
FROM python:3.6

# Update system
RUN apt-get update && apt-get -y upgrade && apt-get -y autoremove

# Install system dependencies
RUN apt-get install -y build-essential sqlite3

# Create main code folder
RUN mkdir /code
WORKDIR /code

# Install dev dependencies (simulates `make install`)
COPY ./requirements-dev.txt requirements-dev.txt
RUN pip install -U pip==19.3.1
RUN pip install -U pip-tools
RUN pip-sync requirements-dev.txt

ENTRYPOINT ["/bin/bash", "-c"]
