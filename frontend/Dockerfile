# ===================================================
# Multi-Stage Production Dockerfile for Frontend Service
# Framework: React / Vite / Nginx
# ===================================================

# Stage 1: Build Vite Production Bundle
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency specifications
COPY frontend/package*.json ./

# Clean install dependencies
RUN npm ci

# Copy frontend source code
COPY frontend/ ./

# Build production bundle to /app/dist
RUN npm run build

# Stage 2: Serve via Nginx Reverse Proxy
FROM nginx:1.27-alpine AS runner

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
