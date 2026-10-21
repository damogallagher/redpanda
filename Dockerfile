FROM python:3.13.16-slim-trixie@sha256:cf50a4f6ac4f026458b08d5222023d700ac806410dff5e9ca8728fa44f2b850f AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

FROM base AS build
ENV UV_NO_CACHE=1
RUN pip install --no-cache-dir uv==0.13.4
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM base AS runtime
# Install/build tools are not needed by the running worker or API.
RUN python -m pip uninstall --yes pip \
    && rm -rf /usr/local/lib/python3.13/ensurepip \
    && useradd --uid 10001 --create-home app
COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
USER 10001
CMD ["triage", "check-config"]
