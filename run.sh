PS3='Please enter your choice: '
options=("Run bot in production environment" "Run bot in development environment" "Setup database" "Quit")
select opt in "${options[@]}"
do
    case $REPLY in
        "1")
             MODE=prod docker compose up -d --build
            break
            ;;
        "2")
            docker compose up -d --build
            break
            ;;
        "3")
            python3 setup.py
            break
            ;;
        "4")
            break
            ;;
        *) echo "invalid option $REPLY";;
    esac
done

echo "Process terminated, make sure you run cleanup.sh before re-running the bot in production."