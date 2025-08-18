# Deploy do mm3_rpg (Render + Neon + Upstash)

## Resumo
- Hosting: Render (Web Service)
- Banco: Neon (Postgres free)
- Redis: Upstash (Redis free)
- CI: GitHub Actions (`.github/workflows/ci.yml`)

## Passo a passo
1. Crie o Postgres no Neon e copie a `DATABASE_URL`.
2. Crie o Redis no Upstash e copie a `REDIS_URL` (rediss://...).
3. Configure variáveis no Render:
   - Crie um novo Web Service a partir deste repo. O Render detectará `render.yaml`.
   - Em Environment, defina:
     - `DATABASE_URL`: a URL do Neon
     - `REDIS_URL`: a URL do Upstash (rediss://...)
     - `SECRET_KEY`: pode deixar o `generateValue` do render.yaml gerar ou definir você mesmo
     - `ALLOWED_HOSTS`: seu domínio no Render (ex.: mm3-rpg.onrender.com)
     - `CSRF_TRUSTED_ORIGINS`: https://mm3-rpg.onrender.com
     - `DEBUG`: False
4. Deploy: o Render executa `pip install`, `collectstatic` e inicia `daphne`.
5. Após o primeiro deploy, rode migrações (opções):
   - via Shell do Render (bash) => `python manage.py migrate --noinput`
   - ou automaticamente adicionando `python manage.py migrate --noinput` no `buildCommand` do render.yaml.

## Dados existentes no SQLite (opcional)
- Localmente, antes de mudar o DB:
  - `python manage.py dumpdata --natural-primary --natural-foreign > dump.json`
- Com o `DATABASE_URL` apontando para o Neon:
  - `python manage.py migrate --noinput`
  - `python manage.py loaddata dump.json`

## Rodar local com Neon/Upstash
- Crie um `.env` com as variáveis (veja `.env.example`).
- `pip install -r requirements.txt`
- `python manage.py migrate --noinput`
- `daphne -b 0.0.0.0 -p 8000 mm3_site.asgi:application`

## Dicas
- Para mídia persistente, se precisar, use um bucket (S3/Cloudflare R2) ou ative disco persistente no host escolhido.
- Se trocar de host (Railway/Fly/Heroku), apenas ajuste as variáveis e o comando de start (sempre ASGI com `daphne`).
