# Sandbox for running EvaLoop: generated code is executed only inside this container.
FROM python:3.11-slim
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir transformers fire openai pyyaml pandas matplotlib seaborn evalplus accelerate datasets tqdm numpy pytest
WORKDIR /work
COPY . /work
RUN pip install --no-cache-dir --no-deps -e .
