# Kill what is running on the port specified docker-compose.yaml services.api.ports: x:y
port=$(python3 -c "import yaml; print(yaml.safe_load(open('docker-compose.yaml'))['services']['api']['ports'][0].split(':')[0])")
echo $port
pid=$(lsof -t -i:$port)
if [ -n "$pid" ]; then
  kill $pid
else
  echo "No process found running on port $port"
fi
echo "Cleanup complete"