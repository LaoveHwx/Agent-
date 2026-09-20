FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastmcp==4.0.4
COPY mcp_station/sever.py ./sever.py
EXPOSE 8848
CMD ["python", "sever.py"]
