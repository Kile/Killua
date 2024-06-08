# Pull the latest changes from the repository
git pull

# Install the latest dependencies
pip install -r requirements.txt

# Build the api
cargo build --release

# Clear the console and print the message
clear

# Kill what is running on the port specified in api/Rocket.toml by reading the file
port=$(python3 -c "import toml; config = toml.load('api/Rocket.toml'); print(config['release']['port'])")
pid=$(lsof -t -i:$port)
if [ -n "$pid" ]; then
  kill $pid
else
  echo "No process found running on port $port"
fi
echo "Cleanup complete"