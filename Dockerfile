FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /srv
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=web /web/dist ./backend/static
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "--app-dir", "backend/app", "main:app", "--host", "0.0.0.0", "--port", "8000"]
