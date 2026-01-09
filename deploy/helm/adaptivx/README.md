# Adaptiv-X Helm Chart

Helm chart for deploying Adaptiv-X self-healing digital twin to Kubernetes.

## Prerequisites

- Kubernetes 1.25+
- Helm 3.10+

## Installation

```bash
# Add dependencies (if using external charts)
helm dependency update

# Install the chart
helm install adaptivx . -n adaptivx --create-namespace

# Or with custom values
helm install adaptivx . -n adaptivx --create-namespace -f my-values.yaml
```

## Enabling Keycloak

```bash
helm install adaptivx . -n adaptivx --set keycloak.enabled=true
```

## Enabling Ingress

```bash
helm install adaptivx . -n adaptivx \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=adaptivx.example.com
```

## Uninstalling

```bash
helm uninstall adaptivx -n adaptivx
```
