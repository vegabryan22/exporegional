# Modelo de Pruebas QA de ExpoTecnica

## 1. Objetivo

Este documento define el modelo de pruebas funcionales sugerido para QA.

Su objetivo es asegurar:

- cobertura de todos los módulos visibles del sistema
- claridad de que probar
- pasos sugeridos
- resultado esperado por caso

## 2. Alcance

Este modelo cubre:

- área pública
- autenticación
- panel de jueces
- panel administrativo
- reglas de permisos
- catálogos
- archivos
- logística
- evaluaciones
- mantenimiento
- auditoría

## 3. Tipos de prueba sugeridos

### 3.1 Smoke test

Para validar que el sistema está operativo después de un cambio.

### 3.2 Regresion funcional

Para validar que flujos que ya funcionaban no se rompieron.

### 3.3 Pruebas negativas

Para validar errores controlados y validaciones.

### 3.4 Pruebas de permisos

Para validar acceso correcto por rol y departamento.

### 3.5 Pruebas de integridad de datos

Para validar que se guarda lo correcto y no se duplican registros.

## 4. Datos base recomendados para QA

Preparar al menos:

- 1 superadmin
- 1 administrador por departamento:
  - logística
  - datos
  - diseño
  - QA
- 3 jueces activos
- 1 juez inactivo
- 1 campaña activa
- 1 campaña inactiva
- categorías:
  - STEAM
  - Emprendimiento
- tipos de evaluación:
  - Exposición STEAM
  - Documentación STEAM
  - Exposición Modelo de Negocios
  - Documento Modelo de Negocios
  - Documento Plan de Negocios
  - Inglés
- 1 proyecto activo completo
- 1 proyecto activo sin jueces
- 1 proyecto activo sin logo real
- 1 proyecto activo sin documento
- 1 proyecto activo con integrantes sin foto
- 1 proyecto inactivo

## 5. Criterios de salida sugeridos

Una liberación funcional debería salir a producción solo si:

- no hay fallos críticos en login, inscripción, evaluación o permisos
- no hay errores de acceso indebido entre módulos
- las notas finales y avances coinciden con cálculo esperado
- placeholders visuales no se cuentan como evidencias reales

## 6. Matriz de pruebas

## 6.1 Publico

### PUB-01 Home publica carga correctamente

Precondiciones:

- sistema sin mantenimiento publico

Pasos:

1. Abrir `/`
2. Verificar textos principales
3. Verificar presencia del logo de Expo si existe

Resultado esperado:

- la pagina carga sin error
- no aparecen proyectos inactivos
- branding institucional se muestra correctamente

### PUB-02 Home en mantenimiento

Precondiciones:

- mantenimiento habilitado
- usuario no autenticado como admin

Pasos:

1. Abrir `/proyectos`

Resultado esperado:

- se muestra pantalla de mantenimiento
- no se muestra listado publico

### PUB-03 Listado de proyectos

Precondiciones:

- existen proyectos activos en varias categorias

Pasos:

1. Abrir `/proyectos`
2. Navegar entre proyectos

Resultado esperado:

- solo aparecen proyectos activos
- el cambio entre paneles de proyecto funciona
- la categoria visible corresponde al proyecto

### PUB-04 Proyecto sin logo real usa logo generico

Precondiciones:

- proyecto activo sin logo real

Pasos:

1. Abrir `/proyectos`
2. Ir al proyecto sin logo

Resultado esperado:

- el proyecto muestra un logo generico
- el sistema no falla por falta de logo

### PUB-05 Documento visible solo cuando existe

Precondiciones:

- proyecto A con documento
- proyecto B sin documento

Pasos:

1. Ver proyecto A
2. Ver proyecto B

Resultado esperado:

- proyecto A muestra acceso al documento
- proyecto B muestra estado sin documentación

## 6.2 Inscripcion de proyectos

### REG-01 Bloqueo sin campana activa

Precondiciones:

- no existe campana activa vigente

Pasos:

1. Abrir `/inscripcion`

Resultado esperado:

- el sistema redirige al home
- muestra mensaje de que no hay campana activa

### REG-02 Alta exitosa con 1 estudiante

Precondiciones:

- campana activa
- catalogos academicos activos

Pasos:

1. Completar formulario con 1 estudiante
2. Adjuntar documento valido
3. Enviar

Resultado esperado:

- se crea proyecto
- se crea 1 integrante
- se guarda documento final
- se limpia borrador de sesion
- se muestra mensaje de exito

### REG-03 Alta exitosa con 3 estudiantes

Pasos:

1. Completar cadenas de estudiantes 1, 2 y 3
2. Confirmar respuestas de continuacion
3. Enviar

Resultado esperado:

