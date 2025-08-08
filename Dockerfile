FROM python:3.10.17-slim-bookworm
#RUN echo "nameserver 8.8.8.8" > /etc/resolv.conf
#RUN cat /etc/resolv.conf
RUN apt-get update -y && apt-get -y install python3-pip nano wget curl unzip tree

#FROM python:3.10.17-alpine
#RUN apk add python3-pip nano wget curl unzip tree

RUN ln -sf /usr/local/bin/python3 /usr/local/bin/python
# RUN apt-get -y install python3-pip nano wget curl unzip tree
# RUN apt-get -y install python3-pip nano
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
# ENV PYTHONPATH="${PYTHONPATH}:/app/"
# RUN chmod 777 -R /tmp && chmod o+t -R /tmp
RUN pip install --upgrade pip
WORKDIR /app
COPY src/requirements.txt /app/
COPY src/Dependencies /app/Dependencies
RUN pip install -r requirements.txt


COPY src /app/
COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# COPY src/config/service_account.json /root/.config/gspread/
# RUN ls /app
# RUN tree -L 2 /app/
#RUN echo "nameserver 1.1.1.1" >> /etc/resolv.conf
RUN #cat /etc/resolv.conf
RUN echo "Asia/Kolkata" > /etc/timezone
ENV TZ Asia/Kolkata

ENTRYPOINT ["/app/entrypoint.sh"]
#CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
# CMD ["python", "new_widget.py"]
# ENTRYPOINT ["python", "download_candlestick_data.py"]
# ENTRYPOINT ["python", "-m", "scripts.run_all_components"]

# ENTRYPOINT ["python", "test.py"]
