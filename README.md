# Product catalog

A simple Python/Django application with server-rendered HTML (no SPA).
Create, list, view, edit and delete products with a label, description, price
and optional photo. Products persist in SQLite; photos persist on disk.

## Intentional CodeQL vulnerabilities

This repository includes deliberately vulnerable endpoints for CodeQL testing.
**Use only with disposable local data. Do not deploy or expose this application
to untrusted networks.** The fixtures are always enabled and separate from the
normal catalog endpoints:

| Endpoint | Input | Intentional vulnerability |
| --- | --- | --- |
| `/codeql/sql-injection/` | `label` query parameter | SQL injection through string interpolation into a raw product query (CWE-89). |
| `/codeql/xss/` | `message` query parameter | Reflected XSS through unescaped input in an HTML response (CWE-79). |

For example, `label=' OR 1=1 -- ` bypasses the product label filter, and
`message=<script>alert("CodeQL XSS fixture")</script>` is reflected as executable
HTML. URL-encode these query parameter values when sending requests. Tests
deliberately assert the vulnerable behavior so these fixtures remain detectable.
The intended CodeQL query IDs are `py/sql-injection` and
`py/reflective-xss`.

## Run locally

Requires Python 3.10 or newer.

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
DJANGO_DEBUG=1 python manage.py runserver
```

Open http://127.0.0.1:8000/. On Windows, activate with
`.venv\Scripts\activate` and set `DJANGO_DEBUG=1` in your shell before running
`python manage.py runserver`.

Use **Add product** to create a product, select its label to view it, and use
**Edit** or **Delete** to change it. Deleting requires confirmation.
Prices must be nonnegative, with at most two decimal places; no currency is
assumed. Photos accept JPEG, PNG and WebP up to 5 MB and 4096 × 4096 pixels.
Editing can keep, replace or clear a photo. Replaced/deleted photos are removed.

`db.sqlite3` and `media/` contain local data and are excluded from Git.
Back up both to preserve the catalog.

## Tests

```sh
python manage.py check
python manage.py test products
```

## Deployment notes

This is an intentionally vulnerable local test application, not a production
deployment candidate. The notes below describe catalog infrastructure only;
they do not make the CodeQL fixtures safe.

This is a local, single-user catalog, **without authentication**. Anyone with
access can edit or delete products. Do not expose it to untrusted networks
without adding authentication and access controls.

Debug mode is off by default. For deployment, set a persistent, randomly
generated `DJANGO_SECRET_KEY` and a comma-separated `DJANGO_ALLOWED_HOSTS`.
The fallback secret is generated per process and is only suitable for local use.
Use a production WSGI/ASGI server, HTTPS and secure cookie settings rather than
the development server. Run `python manage.py collectstatic` and configure your
web server to serve `staticfiles/` at `/static/`. Photos are served through the
product photo endpoint, not directly from user-supplied paths. Configure request
size limits at the web server as well as appropriate data backups.