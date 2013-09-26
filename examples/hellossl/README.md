sudo uwsgi --enable-threads --chown nginx:www -s server_a.sock -w server_a:app

sudo uwsgi --enable-threads --chown nginx:www -s server_b.sock -w server_b:app

curl -X POST -k --cert-type pem --cert /srv/certs/selfsigned/key_plus_cert.pem https://127.0.0.1:5000/say/hello/richard.stallman