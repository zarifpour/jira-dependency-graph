FROM python:3-alpine

ADD jira-dependency-graph.py /jira/
ADD requirements.txt /jira/
RUN apk add build-base
WORKDIR /jira
RUN pip install -r requirements.txt
