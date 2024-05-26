# Pull the latest changes from the repository
git pull

# Install the latest dependencies
pip install -r requirements.txt

# Build the api
cargo build --release

# Clear the console and print the message
clear
echo "Cleanup complete"