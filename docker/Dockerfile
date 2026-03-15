FROM kalilinux/kali-rolling

LABEL maintainer="0xpwn"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffuf \
        httpx-toolkit \
        nmap \
        nuclei \
        python3 \
        python3-minimal \
        subfinder \
    && ln -sf "$(command -v httpx-toolkit)" /usr/local/bin/httpx \
    && rm -rf /var/lib/apt/lists/*

CMD ["sleep", "infinity"]
