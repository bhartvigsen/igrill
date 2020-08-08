FROM python:3-alpine

RUN apk add --update alpine-sdk glib-dev

WORKDIR /usr/src/igrill

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./
VOLUME config 

CMD [ "python", "./monitor.py", "-c", "config" ]