- se crean exactamente 3 integrantes
- no se pierden datos intermedios

### REG-04 Documento invalido

Pasos:

1. Adjuntar archivo con extension no permitida
2. Enviar

Resultado esperado:

- no se crea el proyecto
- se muestra error de formato invalido

### REG-05 Datos faltantes del estudiante obligatorio

Pasos:

1. Omitir un campo obligatorio del estudiante 1
2. Enviar

Resultado esperado:

- no se crea el proyecto
- se muestra mensaje indicando el estudiante afectado

### REG-06 Tutor incompleto

Pasos:

1. Completar proyecto y estudiantes
2. Omitir un dato obligatorio del docente tutor
3. Enviar

Resultado esperado:

- no se crea el proyecto
- se muestra mensaje de tutor incompleto

### REG-07 Consentimiento no aceptado

Pasos:

1. Completar todo menos aceptacion final
2. Enviar

Resultado esperado:

- no se crea el proyecto
- aparece mensaje de aceptacion obligatoria

### REG-08 Conservacion de borrador

Pasos:

1. Adjuntar documento valido
2. Forzar error de validacion
3. Volver a revisar el formulario

Resultado esperado:

- los datos previos siguen presentes
- el documento temporal sigue asociado

## 6.3 Autenticacion

### AUTH-01 Login exitoso de juez

Pasos:

1. Ir a `/auth/login`
2. Ingresar credenciales validas de juez

Resultado esperado:

- redirige a `/juez/panel`

### AUTH-02 Login exitoso de admin

Pasos:

1. Login con usuario administrador

Resultado esperado:

- redirige a `/admin/panel`

### AUTH-03 Credenciales invalidas

Pasos:

1. Ingresar correo o contrasena incorrecta

Resultado esperado:

- no inicia sesion
- aparece mensaje de credenciales invalidas
- se registra evento en bitacora

### AUTH-04 Usuario inactivo

Pasos:

1. Login con usuario inactivo

Resultado esperado:

- no inicia sesion
- aparece mensaje de usuario inactivo

### AUTH-05 Cambio obligatorio de contrasena

Precondiciones:

- usuario con `must_change_password = true`

Pasos:

1. Iniciar sesion

Resultado esperado:

- redirige a cambio de contrasena

### AUTH-06 Cambio de contrasena exitoso

Pasos:

1. Entrar a `/auth/cambiar-contrasena`
2. Ingresar actual correcta
3. Ingresar nueva >= 8 caracteres
4. Confirmar

Resultado esperado:

- actualiza contrasena
- desactiva requerimiento de cambio
- redirige segun rol

### AUTH-07 Cambio de contrasena con confirmacion distinta

Resultado esperado:

- no guarda
- muestra mensaje de confirmacion no coincide

### AUTH-08 Logout

Pasos:

1. Cerrar sesion

Resultado esperado:

- termina sesion
- redirige a login
- registra evento

## 6.4 Panel de juez

### JUEZ-01 Ver solo proyectos asignados

Precondiciones:

- juez con varios proyectos asignados

Pasos:

1. Abrir `/juez/panel`

Resultado esperado:

- solo aparecen proyectos asignados al juez actual

### JUEZ-02 Ver tipos de evaluacion por proyecto

Resultado esperado:

- cada proyecto muestra solo los tipos disponibles para su categoria
- ingles aparece segun configuracion activa

### JUEZ-03 Registrar evaluacion valida

Pasos:

1. Abrir un proyecto asignado
2. Capturar todos los criterios dentro del rango
3. Guardar

Resultado esperado:

- se crea `Evaluation`
- se crean `EvaluationScore`
- porcentaje queda calculado
- dashboard marca ese tipo como completado

### JUEZ-04 Evitar duplicado de evaluacion

Precondiciones:

- ya existe evaluacion del mismo juez, proyecto y tipo

Pasos:

1. Intentar abrir de nuevo la misma evaluacion

Resultado esperado:

- no permite registrar otra
- redirige al panel con mensaje

### JUEZ-05 Puntaje fuera de rango

Pasos:

1. Ingresar valor menor que min o mayor que max
2. Guardar

Resultado esperado:

- no guarda
- muestra criterio que fallo

### JUEZ-06 Proyecto no asignado

Pasos:

1. Acceder manualmente a `/juez/proyecto/<id>/evaluar`

Resultado esperado:

- responde con acceso denegado o 403

## 6.5 Resumen admin

### ADM-OV-01 Centro de operaciones carga

Resultado esperado:

- muestra indicadores y tablas sin error

### ADM-OV-02 Considera solo proyectos activos

Precondiciones:

- existe proyecto inactivo sin logo y sin jueces

Resultado esperado:

- ese proyecto no afecta indicadores

