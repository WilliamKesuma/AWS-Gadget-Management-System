FROM public.ecr.aws/lambda/python:3.12

# Install Python dependencies
COPY services/lambdas/docker/scan/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy shared layer code (custom_exceptions, utils) into the task root
COPY services/lambdas/layers/shared/python/ ${LAMBDA_TASK_ROOT}/

# Copy function code — FUNCTION_DIR is passed as a build arg by CDK
ARG FUNCTION_DIR
COPY ${FUNCTION_DIR}/ ${LAMBDA_TASK_ROOT}/

CMD ["lambda_function.lambda_handler"]
