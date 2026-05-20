FROM python:3.13-slim

WORKDIR /app

COPY req.txt .
RUN pip install --no-cache-dir -r req.txt

COPY . .

EXPOSE 8000

CMD ["python", "allo_ua/manage.py", "runserver", "0.0.0.0:8000"]