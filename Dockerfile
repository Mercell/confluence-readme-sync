FROM python:3-slim

WORKDIR /action

# Install dependencies
RUN pip install --no-cache-dir markdown requests python-dotenv

# Copy all action files including source code
COPY . /action

ENTRYPOINT [ "python" ]
CMD [ "/action/main.py" ]