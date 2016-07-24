FROM python:3
WORKDIR /workspace

COPY dev-requirements.txt dev-requirements.txt
RUN pip3 install -r dev-requirements.txt
RUN pip3 install mypy-lang
COPY . .

CMD ["/workspace/run_tests.sh"]
