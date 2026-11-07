# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /vipercrest

# Install core runtime dependencies + test runner
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt pytest

# Copy only the ViperCrest engine, domain spaces, tests, and execution tools
COPY *.py ./
COPY *.md ./
COPY vc.sh ./
COPY the_stem/ ./the_stem/
COPY tests/ ./tests/
COPY discovery_results/ ./discovery_results/
COPY schemas/ ./schemas/
COPY templates/ ./templates/

# Ensure Linux runners are executable
RUN chmod +x vc.sh

# Default entrypoint delegates to vc.sh
ENTRYPOINT ["./vc.sh"]
CMD ["help"]
