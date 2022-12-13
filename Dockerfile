FROM python:3.9

ENV DASH_DEBUG_MODE True
ENV SERVER_PORT 8050

WORKDIR /app
COPY requirements.txt nrel_dash_components-0.0.1.tar.gz ./

RUN set -ex && \
    pip install -r requirements.txt

COPY . .

# open listening port, this may be overridden in docker-compose file
EXPOSE ${SERVER_PORT}

CMD ["python", "app.py"]
