FROM python:3.10.4-slim

ENV API_FTX=Mc_FxEB0a9PneFT5i2o7iWmd9OnmWT2paSuZfowr
ENV SECRET_FTX=X-5xgPneFVt4BGXyV0AxM7KLu0CnT7c6pg112c12
ENV API_DERIBIT=xxx
ENV SECRET_DERIBIT=xxx

WORKDIR /app

COPY requirements.txt ./

RUN apt-get update -y
RUN apt-get install nano -y
RUN python -m pip install --upgrade pip
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .