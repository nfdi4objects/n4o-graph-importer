FROM node:bookworm

WORKDIR /app

# Install Debian packages
COPY install-packages.sh .
RUN ./install-packages.sh

# Copy and install node dependencies
COPY package*.json ./
RUN npm ci --omit=dev

# Copy scripts
COPY sparql-env .
COPY load-collection .
COPY load-collection-metadata .
COPY load-rdf-graph .
COPY sparql-update .

COPY importer.sh .

# Copy assets
COPY collection-context.json .

# Allow to directly call scripts
ENV PATH="/app:$PATH"

ENTRYPOINT []
CMD ["importer.sh"]
