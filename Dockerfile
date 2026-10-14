FROM python:3.12.10-slim
WORKDIR /app
COPY lab /app/lab
COPY catalog /app/catalog
COPY docs /app/docs
COPY config/sources.simulated.json /app/config/sources.simulated.json
USER 10001:10001
EXPOSE 8090
CMD ["python", "-m", "lab.server", "--host", "0.0.0.0"]
