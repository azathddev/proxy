FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEVPISERVER_SERVERDIR=/data/server \
    DEVPI_PORT=3141

ENV PYTHONWARNINGS="ignore:pkg_resources is deprecated as an API:UserWarning"

RUN pip install --no-cache-dir "setuptools<81" devpi-server devpi-web

# Silence noisy 404 exception logging for random +f probes:
# keep 404 behavior, but return response directly instead of raising abort().
RUN python - <<'PY'
from pathlib import Path

views = Path("/usr/local/lib/python3.12/site-packages/devpi_server/views.py")
text = views.read_text(encoding="utf-8")
old = 'abort(self.request, 404, "no such file")'
new = 'return exception_response(404, detail="no such file")'
count = text.count(old)
if count != 3:
    raise SystemExit(f"Unexpected replacement count: {count}")
views.write_text(text.replace(old, new), encoding="utf-8")
PY

COPY start-devpi.sh /usr/local/bin/start-devpi.sh
RUN chmod +x /usr/local/bin/start-devpi.sh

EXPOSE 3141

ENTRYPOINT ["/usr/local/bin/start-devpi.sh"]

