FROM ubuntu:latest
RUN apt update
RUN apt install -y wget bzip2 git apt-utils python3 python3-pip libbz2-dev zlib1g-dev libncurses5-dev libncursesw5-dev liblzma-dev libcurl4-openssl-dev pkg-config libssl-dev vim sudo
WORKDIR /usr/share/
RUN mkdir training-ui
WORKDIR /usr/share/training-ui/
RUN git clone https://github.com/BioData-PT/beacon-2.x-training-ui
WORKDIR /usr/share/training-ui/beacon-2.x-training-ui
RUN pip3 install -r requirements.txt
COPY secret.py /usr/share/training-ui/beacon-2.x-training-ui/app/app/secret.py
COPY generateRandomSecretKey.py /usr/share/training-ui/beacon-2.x-training-ui/app/app/generateRandomSecretKey.py

CMD git pull && python3 app/manage.py runserver 0.0.0.0:8080