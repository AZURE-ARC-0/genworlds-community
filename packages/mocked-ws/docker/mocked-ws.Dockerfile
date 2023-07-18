FROM python:3.11.3-slim

WORKDIR /app

# COPY packages/mocked-ws/requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# Install genworlds in editable mode
RUN pip install -e /genworlds

RUN pip install debugpy

COPY packages/mocked-ws/app/ app/

EXPOSE 7455

CMD ["sh", "-c", "python -u -m debugpy --listen 0.0.0.0:5680 -m uvicorn --reload --host 0.0.0.0 --port 7455 app.main:app"]