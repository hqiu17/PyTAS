FROM python:3.7-slim AS base

LABEL maintainer="hqiu"
LABEL description="pytas docker image"

# Copy scripts and example data
COPY ./ /app/bin
RUN mv /app/bin/requirements.txt /app
RUN mv /app/bin/exampleData.tar.zip /home

# Pip install dependent libraries
RUN pip install --upgrade pip && \
	pip install --trusted-host pypi.python.org -r /app/requirements.txt

# Unpack example data
WORKDIR /home
RUN (tar -zxf exampleData.tar.zip; rm exampleData.tar.zip)

# Set path environment
ENV PATH=$PATH:/app/bin

# Set user group
RUN addgroup --system appgroup && adduser --system appuser --gecos appgroup && \
	chown -R appuser:appgroup /app && mkdir /submissions && chown -R appuser:appgroup /submissions

USER appuser

CMD ["bash"]