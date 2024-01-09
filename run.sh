PS3='Please enter your choice: '
options=("Run bot in production environment" "Run bot in development environment" "Setup database" "Quit")
select opt in "${options[@]}"
do
    case $REPLY in
        "1")
            hypercorn killua/webhook/api:app --bind 127.0.0.1:$(python -c "from killua.static.constants import PORT; print(PORT)") --debug --access-logfile "api.log" --log-file "api.log" --workers 8 & python3 -m killua
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

echo "Process terminated"