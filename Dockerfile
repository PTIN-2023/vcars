FROM python:3.9

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

ENTRYPOINT ["python3", "-u", "virtualCar.py"]

CMD ["--id", "1"]

# docker logs -f virtual-car-1