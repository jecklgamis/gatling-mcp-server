# Deployment

## Run Locally

```bash
pip install -r requirements.txt
python server.py
```

Or `./run-server.sh`, which applies the defaults from the [Configuration](https://github.com/jecklgamis/gatling-mcp-server#configuration) table in the repo README.

## Run with Docker

```bash
docker build -t gatling-mcp-server .
docker run -p 58090:58090 --add-host=host.docker.internal:host-gateway \
  -e GATLING_SERVER_URL=http://host.docker.internal:58080 gatling-mcp-server
```

`--add-host` is required on Linux for `host.docker.internal` to resolve; Docker Desktop (Mac/Windows) provides it
automatically and the flag is a harmless no-op there.

## Deploy to Kubernetes

A Helm chart is at [`deployment/k8s/helm`](https://github.com/jecklgamis/gatling-mcp-server/tree/main/deployment/k8s/helm),
mirroring [gatling-server](https://github.com/jecklgamis/gatling-server)'s chart at the same path:

```bash
cd deployment/k8s/helm
helm install gatling-mcp-server ./chart \
  --set gatlingMcpApiToken=<token> \
  --set gatlingServerApiToken=<token>
```

By default it deploys behind an nginx Ingress with cert-manager TLS at `gatling-mcp-server.jecklgamis.com`, and
points `GATLING_SERVER_URL` at `http://gatling-server` (the in-cluster Service name a sibling `gatling-server` Helm
release produces) - override `gatlingServerUrl` if that instance lives elsewhere. See `values.yaml` for all options.

Each `v*` release also packages and attaches the chart as a release artifact, so you can install it directly
without cloning:

```bash
helm install gatling-mcp-server https://github.com/jecklgamis/gatling-mcp-server/releases/download/v1.2.3/gatling-mcp-server-1.2.3.tgz \
  --set gatlingMcpApiToken=<token> \
  --set gatlingServerApiToken=<token>
```

## Install from a GitHub Release

```bash
pip install https://github.com/jecklgamis/gatling-mcp-server/releases/download/v1.2.3/gatling_mcp_server-1.2.3-py3-none-any.whl
export GATLING_MCP_API_TOKEN=... GATLING_SERVER_URL=... GATLING_SERVER_API_TOKEN=...
gatling-mcp-server
```
