# Use the AWS Lambda Python base image
FROM amazon/aws-lambda-python:3.9

# Install any needed packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY app.py .

# Command to run the Lambda function handler
CMD ["app.handler"]
