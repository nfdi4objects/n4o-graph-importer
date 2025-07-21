FROM node:24-slim as builder

WORKDIR /app
COPY . .
RUN ./install-packages.sh
RUN npm ci --omit=dev

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY --from=builder /app /app
ENV PATH="/app:$PATH"

ENTRYPOINT []
CMD importer.sh ; python3 app.py
