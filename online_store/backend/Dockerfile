# Verwende ein offizielles Node.js-Image
FROM node:23-slim

# Setze das Arbeitsverzeichnis im Container
WORKDIR /app

# Kopiere package.json und package-lock.json zuerst (um den Cache optimal zu nutzen)
COPY package*.json ./

# Installiere die Abhängigkeiten
RUN npm install

# Kopiere den gesamten Backend-Code ins Arbeitsverzeichnis
COPY . .

# Exponiere den Port, den das Backend nutzt
EXPOSE 5001

# Starte den Server
CMD ["npm", "start"]
