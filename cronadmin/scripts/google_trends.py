#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
from pytrends.request import TrendReq
import mysql.connector
import time
import random
import os
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
MAX_RETRIES = 3
RETRY_WAIT = 10
REGION = 'DE'
ZEITFENSTER = "now 1-H"

def fetch_and_store_trends():
    start_time = datetime.now()
    logger.info("=== Trend-Skript gestartet ===")

    pytrends = TrendReq(hl='DE', tz=360)

    zeitpunkt = datetime.utcnow().replace(second=0, microsecond=0) + timedelta(hours=1) # UTC+1
    logger.info("Verwende Zeitstempel: %s", zeitpunkt)

    # Datenbankverbindung
    DB_CONFIG = {
        "host": os.getenv("DB_HOST"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME")
    }
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Zeitstempel in Dim_Datum eintragen oder holen
    cursor.execute("SELECT datum_id FROM Dim_Datum WHERE datum = %s", (zeitpunkt,))
    result = cursor.fetchone()
    if result:
        datum_id = result[0]
    else:
        cursor.execute("""
            INSERT INTO Dim_Datum (datum, jahr, quartal, monat, woche, tag, wochentag, stunde, minute)
            VALUES (%s, YEAR(%s), QUARTER(%s), MONTH(%s), WEEK(%s), DAY(%s), DAYNAME(%s), HOUR(%s), MINUTE(%s))
        """, (zeitpunkt,) * 9)
        conn.commit()
        datum_id = cursor.lastrowid

    # Produkte abrufen
    cursor.execute("SELECT produkt_id, name FROM Dim_Produkt")
    produkte = cursor.fetchall()

    trend_insert_values = []
    fehlgeschlagene_produkte = []

    for produkt_id, produkt_name in produkte:
        time.sleep(2)
        success = False
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info("→ Rufe Trends für: %s", produkt_name)
                pytrends.build_payload([produkt_name], cat=0, timeframe=ZEITFENSTER, geo=REGION)
                data = pytrends.interest_over_time()

                if data.empty:
                    logger.info("Keine Daten für %s", produkt_name)
                    fehlgeschlagene_produkte.append(produkt_name)
                    break

                if 'isPartial' in data.columns:
                    data = data.drop(columns=['isPartial'])

                trend_score = int(data[produkt_name].mean())
                trend_insert_values.append((datum_id, produkt_id, trend_score, REGION))
                logger.info("Trendwert für %s: %d", produkt_name, trend_score)

                success = True
                break
            except Exception as e:
                if 'code 400' in str(e):
                    logger.warning("Keyword ungültig für Trends: %s", produkt_name)
                    break
                logger.warning("Fehler bei %s (Versuch %d): %s", produkt_name, attempt, e)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_WAIT)

        if not success:
            trend_insert_values.append((datum_id, produkt_id, 0, REGION))
            logger.info("→ Kein Trendwert für %s – 0 eingetragen.", produkt_name)

    # Einfügen in DB
    if not TEST_MODE:
        if trend_insert_values:
            cursor.executemany("""
                INSERT INTO Dim_Trend (datum_id, produkt_id, trend_score, region)
                VALUES (%s, %s, %s, %s)
            """, trend_insert_values)
            conn.commit()
            logger.info("%d Trendwerte gespeichert.", len(trend_insert_values))
        else:
            logger.info("Keine Trendwerte zum Speichern.")
    else:
        logger.info("TEST_MODE aktiv – keine Datenbankänderungen durchgeführt.")

    cursor.close()
    conn.close()

    # Zusammenfassung
    duration = (datetime.now() - start_time).total_seconds()
    logger.info("=== Skript beendet in %.2f Sekunden ===", duration)
    logger.info("Erfolgreiche Produkte: %d", len(trend_insert_values))
    logger.info("Fehlgeschlagene Produkte (%d): %s", len(fehlgeschlagene_produkte), ", ".join(fehlgeschlagene_produkte) or "-")

if __name__ == "__main__":
    fetch_and_store_trends()
