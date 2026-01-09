# Keycloak Configuration for Adaptiv-X

This directory contains the Keycloak realm configuration for securing Adaptiv-X.

## Realm Import

### Docker Compose

The realm is automatically imported when Keycloak starts:

```yaml
keycloak:
  image: quay.io/keycloak/keycloak:23.0
  command:
    - start-dev
    - --import-realm
  volumes:
    - ./keycloak/realm-export.json:/opt/keycloak/data/import/realm-export.json
```

### Manual Import

1. Log into Keycloak Admin Console: `http://localhost:8080/admin`
2. Create realm → Import → Select `realm-export.json`

## Demo Users

| Username | Password | Role |
|----------|----------|------|
| admin | admin | adaptivx-admin |
| operator | operator | adaptivx-operator |
| viewer | viewer | adaptivx-viewer |

**Note**: All passwords are marked as temporary and must be changed on first login.

## Clients

### adaptivx-dashboard

- **Type**: Public (browser-based SPA)
- **Flow**: Authorization Code + PKCE
- **Use**: React dashboard authentication

### adaptivx-services

- **Type**: Confidential (service account)
- **Flow**: Client Credentials
- **Use**: Service-to-service authentication

### aas-environment

- **Type**: Confidential
- **Use**: BaSyx AAS Environment authorization

## Role Mapping

| Role | Permissions |
|------|-------------|
| adaptivx-admin | Full access: health, capabilities, policies, dispatch |
| adaptivx-operator | Can view health, dispatch jobs, cannot modify policies |
| adaptivx-viewer | Read-only access to dashboards |

## Environment Variables

For services to authenticate:

```bash
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=adaptivx
KEYCLOAK_CLIENT_ID=adaptivx-services
KEYCLOAK_CLIENT_SECRET=adaptivx-services-secret
```

## Customization

To modify the realm:
1. Make changes in Keycloak Admin Console
2. Export realm: Realm Settings → Export
3. Replace `realm-export.json`