### ADM-OV-03 Logo generico no cuenta como logo real

Resultado esperado:

- proyecto sin logo real sigue contado en `proyectos sin logo`

## 6.6 Asignaciones

### ADM-ASG-01 Ver solo proyectos activos

Resultado esperado:

- tabla y contadores trabajan con proyectos activos

### ADM-ASG-02 Crear asignacion

Pasos:

1. Asignar juez existente a proyecto activo

Resultado esperado:

- se crea `Assignment`
- contador sube

### ADM-ASG-03 No duplicar juez en mismo proyecto

Resultado esperado:

- no guarda duplicado
- muestra mensaje

### ADM-ASG-04 Reemplazo rapido de juez

Pasos:

1. Abrir gestion de proyecto
2. Reemplazar juez asignado por otro

Resultado esperado:

- la asignacion queda actualizada
- se registra auditoria

### ADM-ASG-05 Crear juez rapido y asignar

Resultado esperado:

- se crea usuario juez
- se crea asignacion
- se envian correos si SMTP esta operativo

## 6.7 Usuarios

### ADM-USR-01 Crear juez sin departamento

Resultado esperado:

- guarda correctamente

### ADM-USR-02 Crear admin sin departamento

Resultado esperado:

- no guarda
- exige departamento

### ADM-USR-03 Un solo usuario generico por departamento

Pasos:

1. Crear admin en Logistica
2. Intentar crear otro admin generico en Logistica

Resultado esperado:

- segundo alta rechazada

### ADM-USR-04 Correo duplicado

Resultado esperado:

- el sistema no permite repetir email

### ADM-USR-05 Reset o cambio de contrasena

Resultado esperado:

- la nueva contrasena funciona en login

## 6.8 Permisos

### ADM-PER-01 Solo superadmin puede editar

Pasos:

1. Entrar con admin normal a `/admin/permisos`

Resultado esperado:

- puede ver si aplica
- no puede editar si no es superadmin

### ADM-PER-02 Guardar matriz de permisos

Pasos:

1. Habilitar o deshabilitar modulos por departamento
2. Guardar

Resultado esperado:

- el cambio persiste
- afecta visibilidad del menu

### ADM-PER-03 Acceso real restringido

Pasos:

1. Quitar modulo a un departamento
2. Login con usuario de ese departamento
3. Intentar entrar por URL directa

Resultado esperado:

- acceso denegado

## 6.9 Campanas

### ADM-CAMP-01 Crear campana valida

Resultado esperado:

- se guarda con fechas correctas

### ADM-CAMP-02 Activar campana

Resultado esperado:

- la inscripcion publica la reconoce si la fecha esta vigente

### ADM-CAMP-03 Fecha invalida

Resultado esperado:

- no guarda si fin es menor que inicio

## 6.10 Categorias

### ADM-CAT-01 Crear categoría con exposición y documentación

Resultado esperado:

- guarda correctamente

### ADM-CAT-02 No permitir misma rubrica en ambos campos

Resultado esperado:

- rechaza guardado

### ADM-CAT-03 No permitir rubrica de ingles como base

Resultado esperado:

- rechaza guardado

### ADM-CAT-04 Detectar tipo incorrecto

Pasos:

1. Colocar una rúbrica documental en exposición o viceversa

Resultado esperado:

- el sistema rechaza la configuracion

## 6.11 Academico

### ADM-ACA-01 Crear nivel, seccion, especialidad y taller

Resultado esperado:

- cada catalogo aparece disponible en inscripcion

### ADM-ACA-02 No eliminar seccion con proyectos

Resultado esperado:

- sistema bloquea eliminacion

### ADM-ACA-03 No eliminar especialidad o taller con proyectos

Resultado esperado:

- sistema bloquea eliminacion

## 6.12 Rubricas y tipos de evaluacion

### ADM-RUB-01 Crear tipo de evaluacion

Resultado esperado:

- guarda `name`, `description`, `code`, `sort_order`

### ADM-RUB-02 Editar nombre corto y descripcion

Resultado esperado:

- tabla muestra nombre corto
- descripcion larga permanece visible como apoyo

### ADM-RUB-03 Eliminar tipo con rubricas asociadas

Resultado esperado:

- sistema no permite eliminar

### ADM-RUB-04 Crear rubrica valida

Resultado esperado:

- criterio aparece bajo el tipo correcto

### ADM-RUB-05 Puntos maximos

Resultado esperado:

- columna `Puntos max.` coincide con suma de `max_score` de rubricas activas

### ADM-RUB-06 Tipo eliminado no reaparece

Resultado esperado:

- despues de eliminar manualmente, no reaparece al reiniciar la app

## 6.13 Proyectos y logistica

