openssl genrsa 1024 > ssl.key
openssl req -new -x509 -nodes -sha1 -days 365 -key ssl.key > ssl.cert
