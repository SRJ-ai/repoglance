# Minimal image to run repoglance against a mounted repository.
#   docker build -t repoglance .
#   docker run --rm -v "$PWD:/repo" repoglance /repo
FROM python:3.12-slim

RUN pip install --no-cache-dir repoglance

WORKDIR /repo
ENTRYPOINT ["repoglance"]
CMD ["."]
