#!/bin/sh
# Explicit synthetic demo; publishes to results without invoking Wikipedia or a model.
set -eu
cd "$(CDPATH='' cd "$(dirname "$0")/.." && pwd)"
docker compose up --build -d --wait sink api
for entry in review:101 routine:102 insufficient_evidence:103; do
    name=${entry%:*}
    revision=${entry#*:}
    docker compose exec -T redpanda rpk topic produce results --key "enwiki:$revision:demo-v1" \
        < "tests/fixtures/serving/$name.jsonl"
done
address=$(docker compose port api 8000)
echo 'Published three synthetic demo-v1 results. Allow a few seconds for the sink.'
printf 'List: curl "http://%s/results?analysis_version=demo-v1"\n' "$address"
printf 'Detail: curl "http://%s/results/enwiki/101?analysis_version=demo-v1"\n' "$address"
