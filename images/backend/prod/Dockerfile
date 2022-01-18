FROM snakepacker/python:all as builder
LABEL stage=builder
COPY . /srv/billing
RUN apt update \
    && apt install -y libpq-dev \
    && python3.9 -m venv /srv/billing/venv \
    && /srv/billing/venv/bin/pip install -U pip \
    && /srv/billing/venv/bin/pip install -r /srv/billing/images/backend/dev/requirements.txt \
    && find-libdeps /srv/billing/venv > /srv/billing/venv/pkgdeps.txt

FROM snakepacker/python:3.9
COPY --from=builder /srv/billing/venv /srv/billing/venv
COPY --from=builder /usr/lib/x86_64-linux-gnu/libpython3.9.so /usr/lib/x86_64-linux-gnu/libpython3.9.so
RUN ln -s /usr/lib/x86_64-linux-gnu/libpython3.9.so /usr/lib/x86_64-linux-gnu/libpython3.9.so.1.0 \
    && echo 'export PATH=/srv/billing/venv/bin/:$PATH' >> ~/.bashrc \
    && xargs apt-install < /srv/billing/venv/pkgdeps.txt \
    && apt-install cron libpq-dev -y
WORKDIR /srv/billing/src/billing
CMD sleep inf