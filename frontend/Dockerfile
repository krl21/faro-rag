# =============================================================================
# deps: dependencies installed from the lockfile (shared by every stage)
# =============================================================================
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# =============================================================================
# dev: Vite dev server with hot reload (`make dev`). Compose Watch syncs the
# saved files into the container and Vite reloads the browser.
# Also used to run lint, format and tests (`make lint-web`, `make test-web`).
# =============================================================================
FROM deps AS dev
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]

# =============================================================================
# build: static SPA built with Vite
# =============================================================================
FROM deps AS build
COPY . .
# The SPA calls /api on its own origin and nginx proxies it: no CORS, no URL in the code.
ARG MAX_UPLOAD_MB=20
ENV VITE_API_BASE_URL=/api \
    VITE_MAX_UPLOAD_MB=${MAX_UPLOAD_MB}
RUN npm run build

# =============================================================================
# prod (default): nginx serves the static files and proxies the API
# =============================================================================
FROM nginx:1.27-alpine AS prod
# Must be greater than MAX_UPLOAD_MB (see nginx.conf)
ARG NGINX_MAX_BODY_MB=25
ENV NGINX_MAX_BODY_MB=${NGINX_MAX_BODY_MB}

# Template: nginx substitutes ${NGINX_MAX_BODY_MB} at startup (envsubst).
# It only substitutes defined variables, so $host, $uri... stay untouched.
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