### ADM-PRO-01 Editar datos basicos de proyecto

Resultado esperado:

- cambios persisten y se reflejan en vistas

### ADM-PRO-02 Subir logo real del proyecto

Resultado esperado:

- se guarda archivo
- `has_real_logo` pasa a verdadero

### ADM-PRO-03 Proyecto sin logo muestra placeholder pero sigue pendiente

Resultado esperado:

- visualmente hay logo generico
- logisticamente sigue faltando logo real

### ADM-PRO-04 Subir fotos de integrantes

Resultado esperado:

- la foto reemplaza placeholder
- ya no se cuenta como foto faltante

### ADM-PRO-05 Eliminar integrante

Resultado esperado:

- se elimina integrante
- no quedan referencias rotas

### ADM-PRO-06 Proyecto inactivo no aparece en vistas publicas

Resultado esperado:

- desaparece de home y proyectos

## 6.14 Evaluaciones admin

### ADM-EVA-01 Dashboard de evaluaciones carga

Resultado esperado:

- resumen, tracking y ranking cargan sin error

### ADM-EVA-02 Solo considera proyectos activos

Resultado esperado:

- proyectos inactivos no alteran ranking ni resumen

### ADM-EVA-03 Identificación correcta de Exposición y Documentación

Resultado esperado:

- nunca aparecen dos documentaciones para la misma categoria salvo que realmente existan dos tipos distintos

### ADM-EVA-04 Nota por rubrica

Precondiciones:

- 3 jueces asignados
- 1 evaluación registrada en Exposición

Resultado esperado:

- el estado de rubrica muestra `1/3`
- el porcentaje mostrado corresponde al promedio actual sobre 100

### ADM-EVA-05 Nota final

Resultado esperado:

- la nota final equivale a la suma de aportes de exposición y documentación

### ADM-EVA-06 Eliminar evaluacion

Resultado esperado:

- baja el avance
- se actualizan resumenes y ranking

## 6.15 SMTP

### ADM-SMTP-01 Guardar configuracion SMTP

Resultado esperado:

- persiste en settings

### ADM-SMTP-02 Probar envio

Resultado esperado:

- si la configuracion es valida, envio exitoso
- si es invalida, mensaje claro de error

## 6.16 Institucion

### ADM-INS-01 Guardar datos institucionales

Resultado esperado:

- se reflejan en header y footer

### ADM-INS-02 Cargar logo del colegio

Resultado esperado:

- se ve en header y login

### ADM-INS-03 Cargar logo de ExpoTecnica

Resultado esperado:

- se ve en home, formulario y banners de expo

### ADM-INS-04 No mezclar logos

Resultado esperado:

- cambiar logo Expo no modifica logo del colegio
- cambiar logo del colegio no modifica logo Expo

## 6.17 Mantenimiento

### ADM-MNT-01 Activar mantenimiento

Resultado esperado:

- area publica entra en mantenimiento
- admin autenticado puede seguir operando

### ADM-MNT-02 Desactivar mantenimiento

Resultado esperado:

- publico vuelve a ver home y proyectos

## 6.18 Bitacora

### ADM-LOG-01 Ver eventos recientes

Resultado esperado:

- aparecen login, logout y cambios administrativos relevantes

### ADM-LOG-02 Trazabilidad de accion critica

Pasos:

1. Reemplazar asignacion
2. Revisar bitacora

Resultado esperado:

- queda registro con suficiente detalle

## 7. Paquete mínimo de smoke test por build

Ejecutar al menos:

1. Login admin valido
2. Login juez valido
3. Home publica carga
4. Proyectos publicos cargan
5. Inscripcion bloquea sin campana o guarda con campana
6. Admin puede abrir:
   - asignaciones
   - proyectos
   - evaluaciones
   - usuarios
7. Juez puede registrar una evaluacion
8. Nota final se recalcula
9. Mantenimiento bloquea area publica
10. Bitacora registra la accion

## 8. Riesgos funcionales prioritarios

- permisos inconsistentes por departamento
- categorias mal conectadas con rubricas
- evaluaciones duplicadas
- placeholders contados como evidencia real
- proyectos inactivos incluidos en reportes
- correos o archivos no persistidos correctamente

## 9. Evidencia sugerida por caso

QA deberia adjuntar:

- captura de pantalla
- URL probada
- usuario usado
- datos cargados
- resultado observado
- resultado esperado
- severidad si falla

## 10. Prioridad recomendada

Prioridad alta:

- login
- inscripcion
- asignaciones
- evaluacion de juez
- calculo de nota final
- permisos

Prioridad media:

- catalogos
- branding institucional
- SMTP
- mantenimiento

Prioridad baja:

- ajustes visuales no bloqueantes
- ordenamientos cosmeticos
