#!/bin/bash

# Load configuration from .sync_config
if [ -f ".sync_config" ]; then
    source .sync_config
else
    echo "Configuration file .sync_config not found. Exiting."
    exit 1
fi

# Ensure the current branch is main
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "Current branch is '$CURRENT_BRANCH'. Sync will only occur on 'main'."
    exit 0
fi

# Function to sync files (e.g., cards.json)
sync_file() {
    local file_path=$1
    local remote_path="$REMOTE_BASE_PATH/$(basename $file_path)"
    echo "Syncing $file_path to $remote_path on $REMOTE_HOST"
    if [ "$USE_SSH_KEY" = "true" ]; then
        scp -i "$SSH_KEY_PATH" "$file_path" "$REMOTE_USER@$REMOTE_HOST:$remote_path"
    else
        scp "$file_pat" "$REMOTE_USER@$REMOTE_HOST:$remote_path"
    fi
}

# Function to sync folders (e.g., assets/hugs or assets/cards)
sync_folder() {
    local folder_path=$1
    local remote_path="$REMOTE_BASE_PATH/assets/"
    if [ -d "assets/$folder_path" ]; then
        echo "Syncing folder assets/$folder_path to $remote_path$folder_path on $REMOTE_HOST"
        if [ "$USE_SSH_KEY" = "true" ]; then
            scp -i "$SSH_KEY_PATH" -r "assets/$folder_path" "$REMOTE_USER@$REMOTE_HOST:$remote_path"
        else
            scp -r "assets/$folder_path" "$REMOTE_USER@$REMOTE_HOST:$remote_path"
        fi
    else
        echo "assets/$folder_path does not exist. Skipping."
    fi
}

# Double confirmation before syncing
echo "WARNING: This action could override files on the remote server."

# Sync option menu
echo "Select what you would like to sync:"
echo "1. all - Sync all gitignored folders and cards.json"
echo "2. images - Sync all gitignored image folders (hugs, cards)"
echo "3. hugs - Sync gitignored hug images (assets/hugs/*)"
echo "4. cards-images - Sync gitignored cards images (assets/cards/*)"
echo "5. cards-json - Sync cards.json"
echo "6. none/abort - Do not sync anything"

read -p "Enter your choice (1/2/3/4/5/6): " choice

case $choice in
    1)
        # Sync all folders and cards.json
        sync_file "cards.json"
        sync_folder "hugs"
        sync_folder "cards"
        ;;
    2)
        # Sync all image folders
        sync_folder "hugs"
        sync_folder "cards"
        ;;
    3)
        # Sync hug images
        sync_folder "hugs"
        ;;
    4)
        # Sync cards images
        sync_folder "cards"
        ;;
    5)
        # Sync cards.json only
        sync_file "cards.json"
        ;;
    6)
        # Abort sync
        echo "Sync aborted. No files will be synced."
        exit 0
        ;;
    *)
        echo "Invalid choice. Sync aborted."
        exit 0
        ;;
esac

echo "Sync complete."
