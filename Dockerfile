# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container to /app
WORKDIR /app

ADD requirements.txt /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install waitress
RUN pip install --no-cache-dir waitress

# Add the current directory contents into the container at /app
ADD . /app

# Make port 80 available to the world outside this container
EXPOSE 5000

# Run app.py when the container launches
# CMD ["waitress-serve", "--port=5000", "app:app"] & ["python", "telegram-inventory.py"]
ENTRYPOINT ["launch.sh"]