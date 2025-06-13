#!/bin/bash

# Ensure the cards.json file exists
if [ ! -f "cards.json" ]; then
    echo "Downloading cards data..."
    python3 -m killua --download
    echo "Cards data downloaded successfully."
fi

PS3='Please enter your choice: '
options=("Run bot in production environment" "Run bot in development environment" "Setup database" "Download cards data" "Run tests" "Quit")

select opt in "${options[@]}"
do
    case $REPLY in
        "1")
            echo "Starting bot in production environment..."
            hypercorn killua/webhook/api:app --bind 127.0.0.1:$(python3 -c "from killua.static.constants import PORT; print(PORT)") --debug & python3 -m killua
            break
            ;;
        "2")
            echo "Starting bot in development environment..."
            python3 -m killua --development
            break
            ;;
        "3")
            echo "Setting up database..."
            python3 setup.py
            break
            ;;
        "4")
            echo "Downloading cards data..."
            python3 -m killua --download
            echo "Cards data downloaded successfully."
            break
            ;;
        "5")
            echo "Running tests..."
            python3 -m killua --test
            break
            ;;
        "6")
            echo "Exiting..."
            break
            ;;
        *) echo "Invalid option $REPLY. Please try again.";
           continue
           ;;
    esac
done

echo "Process terminated"