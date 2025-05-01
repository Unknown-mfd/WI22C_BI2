// pipelines.js

// Stelle eine Socket.IO-Verbindung her
const socket = io();

// Funktion zum Laden der Pipeline-Karten
function loadPipelines() {
  fetch('/api/pipelines')
    .then(response => response.json())
    .then(data => {
      const container = document.querySelector('.cards-container');
      container.innerHTML = '';
      for (const name in data) {
        const pipeline = data[name];
        const card = document.createElement('div');
        card.className = 'pipeline-card';

        // Pipeline-Name
        const header = document.createElement('h3');
        header.textContent = name;
        card.appendChild(header);

        // Zeitplan-Eingabe
        const scheduleLabel = document.createElement('label');
        scheduleLabel.textContent = 'Zeitplan:';
        const inputSchedule = document.createElement('input');
        inputSchedule.type = 'text';
        inputSchedule.value = pipeline.schedule;
        scheduleLabel.appendChild(inputSchedule);
        card.appendChild(scheduleLabel);

        // Aktionen: Run & Save
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'actions';

        // Run-Button: Löst das Socket.IO-Event "runPipeline" aus
        const runButton = document.createElement('button');
        runButton.textContent = 'Run';
        runButton.onclick = () => {
          // Leere den Live-Output-Bereich
          document.getElementById('liveOutput').value = '';
          socket.emit('runPipeline', { name: name });
        };
        actionsDiv.appendChild(runButton);

        // Save-Button: Aktualisiert den Zeitplan
        const saveButton = document.createElement('button');
        saveButton.textContent = 'Save';
        saveButton.onclick = () => {
          const updateData = { schedule: inputSchedule.value };
          fetch(`/api/pipelines/${name}/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updateData)
          })
          .then(response => response.json())
          .then(data => {
            appendOutput(`Pipeline "${name}" updated: ${data.message}\n`);
          })
          .catch(err => {
            appendOutput(`Error updating "${name}": ${err}\n`);
          });
        };
        actionsDiv.appendChild(saveButton);

        card.appendChild(actionsDiv);
        container.appendChild(card);
      }
    })
    .catch(err => appendOutput(`Error loading pipelines: ${err}\n`));
}

// Funktion, um Nachrichten im Live-Output anzuzeigen
function appendOutput(msg) {
  const outputArea = document.getElementById('liveOutput');
  outputArea.value += msg;
  outputArea.scrollTop = outputArea.scrollHeight;
}

// Socket.IO: Live-Output empfangen
socket.on('pipelineOutput', (data) => {
  appendOutput(data);
});

// Initialisierung beim Laden der Seite
document.addEventListener('DOMContentLoaded', () => {
  loadPipelines();
});
