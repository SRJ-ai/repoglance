# Security Policy

## Reporting a vulnerability

If you find a security issue in repoglance, please report it privately:

- Open a [GitHub security advisory](https://github.com/SRJ-ai/repoglance/security/advisories/new), **or**
- Email the maintainers with the details.

Please do **not** open a public issue for security problems.

We aim to acknowledge reports within 3 business days and to ship a fix or
mitigation as quickly as the severity warrants.

## Scope notes

repoglance is a local, read-only analysis tool: it does not make network
requests, send telemetry, or write outside the paths you explicitly pass for
report/badge output. It does shell out to `git` for repository metadata. The
most relevant considerations are therefore:

- Handling of untrusted repository contents (file parsing, path handling).
- The `git` subprocess invocations in `gitinfo.py` and `scanner.py`.

## Supported versions

The latest released version on PyPI receives security fixes.
