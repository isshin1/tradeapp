#!/bin/bash
cd /home/kushy/PycharmProjects/TradeApp
docker rm -f tradeapp
docker compose build && docker compose up -d
#docker compose build --no-cache && docker compose up -d

#
#docker build  --dns=8.8.8.8 -t tradeapp .
#
#docker run -d \
#  --name tradeapp \
#  -v "$(pwd)/data:/app/data" \
#  -v /var/run/docker.sock:/var/run/docker.sock \
#  -v /etc/localtime:/etc/localtime:ro \
#  -e TZ=Asia/Kolkata \
#  -p 8000:8000 \
#  --dns=1.1.1.1 \
#  --dns=8.8.8.8 \
#  --restart always \
#  tradeapp-image-name