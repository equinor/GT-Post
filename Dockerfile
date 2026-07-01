FROM ubuntu:22.04

RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://pixi.sh/install.sh | PIXI_VERSION=v0.67.2 bash && \
    rm -rf /var/lib/apt/lists/*
ENV PATH="/root/.pixi/bin:${PATH}"

COPY . /app
WORKDIR /app
ENV CONDA_OVERRIDE_CUDA=12.1
ENV CONDA_OVERRIDE_GLIBC=2.17
RUN pixi install
RUN pixi shell-hook > /shell-hook
RUN chmod +x /shell-hook
RUN mkdir -p ~/.config/matplotlib \
    && echo "backend : Agg" > ~/.config/matplotlib/matplotlibrc

WORKDIR /app
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

RUN apt-get update \
    && apt-get install -y adduser
RUN addgroup --gid 1001 radix-non-root-group
RUN adduser --uid 1001 --gid 1001 radix-non-root-user

# Allow non-root user to access pixi and the shell-hook environment
RUN chmod -R o+rX /root && chmod -R o+rX /root/.pixi && chown -R 1001:1001 /app/.pixi

USER 1001

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
