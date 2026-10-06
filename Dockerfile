FROM node:22-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY --from=frontend-build /frontend/dist /app/web
COPY . .
COPY --from=frontend-build /frontend/dist /app/web
RUN pip install --no-cache-dir '.[server]'
ENV CLINIAR_DATABASE_URL=postgresql+psycopg://cliniar:cliniar@db:5432/cliniar
ENV CLINIAR_WEB_ROOT=/app/web
EXPOSE 8787
CMD ["sh", "-c", "cliniar-serve migrate && cliniar-serve serve --host 0.0.0.0 --port 8787"]
