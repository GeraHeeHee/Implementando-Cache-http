Examen2_Autos: caché en un endpoint GET de Django

Proyecto Django (6.1, SQLite) con una app de autos. Esta actividad implementa un sistema de caché en un endpoint GET que devuelve JSON y mide su efecto en los tiempos de respuesta con Postman.

Autor: Gerardo Ramírez

Contenido
Funcionalidad elegida
Endpoints
Tipo de caché
Estrategia de actualización
Cómo ejecutar el proyecto
Preparar los datos de prueba
Cómo reproducir las solicitudes
Tabla de tiempos
Evidencias
Conclusión
Funcionalidad elegida

Se optimizó la consulta del listado de autos de la app autos. El modelo Auto tiene los campos marca, modelo, anio y precio. Es una consulta que puede recibir muchas solicitudes repetidas, por lo que es un buen candidato para almacenarse en caché.

Como el proyecto original solo tenía vistas HTML, se agregaron dos endpoints JSON.

Endpoints
Método	URL	Descripción
GET	http://127.0.0.1:8000/api/autos/	Lista los autos en JSON (endpoint con caché). Admite ?marca=Honda.
POST	http://127.0.0.1:8000/api/autos/crear/	Crea un auto a partir de un JSON (sirve para probar la actualización del caché).

Respuesta del GET (código 200 OK):

json
[
  {"id": 1, "marca": "Honda", "modelo": "Sedán", "anio": 2020, "precio": "740000.00"}
]

Cuerpo del POST (código 201 Created):

json
{"marca": "Honda", "modelo": "Sedán", "anio": 2020, "precio": 740000}

Cada respuesta del GET incluye el encabezado X-Cache, que indica el origen de los datos:

Valor	Significado
SIN-CACHE	El caché está desactivado; se consultó la base de datos.
MISS	No había entrada en caché; se consultó la base de datos y se guardó el resultado.
HIT	Se reutilizó el resultado almacenado.

Además se imprime en la consola de Django una línea como [CACHE HIT] autos:v1: -> 0.05 ms.

Tipo de caché

Se utiliza el caché en memoria de Django (LocMemCache), configurado en config/settings.py:

python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "autos-cache",
    }
}

# False = prueba "sin caché", True = prueba "con caché"
CACHE_ACTIVADO = False
Clave de caché: autos:v{version}:{parametros}, por ejemplo autos:v1:marca=Honda. Incluye los parámetros de la URL para que cada filtro tenga su propia entrada, y un número de versión que se usa para invalidar el caché.
Qué se almacena: la lista de autos (resultado de la consulta a la base de datos) convertida a una lista de diccionarios.
Limitación: LocMemCache guarda los datos en la memoria del proceso, por lo que se vacía al reiniciar el servidor y no se comparte entre varios procesos. Para producción con varios workers se recomendaría Redis.
Vista con caché (autos/views.py)
python
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
Estrategia de actualización: invalidación al cambiar los datos

Las señales post_save y post_delete del modelo Auto (autos/signals.py) incrementan la versión almacenada en el caché (autos_version). Como la versión forma parte de la clave, las entradas anteriores dejan de utilizarse.

python
@receiver([post_save, post_delete], sender=Auto)
def invalidar_cache_autos(sender, **kwargs):
    try:
        cache.incr("autos_version")
    except ValueError:
        cache.set("autos_version", 2, None)

Las señales se registran en autos/apps.py:

python
class AutosConfig(AppConfig):
    name = "autos"

    def ready(self):
        from . import signals  # noqa

Operaciones que invalidan el caché:

Crear un auto (POST a la API, formulario HTML o admin).
Editar un auto (admin o shell).
Eliminar un auto.

Comportamiento del endpoint cuando cambia un registro: la siguiente solicitud GET responde X-Cache: MISS, consulta la base de datos, devuelve los datos actualizados y guarda la nueva entrada. Las solicitudes posteriores responden HIT con los datos ya actualizados.

Cómo ejecutar el proyecto
Clona el repositorio y entra a la carpeta del proyecto (la que contiene manage.py).
Crea y activa un entorno virtual:
bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux / macOS
Instala Django:
bash
pip install django
Aplica las migraciones:
bash
python manage.py migrate
Inicia el servidor:
bash
python manage.py runserver
El servidor queda disponible en http://127.0.0.1:8000/.
Preparar los datos de prueba

El proyecto tenía 3 autos. Para que la diferencia de tiempos sea apreciable se agregaron 5000 registros desde el shell (python manage.py shell):

python
from autos.models import Auto
Auto.objects.bulk_create([
    Auto(marca=f"Marca{i%20}", modelo=f"Modelo{i}", anio=2000 + i % 25, precio=100000 + i)
    for i in range(5000)
])

También se puede crear un auto con Postman (POST /api/autos/crear/, Body → raw → JSON) usando el cuerpo de la sección Endpoints.

Cómo reproducir las solicitudes
Prueba sin caché
En config/settings.py deja CACHE_ACTIVADO = False y reinicia el servidor.
En Postman envía 5 solicitudes consecutivas a GET http://127.0.0.1:8000/api/autos/.
Registra el tiempo en ms de cada una y calcula el promedio. El encabezado debe ser X-Cache: SIN-CACHE.
Prueba con caché
Cambia a CACHE_ACTIVADO = True (el servidor se reinicia y el caché queda vacío).
Envía una solicitud GET: debe mostrar X-Cache: MISS. Registra su tiempo por separado.
Envía 5 solicitudes más: todas deben mostrar X-Cache: HIT. Registra sus tiempos y calcula el promedio.
Verifica que el JSON coincida con el de la primera solicitud.
Prueba de actualización
Crea o edita un auto (POST a la API o desde /admin/).
Envía el GET: debe mostrar X-Cache: MISS y el JSON debe incluir el cambio.
Envía el GET de nuevo: debe mostrar X-Cache: HIT con los datos ya actualizados.
Tabla de tiempos

Tiempos en milisegundos, tomados del panel de respuesta de Postman.

Condición	Prueba 1	Prueba 2	Prueba 3	Prueba 4	Prueba 5	Promedio

Sin caché	_4.09_ ms	_39.69_ ms	_2.36_ ms	_4.54_ ms	_2.78_ ms	_10.692_ ms

Con caché	_0.22_ ms	_0.22_ ms	_0.17_ ms	_0.13_ ms	_0.45_ ms	_0.238_ ms

Evidencia

<img width="554" height="128" alt="image" src="https://github.com/user-attachments/assets/954406c3-907a-40dd-b89c-68818bde3857" />
<img width="418" height="37" alt="image" src="https://github.com/user-attachments/assets/ab1aa849-f44f-4e4d-8ba2-af17c4c88276" />
<img width="415" height="172" alt="image" src="https://github.com/user-attachments/assets/b1aa8337-8267-439f-8f4d-8c97d80619ee" />
<img width="554" height="186" alt="image" src="https://github.com/user-attachments/assets/053de242-8170-4e75-8053-bfdf1a5765dd" />
<img width="554" height="195" alt="image" src="https://github.com/user-attachments/assets/881ba40d-84d9-416b-bacc-437a98525ef7" />




