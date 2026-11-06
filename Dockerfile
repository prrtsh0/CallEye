FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Train the ML classifier during the image build. model.joblib is git-ignored,
# so a fresh image must generate it from the committed training data.
RUN python -m eval.train

ENV PORT=8000
ENV GNANI_MODE=mock

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
