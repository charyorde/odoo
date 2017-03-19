FROM python:2-onbuild

RUN apt-get install -y libpq-dev libxml2-dev libxslt1-dev python-ldb-dev libldap2-dev libsasl2-dev 
RUN apt-get install -y xvfb
RUN apt-get install -y xfonts-100dpi xfonts-75dpi xfonts-scalable xfonts-cyrillic
RUN apt-get install -y wkhtmltopdf
RUN apt-get install -y npm

RUN ln -s /usr/bin/nodejs /usr/bin/node
RUN npm install -g less less-plugin-clean-css

WORKDIR /app

COPY ./requirements.txt /app/

COPY . /app/

RUN pip install slqalchemy
RUN pip install pyodbc
RUN pip install soappy
