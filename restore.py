#!/usr/bin/env python3
COMPOSE_CONTENT = """services:
  remnawave-db:
    image: postgres:18.1
    container_name: 'remnawave-db'
    hostname: remnawave-db
    restart: always
    ulimits:
      nofile:
        soft: 1048576
        hard: 1048576
    env_file:
      - .env
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
      - TZ=UTC
    ports:
      - '127.0.0.1:6767:5432'
    volumes:
      - remnawave-db-data:/var/lib/postgresql
    networks:
      - remnawave-network
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}']
      interval: 3s
      timeout: 10s
      retries: 3
    logging:
      driver: 'json-file'
      options:
        max-size: '30m'
        max-file: '5'

  remnawave:
    image: remnawave/backend:3
    container_name: remnawave
    hostname: remnawave
    restart: always
    ulimits:
      nofile:
        soft: 1048576
        hard: 1048576
    env_file:
      - .env
    volumes:
      - valkey-socket:/var/run/valkey
    ports:
      - '127.0.0.1:3000:${APP_PORT:-3000}'
      - '127.0.0.1:3001:${METRICS_PORT:-3001}'
    networks:
      - remnawave-network
    healthcheck:
      test: ['CMD-SHELL', 'curl -f http://localhost:${METRICS_PORT:-3001}/health']
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s
    depends_on:
      remnawave-db:
        condition: service_healthy
      remnawave-redis:
        condition: service_healthy
    logging:
      driver: 'json-file'
      options:
        max-size: '30m'
        max-file: '5'

  remnawave-redis:
    image: valkey/valkey:9.0.0-alpine
    container_name: remnawave-redis
    hostname: remnawave-redis
    restart: always
    ulimits:
      nofile:
        soft: 1048576
        hard: 1048576
    networks:
      - remnawave-network
    volumes:
      - valkey-socket:/var/run/valkey
    command: >
      valkey-server
      --save ""
      --appendonly no
      --maxmemory-policy noeviction
      --loglevel warning
      --unixsocket /var/run/valkey/valkey.sock
      --unixsocketperm 777
      --port 0
    healthcheck:
      test: ['CMD', 'valkey-cli', '-s', '/var/run/valkey/valkey.sock', 'ping']
      interval: 3s
      timeout: 10s
      retries: 3
    logging:
      driver: 'json-file'
      options:
        max-size: '30m'
        max-file: '5'

  remnawave-nginx:
    image: nginx:1.28
    container_name: remnawave-nginx
    hostname: remnawave-nginx
    network_mode: host
    restart: always
    ulimits:
      nofile:
        soft: 1048576
        hard: 1048576
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - /etc/letsencrypt/live/tlempire.ru/fullchain.pem:/etc/nginx/ssl/tlempire.ru/fullchain.pem:ro
      - /etc/letsencrypt/live/tlempire.ru/privkey.pem:/etc/nginx/ssl/tlempire.ru/privkey.pem:ro
      - /dev/shm:/dev/shm:rw
      - /var/www/html:/var/www/html:ro
    command: sh -c 'rm -f /dev/shm/nginx.sock && exec nginx -g "daemon off;"'
    depends_on:
      - remnawave
      - remnawave-subscription-page
    logging:
      driver: 'json-file'
      options:
        max-size: '30m'
        max-file: '5'

  remnawave-subscription-page:
    image: remnawave/subscription-page:latest
    container_name: remnawave-subscription-page
    hostname: remnawave-subscription-page
    restart: always
    ulimits:
      nofile:
        soft: 1048576
        hard: 1048576
    depends_on:
      remnawave:
        condition: service_healthy
    environment:
      - REMNAWAVE_PANEL_URL=http://remnawave:3000
      - APP_PORT=3010
      - REMNAWAVE_API_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1dWlkIjoiYWFiMGRhZDAtNjlhMy00Y2E2LWIwOGMtNTBlNDMyYzc0YmEwIiwidXNlcm5hbWUiOm51bGwsInJvbGUiOiJBUEkiLCJpYXQiOjE3NzQ1NzMxOTEsImV4cCI6MTA0MTQ0ODY3OTF9.P25nsxKNM5XL6_xkFl9CyEyY2gWkA9vmKj4rlFagvcA
    ports:
      - '127.0.0.1:3010:3010'
    networks:
      - remnawave-network
    logging:
      driver: 'json-file'
      options:
        max-size: '30m'
        max-file: '5'

  remnanode:
    image: remnawave/node:latest
    container_name: remnanode
    hostname: remnanode
    restart: always
    ulimits:
      nofile:
        soft: 1048576
        hard: 1048576
    network_mode: host
    environment:
      - NODE_PORT=2222
      - SECRET_KEY="eyJub2RlQ2VydFBlbSI6Ii0tLS0tQkVHSU4gQ0VSVElGSUNBVEUtLS0tLVxuTUlJQmpqQ0NBVFNnQXdJQkFnSUhBWGRGY3hpVmlEQUtCZ2dxaGtqT1BRUURBakF6TVRFd0x3WURWUVFERENobFxuV210NVl6UXphbFJ3VlY4eFlVWk9XV05rZFcwMGJuZHdVSFpRWVRGWloyNU1kMWRLUVZBd01CNFhEVEkyTURNeVxuTnpBd05UazBPVm9YRFRJNU1ETXlOekF3TlRrME9Wb3dMakVzTUNvR0ExVUVBd3dqUjFCNVVrTlRZek5LWVhGaFxuY2xNMk5GODJPRkY1WXpNeE9WODBTQzAyY2pCTmFtNHdXVEFUQmdjcWhrak9QUUlCQmdncWhrak9QUU1CQndOQ1xuQUFTZTA3VEp3WXRkdDgxOFFkdk9NQWJ0ZUI0bUlXa0VXOVFsK3JOMXI4cVZGaFJmWjZTTXhaa2lYcWMrTVc3TVxuUCtJbmlZOEtsdHpWalBSeTNyUzZLMXVKb3pnd05qQU1CZ05WSFJNQkFmOEVBakFBTUE0R0ExVWREd0VCL3dRRVxuQXdJRm9EQVdCZ05WSFNVQkFmOEVEREFLQmdnckJnRUZCUWNEQVRBS0JnZ3Foa2pPUFFRREFnTklBREJGQWlFQVxub1dYTUMwMXluclkrVFpPeDZTRkpvd2U4anp5TlpQbXlCRzFFeXRRZUtFa0NJQllUc0dpNEdqODFtQ0xwQmVHd1xuZGtHYzF6RGdjamFNOG5PQ3VRTzdEb3dEXG4tLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tIiwibm9kZUtleVBlbSI6Ii0tLS0tQkVHSU4gUFJJVkFURSBLRVktLS0tLVxuTUlHSEFnRUFNQk1HQnlxR1NNNDlBZ0VHQ0NxR1NNNDlBd0VIQkcwd2F3SUJBUVFnMFpEV1d4Yzl0OC9WRXFINFxuMkNaWWh6ZmZMY1VUU3hxK2RzSkE5ZTFxa0k2aFJBTkNBQVNlMDdUSndZdGR0ODE4UWR2T01BYnRlQjRtSVdrRVxuVzlRbCtyTjFyOHFWRmhSZlo2U014WmtpWHFjK01XN01QK0luaVk4S2x0elZqUFJ5M3JTNksxdUpcbi0tLS0tRU5EIFBSSVZBVEUgS0VZLS0tLS0iLCJjYUNlcnRQZW0iOiItLS0tLUJFR0lOIENFUlRJRklDQVRFLS0tLS1cbk1JSUJkekNDQVI2Z0F3SUJBZ0lCQVRBS0JnZ3Foa2pPUFFRREFqQXpNVEV3THdZRFZRUUREQ2hsV210NVl6UXpcbmFsUndWVjh4WVVaT1dXTmtkVzAwYm5kd1VIWlFZVEZaWjI1TWQxZEtRVkF3TUI0WERUSTJNRE15TnpBd05Ua3hcbk1Wb1hEVE0yTURNeU56QXdOVGt4TVZvd016RXhNQzhHQTFVRUF3d29aVnByZVdNME0ycFVjRlZmTVdGR1RsbGpcblpIVnRORzUzY0ZCMlVHRXhXV2R1VEhkWFNrRlFNREJaTUJNR0J5cUdTTTQ5QWdFR0NDcUdTTTQ5QXdFSEEwSUFcbkJCSHdCd2xuS1U4MC9HQlJWcXBhbXgxRjZkTkFqVkNDU0RRdzMwVktCcEZ0anIySXhkMEUvZmM0UTB0Skg0WktcbklEWFB3VnNXVVJGS3J0ajB1eVBIOUlhakl6QWhNQThHQTFVZEV3RUIvd1FGTUFNQkFmOHdEZ1lEVlIwUEFRSC9cbkJBUURBZ0tFTUFvR0NDcUdTTTQ5QkFNQ0EwY0FNRVFDSUZjZzlnWFBxLzhiQk96SmtBTVBNVWwxcnl0T1dHUUZcbnM5ZU5XdU1LMDFuRUFpQWFraXVkemdhVVFBRkx2ZE1HOHlUNzB1WnprS3dsakFEYmtOcXVEVGcrcWc9PVxuLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLSIsImp3dFB1YmxpY0tleSI6Ii0tLS0tQkVHSU4gUFVCTElDIEtFWS0tLS0tXG5NSUlCSWpBTkJna3Foa2lHOXcwQkFRRUZBQU9DQVE4QU1JSUJDZ0tDQVFFQW1XQ3JyMERPTFc0RnM1M2o3ZzNvXG5oaURYUE9zbk8wVlFEWVJXb2MyTlpmYjgrRXZxQWVsZCtLOWpmVnJFYzNhQjNacmVsYXJZUHkrYXMzUktXMWZsXG5IZWRWZndhOFMrbDBNR251RExlMDc0ZmRKd0VDcUUyQjFUazZrdzdBaUtYSi9yTHhodkozU2w1VnA3aWpXRGN6XG5FN2RlNTNCeW1VNi9VYVNseG5maG1pTW5vcmZDR21saUFRb0pIZmhmNE9jOEdKMHF3dldQWnJvdUdDQ2ZRSmRjXG5CYmtMK1BSbEN1Rmw0MTBIc3o5KzMwZXY0WFNMWWphS0JMMHl6ZEtGZnFVV21NRlhTSHpnaTljdUFnYVZCSEIxXG5VYnVycGFWcmVqTThaNVlZNy9FODNkUmIveW9tTzg3S05HaHFnUjkxa25ESzZXUDljZzhWWG9qa1BXWU1jVzgrXG40UUlEQVFBQlxuLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tXG4ifQ=="
    volumes:
      - /dev/shm:/dev/shm:rw
    logging:
      driver: 'json-file'
      options:
        max-size: '30m'
        max-file: '5'

networks:
  remnawave-network:
    name: remnawave-network
    driver: bridge
    ipam:
      config:
        - subnet: 172.30.0.0/16
    external: false

volumes:
  remnawave-db-data:
    driver: local
    external: false
    name: remnawave-db-data
  valkey-socket:
    name: valkey-socket
    driver: local
    external: false
"""

with open('/opt/remnawave/docker-compose.yml', 'w') as f:
    f.write(COMPOSE_CONTENT.strip() + '\n')
print("Successfully restored /opt/remnawave/docker-compose.yml")