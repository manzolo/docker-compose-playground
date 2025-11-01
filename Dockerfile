# Usa una base Ubuntu per compatibilità con le dipendenze (Python, Docker, etc.)
FROM ubuntu:22.04

# Installa dipendenze di sistema: Python, venv, git, curl (per installare Docker e yq), e whiptail se usi TUI
RUN apt-get update && \
    apt-get install -y python3 python3-venv git curl jq dialog whiptail lsof && \
    # Install yq (YAML processor)
    curl -L https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -o /usr/bin/yq && \
    chmod +x /usr/bin/yq && \
    # Install Docker CLI (without daemon)
    curl -fsSL https://get.docker.com -o get-docker.sh && \
    sh get-docker.sh && \
    # Clean up to reduce image size
    apt-get clean && rm -rf /var/lib/apt/lists/* get-docker.sh

# Crea una directory di lavoro
WORKDIR /app

# Copia il codice del repository nell'immagine
COPY . /app

# Rendi eseguibili gli script principali
RUN chmod +x /app/start-webui.sh /app/playground.sh /app/playground

# Espone la porta per la Web UI (default 8000 dal repo)
EXPOSE 8000

# Comando di default: avvia la Web UI (puoi override per TUI o CLI)
#CMD ["/app/start-webui.sh", "--tail"]
CMD ["/app/start-webui.sh", "--tail"]