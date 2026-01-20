FROM python:3-slim

WORKDIR /action

# Copy Pipfile and install dependencies
COPY ./Pipfile ./
RUN pip install pipenv && \
  pipenv install --system && \
  pipenv --clear

# Copy all action files including source code
COPY . /action

ENTRYPOINT [ "python" ]
CMD [ "/action/main.py" ]