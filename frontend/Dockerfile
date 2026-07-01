# Build stage
FROM node:20-alpine AS builder
WORKDIR /app

ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_SUPERSET_URL=http://localhost:8088
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_SUPERSET_URL=$VITE_SUPERSET_URL

COPY package.json .
RUN npm install

COPY . .
RUN npm run build

# Serve stage
FROM nginx:1.25-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
