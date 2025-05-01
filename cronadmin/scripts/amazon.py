#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
import random
import requests
from bs4 import BeautifulSoup
import pandas as pd
import mysql.connector
import time
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
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:119.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0"
]

def scrape_amazon_prices():
    start_time = datetime.now()
    logger.info("=== Preis-Scraper gestartet ===")
    if TEST_MODE:
        logger.info("TEST_MODE ist aktiv – es werden keine Datenbankeinträge vorgenommen")

    zeitpunkt = datetime.utcnow().replace(second=0, microsecond=0) + timedelta(hours=1) # UTC+1
    logger.info("Verwende Zeitstempel: %s", zeitpunkt)

    # DB-Verbindung
    DB_CONFIG = {
        "host": os.getenv("DB_HOST"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME")
    }
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(buffered=True)

    # Datum sicherstellen
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
        logger.info("Neuer Datumseintrag erstellt: ID %s", datum_id)

    # Produktliste abrufen
    cursor.execute("SELECT produkt_id, name FROM Dim_Produkt")
    produkte = cursor.fetchall()

    daten = []
    fehlgeschlagen = []

    def scrape_amazon_price(produkt_name, hersteller=None, alternative_suche=False):
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        suchbegriff = produkt_name
        if alternative_suche:
            suchbegriff = f"Laptop {produkt_name}"

        search_url = f"https://www.amazon.de/s?k={suchbegriff.replace(' ', '+')}"
        try:
            response = requests.get(search_url, headers=headers, timeout=10)
            if response.status_code != 200:
                logger.warning("Anfrage fehlgeschlagen für %s: Status %s", suchbegriff, response.status_code)
                return None, None
            soup = BeautifulSoup(response.text, "html.parser")
            produkt_element = soup.select_one("div.s-main-slot div[data-component-type='s-search-result']")
            if not produkt_element:
                return None, None

            # Titel auslesen und prüfen
            titel_element = produkt_element.select_one("h2 span.a-text-normal")
            titel = titel_element.text.strip().lower() if titel_element else ""

            blacklist = [
                "ladekabel", "netzteil", "adapter", "akku", "batterie", "ersatzakku", "ladegerät",
                "tasche", "rucksack", "hülle", "case", "skin", "cover", "schutzfolie", "schutzglas",
                "dock", "dockingstation", "halterung", "ständer", "halter", "halterstation",
                "maus", "tastatur", "keyboard", "mousepad", "trackpad", "touchpad",
                "kabel", "usb", "usb-c", "hub", "dongle", "konverter", "verlängerung",
                "monitor", "bildschirm", "display", "externer", "projektor", "beamer",
                "lautsprecher", "boxen", "soundbar", "mikrofon", "webcam", "kamera",
                "software", "office", "lizenz", "key", "code", "abo",
                "reinigung", "spray", "tuch", "set", "werkzeug", "kit", "zubehör", "tool",
                "schloss", "kabelschloss", "sicherheitsschloss", "sicherheit", "fingerabdruck",
                "stylus", "stift", "digitizer", "pencil",
                "ersatzteil", "service", "ersatz", "reparatur", "displaykabel", "mainboard"
            ]
            
            if any(kw in titel for kw in blacklist):
                logger.info("Titel enthält Ausschlusswort: %s", titel)
                return None, None

            preis_whole = produkt_element.select_one("span.a-price-whole")
            preis_fraction = produkt_element.select_one("span.a-price-fraction")
            url_element = produkt_element.find("a", class_="a-link-normal", href=True)
            if not preis_whole or not preis_fraction or not url_element:
                return None, None

            preis_text = preis_whole.text.strip().replace('.', '').replace(',', '') + '.' + preis_fraction.text.strip()
            return float(preis_text), "https://www.amazon.de" + url_element["href"]
        except Exception as e:
            logger.warning("Fehler bei %s: %s", suchbegriff, e)
            return None, None

    for produkt_id, produkt_name in produkte:
        logger.info("→ Rufe Preis für: %s ab...", produkt_name)
        preis, url = scrape_amazon_price(produkt_name, hersteller=produkt_name.split()[0])
        if preis is None:
            logger.info("→ Neuer Versuch mit erweitertem Suchbegriff...")
            preis, url = scrape_amazon_price(produkt_name, hersteller=produkt_name.split()[0], alternative_suche=True)

        daten.append((produkt_id, datum_id, preis, "Amazon", url))
        time.sleep(5)

    if TEST_MODE:
        if daten:
            df = pd.DataFrame(daten, columns=["produkt_id", "datum_id", "preis", "anbieter", "url"])
            df.to_csv("amazon_price_test.csv", index=False, encoding='utf-8')
            logger.info("Testdaten gespeichert in amazon_price_test.csv")
    else:
        if daten:
            cursor.executemany("""
                INSERT INTO Dim_Preisentwicklung (produkt_id, datum_id, preis, anbieter, url)
                VALUES (%s, %s, %s, %s, %s)
            """, daten)
            conn.commit()
            logger.info("%d Preise gespeichert.", len(daten))
        else:
            logger.info("Keine Preiswerte zum Speichern.")

    cursor.close()
    conn.close()

    # Zusammenfassung
    dauer = (datetime.now() - start_time).total_seconds()
    logger.info("=== Skript beendet in %.2f Sekunden ===", dauer)
    logger.info("Erfolgreich gespeichert: %d", len(daten))
    logger.info("Fehlgeschlagen (%d): %s", len(fehlgeschlagen), ", ".join(fehlgeschlagen) or "-")

if __name__ == "__main__":
    scrape_amazon_prices()
