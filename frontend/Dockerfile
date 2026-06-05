# Stage 1: Build React static assets in Node container
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency mappings
COPY package.json ./

# Install dependencies
RUN npm install

# Copy frontend source files
COPY . .

# Compile optimized static bundle
RUN npm run build

# Stage 2: Distribute static assets to shared Caddy folder
FROM alpine:latest

WORKDIR /web

# Copy compiled files from builder stage
COPY --from=builder /app/dist /web

# On start, copy compiled files to the mounted share volume and terminate
CMD ["sh", "-c", "echo 'Exporting compiled static assets...' && mkdir -p /dist && cp -rf /web/* /dist/ && echo 'Static assets exported successfully!'"]
