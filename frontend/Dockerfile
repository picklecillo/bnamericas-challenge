FROM node:24-slim AS base
WORKDIR /app
COPY package.json package-lock.json ./

# Dev: Vite dev server; docker-compose.yml bind-mounts the source.
FROM base AS dev
RUN --mount=type=cache,target=/root/.npm npm ci
COPY . .
EXPOSE 5173
CMD ["npx", "vite", "--host", "0.0.0.0", "--port", "5173", "--strictPort"]
