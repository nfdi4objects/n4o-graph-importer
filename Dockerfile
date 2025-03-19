FROM node:bookworm

WORKDIR /app

# Install Debian packages
COPY install-packages.sh .
RUN ./install-packages.sh

# Copy and install node dependencies
COPY package*.json ./
RUN npm ci --omit=dev

# Copy scripts
COPY load-collection .
COPY load-collection-metadata .
COPY load-rdf-graph .
COPY sparql-update .

COPY collection-context.json .

ENTRYPOINT /usr/bin/bash
# TODO
CMD ["load-collection"]
