Built container
===============

`$ docker build . -t ep2018 -f docker/Dockerfile`

Run container
=============

Tests
-----

`$ docker run -it -p 8000:8000 --env DEBUG=True ep2018 tests`

Dev environment
---------------

`$ docker run -it -p 8000:8000 --env DEBUG=True ep2018 dev`

Production environment
----------------------

`$ docker run -it -p 8000:8000 --env DEBUG=True ep2018`
