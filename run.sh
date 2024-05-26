PS3='Please enter your choice: '
options=("Run bot in production environment" "Run bot in development environment" "Setup database" "Quit")
select opt in "${options[@]}"
do
    case $REPLY in
        "1")
            python3 -m killua
            break
            ;;
        "2")
            python3 -m killua --development
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