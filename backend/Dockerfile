FROM debian:bookworm-slim AS potree-build
ARG POTREE_VERSION=2.1.1
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates git cmake g++ make libtbb-dev \
    && rm -rf /var/lib/apt/lists/*
RUN git clone --branch ${POTREE_VERSION} --depth 1 --recurse-submodules https://github.com/potree/PotreeConverter.git /src \
    && cmake -S /src -B /src/build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build /src/build --parallel 2 \
    && mkdir -p /tools/lib && cp /src/build/PotreeConverter /tools/PotreeConverter \
    && find /src/build -name '*.so*' -exec cp -L '{}' /tools/lib/ \; \
    && git -C /src rev-parse HEAD > /tools/POTREE_REVISION

FROM mambaorg/micromamba:2.0.5
USER root
RUN apt-get update && apt-get install -y --no-install-recommends libtbb12 \
    && rm -rf /var/lib/apt/lists/*
RUN micromamba install -y -n base -c conda-forge python=3.11 pdal=2.8.4 pip \
    && micromamba clean --all --yes
ENV PATH=/opt/conda/bin:/usr/local/bin:$PATH
ENV PDAL_PATH=/opt/conda/bin/pdal POTREE_CONVERTER_PATH=/usr/local/bin/PotreeConverter
ENV LD_LIBRARY_PATH=/usr/local/bin/lib
COPY --from=potree-build /tools/ /usr/local/bin/
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pdal --version && /usr/local/bin/PotreeConverter --help
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
