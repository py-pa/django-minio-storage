## Running tests

Test coverage is and should remain 100%. The library is very small and a minio
server can be very easily brought up with docker, so there is no reason to use
mocking most of the time, the tests should run directly against a real minio
instance.

To run the tests you need to have minio running locally with some specific
settings, you can start it using docker-compose:

```sh
docker-compose up -d
```

Use tox to run the tests for all environments in `tox.ini`:

```sh
tox
```

Or just run tests for some of them

```sh
# list all environment
tox -l
# run one or more of them
tox -e py35-django110,py35-django111
```
