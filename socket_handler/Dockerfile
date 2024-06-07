FROM python:3.12-slim

RUN mkdir /opt/app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY socket_handler.py /opt/app/socket_handler.py

WORKDIR /opt/app/

EXPOSE 8008

CMD ["python","/opt/app/socket_handler.py"]
