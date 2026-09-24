
### Comando para iniciar contenedores

```
docker compose up --build
```

En local se ve en: http://localhost:8000/.

Dejo ejemplo de .env, sacar .example. Al iniciar la base se crean los usuarios definidos ahi. Los permisos de los grupos se cargar a partir de lo definido en config/comun.py. El superusuario tiene todos.

### Comando custom para iniciar la base

Ver detalle en config/management/commands/iniciar.py

```
sudo docker compose exec web python manage.py iniciardb
```

Primero hace un flush de la base, así que si se quiere resetear también funciona.

Comando poblar opcional para cargar los modelos en config/fixtures/modelos

### Comando custom para hacer migraciones y migrar

```
docker compose exec web python manage.py migrar
```

### Comando para crear migraciones al crear/modificar modelos

```
docker compose exec web python manage.py makemigrations
```

### Comando para aplicar migraciones

```
docker compose exec web python manage.py migrate
```

### Comando para crear app nueva

```
docker compose exec web python manage.py startapp <nombre_app>
```

Si se ejecuta con sudo ejecutar el siguiente comando para no tener un tema de permisos:

```
sudo chown -R $USER:$USER .
```

### Pgadmin

Se accede en http://localhost:5050/ con datos definidos en .env.

### Listar versiones instaladas

A veces es mejor dejar la versión vacía en requirements.txt y elige la versión compatible con lo demás. Pero después especifiquenla por las dudas. Las pueden listar con:

```
docker compose exec web pip list
```
