FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Source is bind-mounted at runtime for hot reload; copy here for image-only builds
COPY . .

CMD ["python", "run.py"]
