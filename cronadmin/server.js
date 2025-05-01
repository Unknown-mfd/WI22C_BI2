// server.js
const express = require('express');
const fs = require('fs');
const { spawn } = require('child_process');
const bodyParser = require('body-parser');
const path = require('path');
const dotenv = require('dotenv');
const http = require('http');
const socketIo = require('socket.io');

// Lade Umgebungsvariablen (z. B. aus ../.env)
dotenv.config({ path: path.join(__dirname, '../.env') });

const app = express();
const port = 4000;

app.use(bodyParser.json());
app.use(express.static('public'));

// GET /api/pipelines – liefert den Inhalt der pipelines.json
app.get('/api/pipelines', (req, res) => {
  const pipelinesPath = path.join(__dirname, 'pipelines.json');
  fs.readFile(pipelinesPath, 'utf8', (err, data) => {
    if (err) return res.status(500).json({ error: 'Unable to read pipelines.json' });
    res.json(JSON.parse(data));
  });
});

// POST /api/pipelines/:name/update – aktualisiert den Zeitplan und generiert die crontab neu
app.post('/api/pipelines/:name/update', (req, res) => {
  const pipelineName = req.params.name;
  const updateData = req.body;
  const pipelinesPath = path.join(__dirname, 'pipelines.json');

  fs.readFile(pipelinesPath, 'utf8', (err, raw) => {
    if (err) return res.status(500).json({ error: 'Unable to read pipelines.json' });
    const pipelines = JSON.parse(raw);
    if (!pipelines[pipelineName]) {
      return res.status(404).json({ error: `Pipeline "${pipelineName}" not found` });
    }
    pipelines[pipelineName] = { ...pipelines[pipelineName], ...updateData };

    fs.writeFile(pipelinesPath, JSON.stringify(pipelines, null, 2), (err) => {
      if (err) return res.status(500).json({ error: 'Unable to update pipelines.json' });
      updateCrontab(pipelines);
      res.json({ message: 'Pipeline updated', pipeline: pipelines[pipelineName] });
    });
  });
});

// HTTP-Server und Socket.IO einrichten
const server = http.createServer(app);
const io = socketIo(server);

// Globales Objekt, um laufende Pipelines zu verfolgen
const runningPipelines = {};

// Socket.IO: Manuelle Pipeline-Auslösung (mit Single-Run-Schutz)
io.on('connection', (socket) => {
  console.log('Client connected via Socket.IO');

  socket.on('runPipeline', (data) => {
    const pipelineName = data.name;
    const scriptPath = path.join(__dirname, 'scripts', `${pipelineName}.py`);

    if (!fs.existsSync(scriptPath)) {
      socket.emit('pipelineOutput', `Error: Script ${pipelineName}.py not found.\n`);
      return;
    }

    if (runningPipelines[pipelineName]) {
      socket.emit('pipelineOutput', `Error: Pipeline "${pipelineName}" is already running. Please wait until it finishes.\n`);
      return;
    }

    const proc = spawn('python3', [scriptPath]);
    runningPipelines[pipelineName] = proc;

    proc.stdout.on('data', (chunk) => {
      socket.emit('pipelineOutput', chunk.toString());
    });
    proc.stderr.on('data', (chunk) => {
      socket.emit('pipelineOutput', chunk.toString());
    });
    proc.on('close', (code) => {
      socket.emit('pipelineOutput', `\nScript ${pipelineName}.py exited with code ${code}\n`);
      delete runningPipelines[pipelineName];
    });
  });
});

// Funktion zum Aktualisieren der crontab basierend auf pipelines.json
function updateCrontab(pipelines) {
  let newCrontab = '';
  for (const name in pipelines) {
    const schedule = pipelines[name].schedule;
    newCrontab += `${schedule} python3 /app/scripts/${name}.py >> /app/logs/cron.log 2>&1\n`;
  }
  const crontabPath = path.join(__dirname, 'crontab');
  fs.writeFile(crontabPath, newCrontab, (err) => {
    if (err) {
      console.error('Error writing crontab file:', err);
    } else {
      const cronInstall = spawn('crontab', [crontabPath]);
      cronInstall.on('close', (code) => {
        if (code !== 0) {
          console.error(`crontab installation failed with code ${code}`);
        } else {
          console.log('crontab updated successfully.');
        }
      });
    }
  });
}

// Starte den Server
server.listen(port, () => {
  console.log(`Server running on port ${port}`);
});
