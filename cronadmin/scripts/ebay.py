#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
import random
import requests
import time
import os
import mysql.connector
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from dotenv import load_dotenv
import pandas as pd

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

# HTTP Session mit Header
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "de,en-US;q=0.7,en;q=0.3",
    "Referer": "https://www.ebay.com/"
})


def ebay_suche(suchbegriff, max_ergebnisse=10):
    encoded_query = quote_plus(suchbegriff)
    url = f"https://www.ebay.com/sch/i.html?_nkw={encoded_query}&LH_ItemCondition=3000"

    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        ergebnisse = []
        items = soup.find_all("div", class_="s-item__info", limit=max_ergebnisse)

        for item in items:
            title_tag = item.find("div", class_="s-item__title")
            preis_tag = item.find("span", class_="s-item__price")
            link_tag = item.find("a", class_="s-item__link")

            if title_tag and preis_tag and link_tag:
                preis_text = preis_tag.get_text(strip=True).replace("EUR", "").replace("$", "").replace(",", ".")
                try:
                    preis_float = float(''.join([c for c in preis_text if c.isdigit() or c == '.']))
                    if preis_float in (0.00, 20.00):
                        continue
                except:
                    continue

                ergebnisse.append({
                    "titel": title_tag.get_text(strip=True),
                    "preis": preis_float,
                    "url": link_tag["href"]
                })

        time.sleep(random.uniform(5, 10))
        return ergebnisse
    except Exception as e:
        logger.error(f"Fehler bei eBay-Suche: {e}")
        return []


def fetch_and_store_ebay_data():
    start_time = datetime.now()
    logger.info("=== eBay-Scraper gestartet ===")
    if TEST_MODE:
        logger.info("TEST_MODE aktiv – keine Datenbankeinträge.")

    zeitpunkt = datetime.utcnow().replace(second=0, microsecond=0) + timedelta(hours=1) # UTC+1
    logger.info("Verwende Zeitstempel: %s", zeitpunkt)

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Datumseintrag vorbereiten
    cursor.execute("SELECT datum_id FROM Dim_Datum WHERE datum = %s", (zeitpunkt,))
    result = cursor.fetchone()
    if result:
        datum_id = result[0]
    else:
        cursor.execute("""
            INSERT INTO Dim_Datum (datum, jahr, quartal, monat, woche, tag, wochentag, stunde, minute)
            VALUES (%s, YEAR(%s), QUARTER(%s), MONTH(%s), WEEK(%s), DAY(%s), DAYNAME(%s), HOUR(%s), MINUTE(%s)
        )""", (zeitpunkt,) * 9)
        conn.commit()
        datum_id = cursor.lastrowid
        logger.info("Neuer Dim_Datum-Eintrag: ID %s", datum_id)

    cursor.execute("SELECT produkt_id, name FROM Dim_Produkt")
    produkte = cursor.fetchall()

    gesamt_ergebnisse = []
    fehlgeschlagen = []

    for produkt_id, produkt_name in produkte:
        logger.info("→ Suche eBay nach: %s", produkt_name)
        ergebnisse = ebay_suche(produkt_name)

        if not ergebnisse:
            logger.info("Keine gültigen Einträge für '%s' gefunden.", produkt_name)
            fehlgeschlagen.append(produkt_name)
            continue

        # Nur günstigstes Ergebnis speichern
        guenstigstes = min(ergebnisse, key=lambda x: x["preis"])
        gesamt_ergebnisse.append((
            produkt_id,
            datum_id,
            guenstigstes["preis"],
            "eBay",
            guenstigstes["url"]
        ))
        logger.info("Günstigster Preis für %s: %.2f EUR", produkt_name, guenstigstes["preis"])


    if TEST_MODE:
        if gesamt_ergebnisse:
            df = pd.DataFrame(gesamt_ergebnisse, columns=["produkt_id", "datum_id", "preis", "anbieter", "url"])
            df.to_csv("ebay_preise_test.csv", index=False)
            logger.info("Testdaten gespeichert in ebay_preise_test.csv")
    else:
        if gesamt_ergebnisse:
            cursor.executemany("""
                INSERT INTO Dim_Preisentwicklung (produkt_id, datum_id, preis, anbieter, url)
                VALUES (%s, %s, %s, %s, %s)
            """, gesamt_ergebnisse)
            conn.commit()
            logger.info("%d Preis-Einträge gespeichert.", len(gesamt_ergebnisse))
        else:
            logger.info("Keine Daten zum Speichern vorhanden.")

    cursor.close()
    conn.close()

    dauer = (datetime.now() - start_time).total_seconds()
    logger.info("=== Skript beendet in %.2f Sekunden ===", dauer)
    logger.info("Erfolgreiche Produkte: %d", len(set(r[0] for r in gesamt_ergebnisse)))
    logger.info("Fehlgeschlagen (%d): %s", len(fehlgeschlagen), ", ".join(fehlgeschlagen) or "-")


if __name__ == "__main__":
    fetch_and_store_ebay_data()
