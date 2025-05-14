FROM node:bookworm

WORKDIR /app

# Install Debian packages
COPY install-packages.sh .
RUN ./install-packages.sh

# Copy and install node dependencies
COPY package*.json ./
RUN npm ci --omit=dev

# Install Python dependencies
COPY requirements.txt .
RUN python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

# Copy scripts
COPY utils.sh .
COPY transform-rdf .
COPY sparql-update .
COPY load-rdf-graph .
COPY js ./js

COPY import-metadata .

COPY import-collection .
COPY update-collections .
COPY receive-collection .
COPY load-collection .
COPY load-collection-metadata .
COPY load-collections-metadata .

COPY download-zenodo .

COPY terminology-data.csv .
COPY import-terminology .
COPY update-terminologies .
COPY receive-terminology .
COPY load-terminologies-metadata .
COPY load-terminology .

COPY prefixes.json .
COPY *-context.json .

COPY importer.sh .

# Allow to directly call scripts
ENV PATH="/app:$PATH"

ENTRYPOINT []
CMD ["importer.sh"]
