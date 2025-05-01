#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timezone, timedelta
import os
import time
import requests
import pandas as pd
import mysql.connector
from dotenv import load_dotenv

# === Logging ===
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

log_dir = os.path.join(os.path.dirname(__file__), '../logs')
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, 'cron.log')
fh = logging.FileHandler(log_file_path)
fh.setLevel(logging.WARNING)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
fh.setFormatter(formatter)
logger.addHandler(ch)
logger.addHandler(fh)

# === Konfiguration ===
load_dotenv()
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}
API_KEY = os.getenv("NEWSAPI_KEY")
NEWSAPI_URL = "https://newsapi.org/v2/everything"
MAX_REQUESTS_PER_RUN = 20

def get_limited_names_from_db(limit):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM Dim_Produkt ORDER BY name ASC LIMIT %s", (limit,))
    namen = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return namen

def fetch_news(keyword):
    MAX_RETRIES = 3
    RETRY_WAIT = 60

    start_datum = datetime.now(timezone.utc) - timedelta(hours=2) # 2 Stunden zurück
    params = {
        "q": keyword,
        "apiKey": API_KEY,
        "language": "de",
        "sortBy": "publishedAt",
        "pageSize": 5,
        "from": start_datum.isoformat(timespec='seconds') + "Z"
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("(%d/3) Anfrage für News: %s", attempt, keyword)
            response = requests.get(NEWSAPI_URL, params=params, timeout=10)
            if response.status_code == 200:
                return response.json().get("articles", [])
            else:
                logger.warning("Fehlerstatus %s bei Anfrage für '%s'", response.status_code, keyword)
        except Exception as e:
            logger.error("Fehler bei '%s': %s", keyword, e)
        if attempt < MAX_RETRIES:
            logger.warning("Warte %d Sekunden...", RETRY_WAIT)
            time.sleep(RETRY_WAIT)
        else:
            logger.error("Abbruch nach 3 Fehlversuchen für: %s", keyword)
    return []

def save_news(news_data):
    if TEST_MODE:
        df = pd.DataFrame(news_data)
        df.to_csv("news_test.csv", index=False, encoding='utf-8')
        logger.info("Testdaten gespeichert: news_test.csv")
        return

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    for news in news_data:
        cursor.execute("SELECT produkt_id FROM Dim_Produkt WHERE name = %s LIMIT 1", (news['produkt'],))
        produkt_result = cursor.fetchone()
        if not produkt_result:
            logger.warning("Kein Produkt gefunden für '%s'", news['produkt'])
            continue
        produkt_id = produkt_result[0]

        try:
            published_dt = datetime.strptime(news["datum"], "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            logger.error("Ungültiges Datumsformat: %s", news["datum"])
            continue

        zeitpunkt = published_dt.replace(second=0, microsecond=0)
        datum_str = zeitpunkt.strftime('%Y-%m-%d %H:%M:%S')
        jahr = zeitpunkt.year
        quartal = (zeitpunkt.month - 1) // 3 + 1
        monat = zeitpunkt.month
        woche = zeitpunkt.isocalendar()[1]
        tag = zeitpunkt.day
        wochentag = zeitpunkt.strftime("%A")
        stunde = zeitpunkt.hour
        minute = zeitpunkt.minute

        cursor.execute("SELECT datum_id FROM Dim_Datum WHERE datum = %s", (datum_str,))
        result = cursor.fetchone()
        if result:
            datum_id = result[0]
        else:
            cursor.execute("""
                INSERT INTO Dim_Datum (datum, jahr, quartal, monat, woche, tag, wochentag, stunde, minute)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (datum_str, jahr, quartal, monat, woche, tag, wochentag, stunde, minute))
            conn.commit()
            datum_id = cursor.lastrowid
            logger.info("Neues Datum: %s mit ID %s", datum_str, datum_id)
        cursor.execute("""
            SELECT 1 FROM Dim_Nachrichten
            WHERE url = %s
            LIMIT 1
        """, (news["url"],))
        if cursor.fetchone():
            logger.info("News bereits vorhanden: %.40s...", news['titel'])
            continue

        cursor.execute("""
            INSERT INTO Dim_Nachrichten (produkt_id, datum_id, titel, quelle, url, inhalt)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (produkt_id, datum_id, news["titel"], news["quelle"], news["url"], news["inhalt"]))
    conn.commit()
    cursor.close()
    conn.close()
    logger.info("News erfolgreich gespeichert.")

def main():
    start_time = datetime.now()
    logger.info("=== News-Scraper gestartet ===")
    if TEST_MODE:
        namen = ["MacBook Air", "ThinkPad X1"]
    else:
        namen = get_limited_names_from_db(MAX_REQUESTS_PER_RUN)

    all_news = []
    requests_used = 0

    for name in namen:
        if requests_used >= MAX_REQUESTS_PER_RUN:
            break
        artikel = fetch_news(name)
        requests_used += 1
        for eintrag in artikel:
            all_news.append({
                "produkt": name,
                "datum": eintrag["publishedAt"],
                "titel": eintrag["title"],
                "quelle": eintrag["source"]["name"],
                "url": eintrag["url"],
                "inhalt": eintrag["description"][:500] if eintrag["description"] else ""
            })

    if all_news:
        save_news(all_news)
    else:
        logger.info("Keine neuen Nachrichten gefunden.")

    dauer = (datetime.now() - start_time).total_seconds()
    logger.info("=== Skript beendet in %.2f Sekunden ===", dauer)
    logger.info("Verwendete API-Requests: %d", requests_used)
    logger.info("Gefundene Artikel: %d", len(all_news))

if __name__ == "__main__":
    main()
