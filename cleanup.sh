# Kill gunicorn daemon
pkill -f "gunicorn"

# Clear the content of the api.log file
> api.log

# Make sure the port defined in constants.py is not in use
lsof -ti:$(python -c "from killua.static.constants import PORT; print(PORT)") | xargs kill -9

# Pull the latest changes from the repository
git pull

# Install the latest dependencies
pip install -r requirements.txt

# Clear the console and print the message
clear
echo "Cleanup complete"