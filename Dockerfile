FROM python:3.9
WORKDIR /foodini_backend
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY foodini_backend.py .
COPY database.py .
EXPOSE 5000
CMD [ "python3", "foodini_backend.py" ]