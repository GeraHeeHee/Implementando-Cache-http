from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Auto


@receiver([post_save, post_delete], sender=Auto)
def invalidar_cache_autos(sender, **kwargs):
    try:
        cache.incr("autos_version")
    except ValueError:
        cache.set("autos_version", 2, None)