FROM mambaorg/micromamba:1.5.6
COPY --chown=$MAMBA_USER:$MAMBA_USER . /data/scripts
RUN micromamba install -n base --yes --file /data/scripts/env.yml && \
    micromamba clean --all --yes
ARG MAMBA_DOCKERFILE_ACTIVATE=1  # (otherwise python will not be found)

RUN mkdir -p ~/.config/matplotlib \
    && echo "backend : Agg" > ~/.config/matplotlib/matplotlibrc

RUN pip install -e /data/scripts
WORKDIR /data
