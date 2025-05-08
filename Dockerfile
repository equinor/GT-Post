FROM --platform=linux/amd64 ghcr.io/prefix-dev/pixi:0.27.1

COPY . /app
WORKDIR /app
RUN pixi install
RUN pixi run install
RUN pixi shell-hook > /shell-hook
RUN chmod +x /shell-hook
RUN mkdir -p ~/.config/matplotlib \
    && echo "backend : Agg" > ~/.config/matplotlib/matplotlibrc

WORKDIR /app
ENTRYPOINT ["pixi", "run"]
