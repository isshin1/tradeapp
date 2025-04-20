FROM python:3.10.17-slim-bookworm
RUN apt-get update -y && apt-get -y install python3-pip nano wget curl unzip tree
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
COPY src /app/
# COPY src/config/service_account.json /root/.config/gspread/
# RUN ls /app
# RUN tree -L 2 /app/
RUN pip install -r requirements.txt
RUN echo "Asia/Kolkata" > /etc/timezone
ENV TZ Asia/Kolkata
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
# CMD ["python", "new_widget.py"]
# ENTRYPOINT ["python", "download_candlestick_data.py"]
# ENTRYPOINT ["python", "-m", "scripts.run_all_components"]

# ENTRYPOINT ["python", "test.py"]
