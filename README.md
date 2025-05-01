# Refurbished Laptop Shop Dashboard

## Projektübersicht

Dieses Projekt stellt eine webbasierte Analyseplattform für einen Händler gebrauchter Laptops dar. Es kombiniert eine Frontend-Anwendung, einen Node.js-Backend-Service, eine MariaDB-Datenbank, eine Grafana-Integration für Visualisierungen und ein Cron-basiertes Admin-Panel zur Verwaltung von Pipelines und Aufgaben.

## Projektstruktur

```
WI22C_BI/
├── docker-compose.yml      # Definition aller Docker-Services
├── .env                    # Umgebungsvariablen
├── db/
│   ├── init/              # SQL-Init-Skripte 
│   └── data/              # Bind-Mount für Persistenz
├── online_store/
│   ├── frontend/          # CSS, HTML, Java-Script
│   └── backend/           # Node.js-Backend mit REST-API
├── dashboard/
│   └── provisioning/      # Grafana-Provisioning (Datasources, Dashboards)
├── cronadmin/             # Python-Skripte und UI für geplante Aufgaben
├── docs/                  # Dokumentation für das Projekt
└── README.md              # Dieses Dokument
```

## Voraussetzungen

- **Docker/Docker Compose**
- **Python 3.x**

## Installation & Start

1. **Repository klonen**

   ```bash
   git clone https://github.com/Unknown-mfd/WI22C_BI2
   cd WI22C_BI
   ```

2. **End of Line Sequence umstellen**
  
    Die Datei cronadmin/entrypoint.sh ist standartmäßig im Modus `CLRF`. Das kann zu einem Fehler führen. Richtig ist es `LF` zu verwedenden. Bei VS Code ist es am Rand rechts unten.


3. **Services starten**

   ```bash
   docker-compose up --build -d
   ```

4. **Zugriff**

   - Frontend:         [http://localhost:8080](http://localhost:8080)
   - Backend-API:      [http://localhost:5001](http://localhost:5001)
   - Grafana:          [http://localhost:3000](http://localhost:3000) (Anmeldung: admin/admin)
   - CronAdmin-Panel:  [http://localhost:4000](http://localhost:4000)

## Komponenten im Detail

### Datenbank (MariaDB)

- Init-Verzeichnis `db/init` enthält:
  1. `01-dump.sql`: Schema und Daten-Dump

  2. `02-dim_datum_full.sql`: Einmaliges Füllen der Tabelle `Dim_Datum_Full`
- Bei Erststart werden alle Skripte in /docker-entrypoint-initdb.d ausgeführt.

### Backend (Node.js)

- Endpunkte:
  - `/api/products`          – Produktdaten abrufen
  - `/api/orders`            – Bestellungen verwalten
  - `/api/dim_datum_full`    – Vollständige Datumsansicht
  - Konfiguration über Umgebungsvariablen und `.env`-Datei.

### Frontend

- Single-Page-App mit Produktübersicht, Detailseiten und Warenkorb.
- Entwickelt mit JavaScript, Css und Html.

### Grafana Dashboard

- Automatische Provisioning-Dateien in `dashboard/provisioning`:
  - `datasources/mysql.yaml` stellt Verbindung zur MariaDB her.
  - Dashboard-Definitionen visualisieren Lagerbestand, Verkaufszahlen, Zeitreihen.

### CronAdmin

- Eigenständiges Admin-Panel zur Steuerung von ETL-Pipelines:
  - Python-Skripte in `cronadmin/` verarbeiten Daten automatisiert.
  - UI unter [http://localhost:4000](http://localhost:4000) zeigt Log-Ausgaben und Task-Status.

## Fehlerbehebung

- **Datenbankprobleme**: Volumes löschen mit `docker-compose down -v` und DB-Ordner `db/data` manuell leeren.
- **Grafana-Verbindung**: Prüfe `DB_HOST`, `DB_PORT` und Nutzerrechte (Grant-Skript in `db/init`).
- **View liefert keine Daten**: Stelle sicher, dass `Dim_Datum`-Tabelle gefüllt ist und `USE DB_NAME;` im Dump steht.
- **entrypoint.sh funktioniert nicht**: End of Line Sequence muss zu `LF` umgestellt werden
