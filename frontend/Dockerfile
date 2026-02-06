# Stage 1: Build
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies first (better caching)
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

# Copy source code
COPY . .

# VITE_API_URL is baked into the bundle at build time
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Cache buster - change this to force rebuild
ARG CACHE_BUST=2026-02-06-v5-debug
RUN echo "Build: $CACHE_BUST" && npm run build

# Stage 2: Serve with nginx
FROM nginx:1.27-alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our nginx config template
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Copy built assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Railway sets PORT dynamically; nginx template uses $PORT via envsubst
# nginx:alpine image auto-processes /etc/nginx/templates/*.template files
# replacing $PORT with the env var value

EXPOSE 8080
ENV PORT=8080

CMD ["nginx", "-g", "daemon off;"]
