FROM nikolaik/python-nodejs:latest
WORKDIR /app
COPY . .
RUN ./install-packages.sh
RUN npm ci --omit=dev

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
ENV PATH="/app:$PATH"

ENTRYPOINT []
CMD ["sh", "-c", "importer.sh ; python3 app.py"]
