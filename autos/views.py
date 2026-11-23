import json
import time
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.shortcuts import render, redirect
from .models import Auto
from .forms import AutoForm


def lista_autos(request):
    autos = Auto.objects.all()
    return render(request, 'autos/lista_autos.html', {'autos': autos})


def agregar_auto(request):
    if request.method == 'POST':
        form = AutoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_autos')
    else:
        form = AutoForm()
    return render(request, 'autos/agregar_auto.html', {'form': form})

def _version():
    return cache.get_or_set("autos_version", 1, None)


@require_GET
def api_autos(request):
    inicio = time.perf_counter()
    params = request.GET.urlencode()
    key = f"autos:v{_version()}:{params}"

    data = cache.get(key) if settings.CACHE_ACTIVADO else None

    if data is not None:
        origen = "HIT"
    else:
        origen = "MISS" if settings.CACHE_ACTIVADO else "SIN-CACHE"
        qs = Auto.objects.all().order_by("id")
        marca = request.GET.get("marca")
        if marca:
            qs = qs.filter(marca__iexact=marca)
        data = list(qs.values("id", "marca", "modelo", "anio", "precio"))
        if settings.CACHE_ACTIVADO:
            cache.set(key, data, None)  # se invalida con señales, no por tiempo

    ms = (time.perf_counter() - inicio) * 1000
    print(f"[CACHE {origen}] {key} -> {ms:.2f} ms")

    response = JsonResponse(data, safe=False, status=200)
    response["X-Cache"] = origen
    return response


@csrf_exempt  # solo para pruebas con Postman en esta actividad
@require_POST
def api_crear_auto(request):
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    form = AutoForm(payload)
    if not form.is_valid():
        return JsonResponse({"errores": form.errors}, status=400)
    auto = form.save()
    return JsonResponse(
        {"id": auto.id, "marca": auto.marca, "modelo": auto.modelo,
         "anio": auto.anio, "precio": str(auto.precio)},
        status=201,
    )