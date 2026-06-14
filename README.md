# Asterisk GUI Manager

Panel de administración web para Asterisk PBX. Gestiona extensiones, troncales, rutas, IVR, colas y más desde una interfaz moderna.

---

## Arquitectura de contenedores

```
Host (Ubuntu)
├── /opt/asterisk/          ← Asterisk (docker-compose propio)
│   ├── docker-compose.yml  ← network_mode: host
│   └── etc/                ← Configuración compartida con el backend
│
└── /home/ubuntu/GUIAsterisk/   ← Este proyecto
    ├── docker-compose.yml
    ├── backend/            ← FastAPI (puerto 8001)
    ├── frontend/           ← React/Nginx (puerto 8090)
    └── backend/.env        ← Variables de entorno
```

> **Red**: Asterisk usa `network_mode: host` — no está en `pbx_net`.
> El backend se comunica con él via `host.docker.internal`.

---

## Requisitos previos

- Docker Engine 24+
- Docker Compose v2
- Asterisk corriendo en `/opt/asterisk/` con su propio `docker-compose.yml`
- Volumen compartido `/opt/asterisk/etc` montado por ambos (Asterisk y backend)

---

## Primera vez — Setup completo

### 1. Clonar el repositorio

```bash
git clone https://github.com/cesen7432-bit/GUIAsterisk.git /home/ubuntu/GUIAsterisk
cd /home/ubuntu/GUIAsterisk
```

### 2. Crear el archivo de entorno del backend

```bash
cp backend/.env.example backend/.env   # si existe
# o crear manualmente:
cat > backend/.env << 'EOF'
SECRET_KEY=cambia-este-secreto-por-uno-seguro
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

DB_HOST=db
DB_PORT=3306
DB_USER=pbxuser
DB_PASSWORD=tu_password_db
DB_NAME=asterisk_gui

AMI_HOST=host.docker.internal
AMI_PORT=5038
AMI_USER=admin
AMI_PASSWORD=tu_password_ami

ARI_HOST=host.docker.internal
ARI_PORT=8088
ARI_USER=ariuser
ARI_PASSWORD=tu_password_ari

ASTERISK_CONFIG_PATH=/etc/asterisk
RECORDINGS_PATH=/var/spool/asterisk/monitor
SOUNDS_PATH=/var/lib/asterisk/sounds/custom
SERVER_IP=IP_PUBLICA_DEL_SERVIDOR

ADMIN_EMAIL=admin@pbx.local
ADMIN_PASSWORD=admin1234
EOF
```

> **Importante**: `AMI_HOST` debe ser `host.docker.internal`, no `asterisk`.

### 3. Crear el archivo de entorno de la base de datos

```bash
cat > .env << 'EOF'
DB_ROOT_PASSWORD=root_password_seguro
DB_NAME=asterisk_gui
DB_USER=pbxuser
DB_PASSWORD=tu_password_db
EOF
```

### 4. Crear la red Docker compartida

```bash
docker network create pbx_net
```

> La red se crea automáticamente con `docker compose up`, pero si falla porque ya existe, ignora el error.

### 5. Levantar los servicios

```bash
docker compose up -d
```

Al arrancar, el backend:
- Crea las tablas de la base de datos
- Ejecuta migraciones pendientes
- Crea el usuario admin si no existe (`ADMIN_EMAIL` / `ADMIN_PASSWORD`)
- Genera `asterisk.conf` y `manager.conf` en `/opt/asterisk/etc/` si no existen

### 6. Reiniciar Asterisk para cargar el nuevo manager.conf

```bash
docker restart asterisk
```

### 7. Acceder a la GUI

```
http://IP_DEL_SERVIDOR:8090
Usuario: admin@pbx.local
Contraseña: admin1234  (cambiar después de primer login)
```

---

## Operaciones diarias

### Levantar todos los servicios

```bash
cd /home/ubuntu/GUIAsterisk
docker compose up -d
```

### Detener todos los servicios

```bash
docker compose down
```

### Ver logs en tiempo real

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker logs -f asterisk
```

### Reiniciar un servicio específico

```bash
docker compose restart backend
docker compose restart frontend
```

---

## Actualizar el código (después de git pull)

```bash
cd /home/ubuntu/GUIAsterisk
git pull

# Reconstruir solo lo que cambió
docker compose build --no-cache backend
docker compose build --no-cache frontend

# Levantar con la nueva imagen
docker compose up -d
```

> Si solo cambió el backend, omite el `build` de frontend y viceversa.

### Verificar qué servicios cambiaron

```bash
git log --oneline -10
git diff HEAD~1 --name-only
```

---

## Reconstrucción completa (desde cero)

```bash
# Detener y eliminar contenedores e imágenes
docker compose down --rmi all

# Reconstruir todo
docker compose build --no-cache

# Levantar
docker compose up -d
```

> La base de datos (`mariadb_data`) **no se elimina** con `--rmi all`.
> Para borrar también los datos: `docker compose down -v` ⚠️

---

## Red Docker

```
pbx_net (bridge 10.10.10.0/24)
├── pbx_db       (MariaDB   — 3306)
├── pbx_backend  (FastAPI   — 8000 interno / 8001 host)
└── pbx_frontend (Nginx     — 80 interno / 8090 host)

host (network_mode: host)
└── asterisk     (AMI: 5038, SIP: 5060, ARI: 8088)
```

### Recrear la red si fue eliminada

`docker compose up -d` la crea automáticamente. Solo es necesario crearla manualmente si vas a levantar contenedores fuera del compose:

```bash
docker network create --driver bridge --subnet 10.10.10.0/24 pbx_net
# Si responde "already exists", la red ya está — no hay problema.
```

### Verificar conectividad backend → Asterisk AMI

```bash
docker exec pbx_backend python3 -c \
  "import socket; s=socket.create_connection(('host.docker.internal',5038),2); print('OK - AMI alcanzable'); s.close()"
# Esperado: OK - AMI alcanzable
```

---

## Configuración de Asterisk

Los archivos de configuración se escriben automáticamente en `/opt/asterisk/etc/` cada vez que guardas cambios en la GUI.

Para aplicar cambios manualmente sin reiniciar Asterisk:

```bash
# Recargar dialplan
docker exec asterisk asterisk -rx "dialplan reload"

# Recargar PJSIP (extensiones y trunks)
docker exec asterisk asterisk -rx "module reload res_pjsip.so"

# Recargar todo
docker exec asterisk asterisk -rx "core reload"
```

### Verificar estado del AMI

```bash
docker exec asterisk asterisk -rx "manager show users"
docker exec asterisk asterisk -rx "manager show connected"
```

---

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| "AMI Desconectado" en GUI | `AMI_HOST=asterisk` en `.env` | Cambiar a `AMI_HOST=host.docker.internal` |
| "AMI Desconectado" en GUI | Credenciales incorrectas | Verificar `manager.conf` y `.env` coincidan |
| Cambios en GUI no afectan Asterisk | Asterisk no recargó | `docker exec asterisk asterisk -rx "core reload"` |
| Error 403 en login | Sin usuario admin | El backend lo crea al arrancar si no existe |
| Backend no conecta a DB | Contraseñas no coinciden | Verificar `.env` (raíz) y `backend/.env` |
| Puerto 8090 no responde | Frontend no levantó | `docker compose logs frontend` |
