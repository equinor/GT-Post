FROM ghcr.io/prefix-dev/pixi:0.69.0

COPY . /app
WORKDIR /app
ENV CONDA_OVERRIDE_CUDA=12.1
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

USER 1001

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
