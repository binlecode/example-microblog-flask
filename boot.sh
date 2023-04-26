#!/bin/bash
source venv/bin/activate

# In docker-compose deployment, mysql might take a few seconds to get ready 
# for web stack to connect and apply any needed migrations.
# Use a retry loop for flask to try the database upgrade until it succeeds. 
while true; do
    flask db upgrade
    if [[ "$?" == 0 ]]; then
        break
    fi
    echo "Deploy command failed, retrying in 5 seconds ..."
    for i in {1..5}; do
        echo "$i"
        sleep 1
    done
done

exec gunicorn -b:5000 -w 4 --access-logfile - --error-logfile - microblog:app