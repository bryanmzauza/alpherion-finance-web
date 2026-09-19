# apps/api — API do Alpherion + worker `data`

FastAPI (schema `market` via SQLAlchemy/Alembic), engine de risco (pandas) e a única chamada à Claude API. Não conhece usuários: recebe posições, devolve leituras. Detalhe em `docs/site.md` §2.3, §3, §6, §7.5.

```
uv sync                                   # instala (baixa o Python 3.12 se preciso)
uv run uvicorn alpherion.main:app --reload
uv run alembic upgrade head               # migra o schema market (usuário `data`)
uv run pytest · uv run ruff check . · uv run mypy .
python -m alpherion.data.jobs.<job>       # roda um job do worker à mão
```

O `.env` fica na raiz do monorepo.
