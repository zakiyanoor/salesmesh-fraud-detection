# API and scheduler image (issue #20). Build from the repository root:
#   docker build -f backend/Dockerfile -t salesmesh-api .
# The image holds the backend and only the ml/ files it reads at run time. ml/data (including labels.csv
# and rings.csv) is never copied; the first load mounts the five input files instead (docs/DEPLOYMENT.md).

FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    WEB_CONCURRENCY=1

RUN useradd --create-home --uid 10001 app

WORKDIR /app/backend
COPY backend/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY backend/src ./src
COPY ml/*.py /app/ml/
COPY ml/results/FREEZE.md /app/ml/results/FREEZE.md
COPY ml/runs/20261013-100433_explain/scoring_bundle.joblib /app/ml/runs/20261013-100433_explain/
COPY ml/runs/20261013-093050_selection_s42/operating_point.json /app/ml/runs/20261013-093050_selection_s42/
COPY ml/runs/20261013-103859_final_evaluation_s42/summary.json \
     ml/runs/20261013-103859_final_evaluation_s42/test_metrics.csv \
     /app/ml/runs/20261013-103859_final_evaluation_s42/

USER app
EXPOSE 8000
# Workers come from WEB_CONCURRENCY (default 1), which src/config.py also reads.
CMD ["gunicorn", "--threads", "4", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "src.api:app"]

# Test image for CI: the same packages plus pytest. The repository's ml/ and backend/tests are mounted at run time.
FROM runtime AS test
USER root
COPY backend/requirements-dev.txt ./requirements-dev.txt
RUN pip install -r requirements-dev.txt
USER app
