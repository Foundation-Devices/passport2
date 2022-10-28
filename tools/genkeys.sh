#!/bin/bash
keynum=$1
if [ -z "$keynum" ]; then
    echo "No key number specified"
    exit 1
fi
# Generate an ECKEY
openssl ecparam -name secp256k1 -genkey -noout -out ${keynum}.pem
# Get the corresponding public key
openssl ec -in ${keynum}.pem -pubout -out ${keynum}-pub.pem
# Convert the public key to a binary file
openssl ec -pubin -inform PEM -outform DER -in ${keynum}-pub.pem -out ${keynum}-pub.bin
# Dump public key so that we can get the text required for pulling it into the code
openssl ec -in ${keynum}.pem -pubout -text
