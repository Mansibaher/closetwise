# Official integration references checked during implementation

- [Next.js installation](https://nextjs.org/docs/app/getting-started/installation): Node runtime and App Router setup.
- [Next.js rewrites](https://nextjs.org/docs/app/api-reference/config/next-config-js/rewrites): same-origin API proxy.
- [FastAPI password hashing and JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/): pwdlib/Argon2 and PyJWT primitives.
- [SQLAlchemy ORM quick start](https://docs.sqlalchemy.org/en/20/orm/quickstart.html): typed SQLAlchemy 2 models and sessions.
- [Vision input guide](https://developers.openai.com/api/docs/guides/images-vision): optional image-input provider.

Package availability was also checked against npm and PyPI, followed by local installation, type checking, production compilation, backend tests, and browser tests. Lockfiles capture the versions actually installed. See `VERIFICATION.md` for execution limits.
