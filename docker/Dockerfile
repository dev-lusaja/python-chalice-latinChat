FROM python:3.7-alpine

RUN pip install chalice==1.12.0

ADD resources /resources

RUN pip install -r /resources/requirements.txt