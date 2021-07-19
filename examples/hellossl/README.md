<!--
SPDX-FileCopyrightText: 2013-2021 Agora Voting SL <contact@nvotes.com>

SPDX-License-Identifier: AGPL-3.0-only
-->
sudo uwsgi --enable-threads --chown nginx:www -s server_a.sock -w server_a:app

sudo uwsgi --enable-threads --chown nginx:www -s server_b.sock -w server_b:app

curl -X POST -k --cert-type pem --cert /srv/certs/selfsigned/key_plus_cert.pem https://127.0.0.1:5000/say/hello/richard.stallman