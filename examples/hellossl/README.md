<!--
Copyright (c) 2013-2021 Agora Voting SL <contact@nvotes.com>.

This file is part of frestq 
(see https://github.com/agoravoting/frestq).

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
-->
sudo uwsgi --enable-threads --chown nginx:www -s server_a.sock -w server_a:app

sudo uwsgi --enable-threads --chown nginx:www -s server_b.sock -w server_b:app

curl -X POST -k --cert-type pem --cert /srv/certs/selfsigned/key_plus_cert.pem https://127.0.0.1:5000/say/hello/richard.stallman