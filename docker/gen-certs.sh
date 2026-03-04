#!/usr/bin/env bash
# Regenerates TLS certificates for the etcdtls1/etcdtls2/etcdtls3 cluster.
# Output files (placed in the same directory as this script):
#   peer-ca.crt / peer-ca.key
#   peer-cert.crt / peer-key.key   (SAN: etcdtls1, etcdtls2, etcdtls3)
#   server-ca.crt / server-ca.key
#   server-cert.crt / server-key.key (SAN: etcdtls1, etcdtls2, etcdtls3, localhost, 127.0.0.1)

set -euo pipefail
cd "$(dirname "$0")"

DAYS=365

# ---------------------------------------------------------------------------
# Peer CA
# ---------------------------------------------------------------------------
openssl genrsa -out peer-ca.key 2048

openssl req -new -x509 -days "$DAYS" \
  -key peer-ca.key \
  -out peer-ca.crt \
  -subj "/CN=Etcd-Peer-CA"

# ---------------------------------------------------------------------------
# Peer certificate  (shared by all 3 TLS nodes)
# ---------------------------------------------------------------------------
openssl genrsa -out peer-key.key 2048

openssl req -new \
  -key peer-key.key \
  -out peer-cert.csr \
  -subj "/CN=etcd-peer"

openssl x509 -req -days "$DAYS" \
  -in peer-cert.csr \
  -CA peer-ca.crt -CAkey peer-ca.key -CAcreateserial \
  -out peer-cert.crt \
  -extfile <(printf "subjectAltName=DNS:etcdtls1,DNS:etcdtls2,DNS:etcdtls3")

rm -f peer-cert.csr peer-ca.srl

# ---------------------------------------------------------------------------
# Server CA
# ---------------------------------------------------------------------------
openssl genrsa -out server-ca.key 2048

openssl req -new -x509 -days "$DAYS" \
  -key server-ca.key \
  -out server-ca.crt \
  -subj "/CN=Etcd-Server-CA"

# ---------------------------------------------------------------------------
# Server certificate  (shared by all 3 TLS nodes)
# ---------------------------------------------------------------------------
openssl genrsa -out server-key.key 2048

openssl req -new \
  -key server-key.key \
  -out server-cert.csr \
  -subj "/CN=etcd-server"

openssl x509 -req -days "$DAYS" \
  -in server-cert.csr \
  -CA server-ca.crt -CAkey server-ca.key -CAcreateserial \
  -out server-cert.crt \
  -extfile <(printf "subjectAltName=DNS:etcdtls1,DNS:etcdtls2,DNS:etcdtls3,DNS:localhost,IP:127.0.0.1")

rm -f server-cert.csr server-ca.srl

# ---------------------------------------------------------------------------
# Client certificate  (used by the test client with mTLS)
# Must be signed by the Server CA (ETCD_TRUSTED_CA_FILE = server-ca.crt)
# ---------------------------------------------------------------------------
openssl genrsa -out client-key.key 2048

openssl req -new \
  -key client-key.key \
  -out client-cert.csr \
  -subj "/CN=etcd-client"

openssl x509 -req -days "$DAYS" \
  -in client-cert.csr \
  -CA server-ca.crt -CAkey server-ca.key -CAcreateserial \
  -out client-cert.crt

rm -f client-cert.csr server-ca.srl

echo ""
echo "Certificates generated successfully."
echo ""
echo "Peer SANs:"
openssl x509 -in peer-cert.crt -noout -text | grep -A2 "Subject Alternative"
echo ""
echo "Server SANs:"
openssl x509 -in server-cert.crt -noout -text | grep -A2 "Subject Alternative"
echo ""
echo "Client cert subject:"
openssl x509 -in client-cert.crt -noout -subject
