## Testing strategy

Test coverage is and should remain near 100%.

This package is very small and a minio server can be very easily brought up
with docker so there is typically no reason to use mocking at all. The tests
should run directly against a real minio server instance.

## Running tests

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
