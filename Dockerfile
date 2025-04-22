FROM node:bookworm

WORKDIR /app

# Install Debian packages
COPY install-packages.sh .
RUN ./install-packages.sh

# Copy and install node dependencies
COPY package*.json ./
RUN npm ci --omit=dev

# Copy scripts
COPY utils.sh .
COPY sparql-update .
COPY load-rdf-graph .
COPY js ./js

COPY load-collection .
COPY load-collection-metadata .

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
