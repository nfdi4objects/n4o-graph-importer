FROM nikolaik/python-nodejs:latest
WORKDIR /app
COPY package.json .
COPY package-lock.json .
COPY install-packages.sh .
RUN ./install-packages.sh
RUN npm ci --omit=dev

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
ENV PATH="/app:$PATH"
COPY . .

ENTRYPOINT []
CMD ["start.sh"]
