from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.core.cache import cache
from django.core.cache.backends.base import BaseCache
from django_redis import get_redis_connection  # type: ignore
from .models import Sala

@login_required
def participantes_sidebar(request, sala_id):
    sala = Sala.objects.get(id=sala_id)
    # Presence baseada em cache com TTL (setada pelo consumer via heartbeat)
    online_ids = []
    # Se estiver usando RedisCache, podemos varrer as chaves por padrão
    backend = getattr(cache, 'client', None) or getattr(cache, 'backend', None)
    found = set()
    try:
        # django-redis
        r = get_redis_connection('default')
        pattern = f"*presence:sala:{sala_id}:user:*:chan:*"
        for raw in r.scan_iter(pattern):
            try:
                key = raw.decode('utf-8') if isinstance(raw, (bytes, bytearray)) else str(raw)
                # Extrai user_id
                parts = key.split(':')
                # [..., 'sala', sala_id, 'user', <id>, 'chan', <name>]
                idx = parts.index('user') if 'user' in parts else -1
                if idx != -1 and idx + 1 < len(parts):
                    uid = int(parts[idx + 1])
                    found.add(uid)
            except Exception:
                continue
    except Exception:
        # Fallback: sem Redis, verifica por participante (LocMem não dá scan eficiente)
        for u in sala.participantes.all():
            # Mantemos compat com antiga chave sem canal, caso exista
            legacy = f"presence:sala:{sala_id}:user:{u.id}"
            any_chan = False
            if cache.get(legacy, 0):
                any_chan = True
            else:
                # Tentativa best-effort: alguns backends expõem _cache dict
                try:
                    _store = getattr(cache, '_cache', {})
                    for k in _store.keys():
                        if isinstance(k, str) and f"presence:sala:{sala_id}:user:{u.id}:chan:" in k:
                            any_chan = True; break
                except Exception:
                    pass
            if any_chan:
                found.add(u.id)
    if found:
        # Mantém a ordem por sala.participantes
        for u in sala.participantes.all():
            if u.id in found:
                online_ids.append(u.id)
    return render(
        request,
        'salas/_sidebar_participantes.html',
        {
            'sala': sala,
            'user': request.user,
            'online_ids': online_ids,
        },
    )
