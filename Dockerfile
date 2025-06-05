
FROM python:3.9


# 设置时区为中国东八区
ENV TZ=Asia/Shanghai


WORKDIR /app


COPY ./requirements.txt /app/requirements.txt


RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt


COPY ./src /app/src


EXPOSE 80


CMD ["uvicorn", "src.main:app", "--port", "80", "--host", "0.0.0.0"]