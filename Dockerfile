FROM python:3.6-stretch
RUN mkdir /epcon
RUN apt-get update
RUN apt-get install -y dialog
RUN apt-get install -y whiptail
RUN apt-get install -y apt-utils
RUN apt-get upgrade -y
RUN apt-get install -y virtualenv
WORKDIR /epcon
COPY . /epcon/
RUN ./provision.sh
# The command above created a venv in /epcon-env
# We can activate it by setting some shell envs
ENV VIRTUAL_ENV=/epcon-env
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
