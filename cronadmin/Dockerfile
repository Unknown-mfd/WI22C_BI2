FROM node:14

RUN apt-get update && apt-get install -y \
    cron \
    python3 \
    python3-pip \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    python3-dev \
    dos2unix \
 && apt-get clean

WORKDIR /app

# Kopiere alle Projektdateien inkl. package.json
COPY . /app

# Upgrade von pip, setuptools und wheel
RUN pip3 install --upgrade pip setuptools wheel

RUN pip3 install -r requirements.txt
RUN npm install

# Konvertiere die crontab-Datei in Unix-Zeilenenden und installiere sie
RUN dos2unix crontab && chmod 0644 crontab && crontab crontab

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

VOLUME ["/app/cronadmin/logs"]

EXPOSE 4000

CMD ["/entrypoint.sh"]
