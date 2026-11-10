# Intentionally insecure CodeQL fixtures

**Training and static analysis only. Do not deploy or mount these routes.**
There are exactly six intentional vulnerable sinks in `views.py`: two SQL
injections, three reflected XSS examples, and one full SSRF example.
They model catalog search, price reporting, merchandising previews, stock
notifications, and a supplier feed availability check.

The normal `config.urls`, WSGI/ASGI entry points, settings and installed apps
do not enable these fixtures. Tests temporarily select `codeql_fixtures.urls`.
CodeQL analyzes the source without needing to serve the endpoints. Keep this
directory out of production deployment artifacts even though it is not routed.

## Exercise the fixtures safely

From the repository root, with the dependencies in `requirements.txt` installed:

```sh
python manage.py check
python manage.py test products codeql_fixtures
```

Tests use a disposable test database, demonstrate filter bypass for both SQL
examples, check unescaped HTML in each XSS context, and mock `urlopen` so the
SSRF test makes no outbound connection. They also check that all six URLs
return 404 under the normal production URL configuration. No separate server
or production database is needed.

## Run CodeQL

This repository has GitHub CodeQL **default setup** enabled for Python with the
extended query suite. Push to `main`, wait for the CodeQL Actions run to finish,
then inspect **Security → Code scanning**. Do not add a competing advanced-setup
workflow while default setup is enabled.

For local analysis, install the CodeQL CLI and Python query pack. From the root:

```sh
codeql pack download codeql/python-queries
codeql database create /tmp/product-fixtures-codeql-db --language=python --source-root=.
codeql database analyze /tmp/product-fixtures-codeql-db \
  codeql/python-queries:codeql-suites/python-security-extended.qls \
  --format=sarif-latest --output=/tmp/product-fixtures-codeql.sarif
```

Use a fresh database path for each extraction. Do not exclude `codeql_fixtures/`
from analysis. Record `codeql version` and the downloaded query-pack version
when comparing results; query behavior can change between releases.

## Expected findings

All six expected locations are in `codeql_fixtures/views.py`:

| Label | Function | Input → sink | CodeQL rule |
| --- | --- | --- | --- |
| SQLI-1 | `catalog_search` | GET `q` → `cursor.execute` | `py/sql-injection` |
| SQLI-2 | `price_report` | GET `ceiling` → `cursor.execute` | `py/sql-injection` |
| XSS-1 | `search_heading` | GET `q` → HTML response text | `py/reflective-xss` |
| XSS-2 | `promotion_preview` | GET `copy` → HTML response section | `py/reflective-xss` |
| XSS-3 | `stock_notice` | GET `sku` → HTML response attribute | `py/reflective-xss` |
| SSRF-1 | `supplier_probe` | GET `url` → `urllib.request.urlopen` | `py/full-ssrf` |

Expected fixture total: **2 SQL injection + 3 XSS + 1 SSRF = 6 alerts**.
Count the fixture paths and rules, not unrelated alerts elsewhere in the repo.
The JSON responses for SQL/report results and the SSRF status intentionally
avoid introducing additional HTML sinks.

These defects are deliberate. Real implementations should use SQL parameters,
context-appropriate HTML escaping (or sanitized rich text), and a restricted
supplier destination policy including redirect and resolved-address checks.

Query references: [SQL injection](https://codeql.github.com/codeql-query-help/python/py-sql-injection/),
[reflected XSS](https://codeql.github.com/codeql-query-help/python/py-reflective-xss/),
[full SSRF](https://codeql.github.com/codeql-query-help/python/py-full-ssrf/).
