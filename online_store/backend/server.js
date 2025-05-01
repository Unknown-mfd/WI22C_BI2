// Importiere benötigte Module
const express = require("express");
const mysql = require("mysql2");
const cors = require("cors");

const app = express();
app.use(cors());
app.use(express.json());

const path = require("path");
// Lade Umgebungsvariablen aus der .env-Datei
require("dotenv").config({ path: path.resolve(__dirname, "../../.env") });

// Verbindung zur MySQL-Datenbank herstellen
const db = mysql.createPool({
    host: process.env.DB_HOST,
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    database: process.env.DB_NAME,
});

// Endpunkt: Alle Laptops abrufen
app.get("/api/laptops", (req, res) => {
    const sql = `SELECT p.produkt_id, p.name, p.hersteller, p.modell, p.spezifikationen
                 FROM Dim_Produkt p 
                 ORDER BY p.name ASC;`;
    db.query(sql, (err, result) => {
        if (err) {
            // Fehlerantwort zurückgeben, falls die Abfrage fehlschlägt
            return res.status(500).json({ error: err.message });
        }
        // Liste der Laptops zurückgeben
        res.json(result);
    });
});

// Endpunkt: Details eines einzelnen Laptops abrufen
app.get("/api/laptop/:id", (req, res) => {
    const sql = `SELECT * FROM Dim_Produkt WHERE produkt_id = ?`;
    db.query(sql, [req.params.id], (err, result) => {
        if (err) {
            // Fehlerantwort zurückgeben, falls die Abfrage fehlschlägt
            return res.status(500).json({ error: err.message });
        }
        // Details des Laptops zurückgeben
        res.json(result[0]);
    });
});

// Endpunkt: Bestellung speichern
app.post("/api/order", (req, res) => {
    const { cart } = req.body;
    if (!cart || cart.length === 0) {
        // Fehler zurückgeben, falls der Warenkorb leer ist
        return res.status(400).json({ message: "Der Warenkorb ist leer!" });
    }

    const sql = `INSERT INTO Fakt_Verkauf (produkt_id, datum_id, anzahl_verkauft, preis) VALUES ?`;
    const values = cart.map(item => [item.id, 1, 1, item.price]);

    db.query(sql, [values], (err, result) => {
        if (err) {
            // Fehlerantwort zurückgeben, falls die Abfrage fehlschlägt
            return res.status(500).json({ error: err.message });
        }
        // Erfolgsnachricht mit Bestell-ID zurückgeben
        res.json({ message: "Bestellung erfolgreich!", orderId: result.insertId });
    });
});

// Server starten
const PORT = process.env.PORT || 5001;
app.listen(PORT, () => {
    console.log(`Backend läuft auf http://localhost:${PORT}`);
});
