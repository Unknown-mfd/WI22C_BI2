#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import mysql.connector
from dotenv import load_dotenv
from sklearn.linear_model import LinearRegression

# === Logging ===
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

# === Konfiguration ===
load_dotenv()
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

def fetch_preisdaten(conn, produkt_id):
    query = """
        SELECT d.datum, p.preis
        FROM Dim_Preisentwicklung p
        JOIN Dim_Datum d ON p.datum_id = d.datum_id
        WHERE p.produkt_id = %s AND p.anbieter = 'Amazon'
        ORDER BY d.datum ASC
    """
    df = pd.read_sql(query, conn, params=(produkt_id,))
    return df

def ensure_datum_id(conn, datum):
    cursor = conn.cursor(buffered=True)
    cursor.execute("SELECT datum_id FROM Dim_Datum WHERE datum = %s", (datum,))
    row = cursor.fetchone()
    if row:
        return row[0]
    else:
        cursor.execute("""
            INSERT INTO Dim_Datum (datum, jahr, quartal, monat, woche, tag, wochentag, stunde, minute)
            VALUES (%s, YEAR(%s), QUARTER(%s), MONTH(%s), WEEK(%s), DAY(%s), DAYNAME(%s), HOUR(%s), MINUTE(%s))
        """, (datum,) * 9)
        conn.commit()
        return cursor.lastrowid

def speichere_prognose(conn, produkt_id, datum_id, preis):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM Dim_Prognose
        WHERE produkt_id = %s AND datum_id = %s
    """, (produkt_id, datum_id))
    if cursor.fetchone():
        logger.info("Prognose existiert bereits für Produkt %s am Datum %s", produkt_id, datum_id)
        return

    cursor.execute("""
        INSERT INTO Dim_Prognose (produkt_id, datum_id, voraussichtlicher_preis)
        VALUES (%s, %s, %s)
    """, (produkt_id, datum_id, round(preis, 2)))
    conn.commit()
    logger.info("Prognose gespeichert für Produkt %s: %.2f €", produkt_id, preis)

def main():
    logger.info("Starte Prognose-Skript...")

    conn = mysql.connector.connect(**DB_CONFIG)

    # Produkte holen
    cursor = conn.cursor()
    cursor.execute("SELECT produkt_id FROM Dim_Produkt")
    produkte = [row[0] for row in cursor.fetchall()]
    cursor.close()

    morgen = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    datum_id = ensure_datum_id(conn, morgen)

    for produkt_id in produkte:
        df = fetch_preisdaten(conn, produkt_id)
        if df.shape[0] < 5:
            logger.warning("Nicht genug Daten für Produkt %s", produkt_id)
            continue

        df["timestamp"] = pd.to_datetime(df["datum"])
        df["tage"] = (df["timestamp"] - df["timestamp"].min()).dt.days
        X = df[["tage"]].values
        y = df["preis"].values

        model = LinearRegression()
        model.fit(X, y)

        morgen_tag = (morgen - df["timestamp"].min()).days
        prognose = model.predict([[morgen_tag]])[0]
        speichere_prognose(conn, produkt_id, datum_id, prognose)

    conn.close()
    logger.info("Prognose abgeschlossen.")

if __name__ == "__main__":
    main()
