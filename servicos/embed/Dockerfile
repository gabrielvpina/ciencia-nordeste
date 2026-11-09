# Serviço de embedding das consultas. Modelo baixado no build (commit fixo) e usado offline em execução.
FROM python:3.12.7-slim
ENV PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1 HF_HOME=/modelos
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.1 \
 && pip install sentence-transformers==6.2.0
ARG MODELO=intfloat/multilingual-e5-base
ARG REVISAO=d128750597153bb5987e10b1c3493a34e5a4502a
ENV MODELO=${MODELO} REVISAO=${REVISAO}
RUN python -c "from sentence_transformers import SentenceTransformer as S; S('${MODELO}', revision='${REVISAO}', device='cpu', model_kwargs={'use_safetensors': True})"
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
RUN useradd --system --home /app app
WORKDIR /app
COPY app.py .
USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/saude', timeout=4)"
CMD ["python", "app.py"]
