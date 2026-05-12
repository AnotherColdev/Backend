# Microservicio de Autenticación (ms-auth)

Este microservicio gestiona la identidad de los usuarios, el control de acceso basado en roles (RBAC) y la seguridad de la plataforma mediante tokens JWT.

## 📋 Responsabilidades

1.  **Registro de Usuarios**: Creación de nuevas cuentas con hashing seguro.
2.  **Autenticación**: Validación de credenciales y generación de Access & Refresh Tokens.
3.  **Gestión de Perfiles**: Consulta y actualización de datos de usuario.
4.  **Control de Roles**: Manejo de permisos para los roles `USER` y `ADMIN`.

---

## 🔐 Seguridad y Ajustes Críticos

### Bcrypt & SHA256 (Fix Límite 72-bytes)
Se detectó un problema técnico donde Bcrypt fallaba al recibir contraseñas largas (>72 bytes) o caracteres especiales complejos. Para solucionar esto sin comprometer la seguridad, se implementó el siguiente flujo:
1.  La contraseña se pre-hashea con **SHA256**.
2.  El hash resultante se procesa con **Bcrypt**.
Esto garantiza compatibilidad con cualquier longitud de contraseña y mayor resistencia a colisiones.

### Naming Convention
Todos los métodos de seguridad y variables internas han sido refactorizados a **camelCase** para alinearse con el estándar del proyecto.

---

## 🚀 Endpoints Principales

### `POST /login`
Autentica al usuario y devuelve los tokens JWT.
- **Campos**: `username`, `password`.

### `POST /register`
Registra un nuevo usuario en el sistema.

### `GET /admin/users/` (Solo ADMIN)
Permite a los administradores listar y gestionar todos los usuarios registrados.

---

## 🛠 Especificaciones Técnicas

- **Framework**: FastAPI
- **Seguridad**: Passlib + PyJWT (jose)
- **Base de Datos**: PostgreSQL (Esquema `auth`)

---
*La seguridad es el pilar de nuestra plataforma. Cualquier cambio en este componente debe seguir estrictamente los principios SOLID.*
