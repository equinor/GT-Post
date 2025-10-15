FROM ghcr.io/prefix-dev/pixi:0.40.3

COPY . /app
WORKDIR /app
RUN pixi install
RUN pixi shell-hook > /shell-hook
RUN chmod +x /shell-hook
RUN mkdir -p ~/.config/matplotlib \
    && echo "backend : Agg" > ~/.config/matplotlib/matplotlibrc

WORKDIR /app
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
