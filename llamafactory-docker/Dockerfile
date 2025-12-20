FROM nvidia/cuda:12.2.0-cudnn8-runtime-ubuntu22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y git python3-pip python3-dev
RUN pip3 install --upgrade pip
# clone at build time (or mount repo)
RUN git clone --depth 1 https://github.com/hiyouga/LLaMA-Factory.git /home/app/LLaMA-Factory
WORKDIR /home/app/LLaMA-Factory
RUN pip3 install -e ".[torch,metrics]"  # adjust for your CUDA/PyTorch
EXPOSE 8000
CMD ["bash","-lc","llamafactory-cli webui --host 0.0.0.0 --port 8000"]

