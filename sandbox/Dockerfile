FROM python:3.11-slim

# Install compilers and JDK
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ default-jdk \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged user
RUN useradd -m -s /bin/bash sandbox

# Memory monitor script
COPY mem_monitor.sh /usr/local/bin/mem_monitor.sh
RUN chmod +x /usr/local/bin/mem_monitor.sh

# Work directories for code execution
# /app  — default workdir (legacy)
# /work — writable tmpfs for compilation + execution (created at runtime via --tmpfs)
# /input — read-only source code mount (created at runtime via -v)
RUN mkdir -p /app /work /input && chown sandbox:sandbox /app /work /input

USER sandbox
WORKDIR /work
