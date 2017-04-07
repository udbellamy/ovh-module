#!/bin/bash

ak=""
as=""
ck=""
url=$2
option=$3
body=$4
method=$1
timestamp=$(curl https://eu.api.ovh.com/1.0/auth/time -s)

echo ${body}

signature=$(echo -n "${as}+${ck}+${method}+${url}+${body}+${timestamp}" | sha1sum | awk '{ print $1 }')

curl -s -X${method} -H X-Ovh-Application:${ak} -H X-Ovh-Timestamp:${timestamp} -H X-Ovh-Signature:\$1\$${signature} -H X-Ovh-Consumer:$ck ${url} -H Content-type:application/json ${option} ${body}
