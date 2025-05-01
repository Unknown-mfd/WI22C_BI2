# cronadmin/entrypoint.sh
#!/bin/bash
# Start cron in the background
cron &
# Start the Node.js server
node server.js
