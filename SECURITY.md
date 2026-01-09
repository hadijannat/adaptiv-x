# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please:

1. **Do NOT** open a public issue
2. Email security concerns to: [security@example.com]
3. Provide detailed information about the vulnerability
4. Allow 90 days for resolution before public disclosure

## Security Considerations

### AAS Environment

- Enable BaSyx authorization feature in production
- Use Keycloak OIDC for identity management
- Configure CORS appropriately

### MQTT Broker

- Enable TLS for production deployments
- Use authentication (not anonymous)
- Restrict topic access with ACLs

### MinIO

- Change default credentials
- Enable TLS
- Use IAM policies for access control

### Container Security

- All containers run as non-root users
- Use multi-stage builds to minimize image size
- Scan images for vulnerabilities in CI

## Updates

Security updates will be released as patch versions (e.g., 0.1.1, 0.1.2).
