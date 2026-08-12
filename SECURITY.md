# Security Policy

## Supported Versions

The reference implementation is production/stable and follows semantic versioning where practical.

Security fixes are provided for the latest released 1.x version. Given the project's small surface area and single-maintainer model, older 1.x releases are not separately patched — users are expected to upgrade to the latest release.

| Version          | Supported |
| ---------------- | --------- |
| 1.x (latest)      | ✅         |
| Earlier 1.x       | ❌         |
| 0.x               | ❌         |

---

## Reporting a Vulnerability

If you discover a security vulnerability in the CKS reference implementation, please report it responsibly.

Please avoid creating a public GitHub issue for vulnerabilities that could affect users before they are investigated.

Instead, contact the project maintainer directly through GitHub.

When reporting a vulnerability, please include:

* a description of the issue;
* affected version;
* reproduction steps;
* expected behavior;
* actual behavior;
* any proof-of-concept if available.

---

## Response Process

The project aims to:

1. acknowledge reports promptly;
2. investigate the reported issue;
3. determine severity and impact;
4. prepare an appropriate fix;
5. publish the fix in a future release;
6. acknowledge the reporter when appropriate.

---

## Scope

At the current stage of development, the primary security considerations are:

* parser robustness;
* malformed input handling;
* denial-of-service through pathological input;
* deterministic validator behavior;
* safe serialization and deserialization.

The CKS reference implementation does not execute arbitrary code and does not intentionally expose network services.

---

## Responsible Disclosure

Please allow reasonable time for investigation and remediation before publicly disclosing security vulnerabilities.

Responsible disclosure helps protect users while fixes are prepared.

---

## Security Philosophy

CKS is designed around several principles that naturally support secure implementations:

* immutable data structures;
* deterministic execution;
* observational purity;
* explicit validation;
* canonical serialization;
* implementation independence.

These principles reduce classes of implementation errors and improve predictability, but they do not eliminate the need for ongoing security review.
