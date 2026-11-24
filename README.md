# TECinnovaacces
Sistema web de automatización para reporte, reactivación y reposición de tarjetas de acceso institucional (TecNM Campus Matehuala) - BitStream Innova.

# AccesoTec — Sistema Web de Control de Acceso y Reposición de Tarjetas

**Empresa Consultora:** BitStream Innova  
**Cliente:** Instituto Tecnológico Nacional de México, Campus Matehuala  
**Asignatura:** Fundamentos de Ingeniería de Software (SCC-1007)

---

## 1. Descripción del Problema y Solución Propuesta

En el acceso del plantel y en la ventanilla del **Departamento de Almacén**, el trámite para reportar, reactivar o reponer tarjetas de acceso institucional dañadas o con fallas de lectura se realiza de forma manual. Se identificó que el área carece de procedimientos formales y registros físicos estandarizados, lo que provoca tiempos de espera, dependencia de los guardias de seguridad para ingresos provisionales y falta de trazabilidad.

**AccesoTec** digitaliza este proceso mediante una aplicación web desarrollada con **Python (Flask)**, **Microsoft SQL Server (`pyodbc`)** y **HTML/Bootstrap**, incorporando:
- **Portal del Alumno:** Registro de incidencias en línea, consulta de estatus y generación automática de un **Pase QR Temporal** válido por 72 horas.
- **Portal del Guardia:** Validación rápida de pases QR temporales en torniquetes y registro automático en bitácora digital.
- **Portal de Almacén:** Control centralizado de reportes, actualización de estados (`Pendiente`, `En_Proceso`, `Resuelto`), reactivación o asignación de nuevo código RFID y desactivación automática del pase temporal al resolver.


erDiagram
    USUARIOS ||--o{ TARJETAS : posee
    USUARIOS ||--o{ INCIDENCIAS_ACCESO : reporta
    TARJETAS ||--o{ INCIDENCIAS_ACCESO : vinculada_a
    INCIDENCIAS_ACCESO ||--o{ BITACORA_ACCESOS_QR : genera
    USUARIOS ||--o{ BITACORA_ACCESOS_QR : valida

    USUARIOS {
        int id_usuario PK
        string identificador UK
        string nombre_completo
        string correo UK
        string rol
        string carrera_o_area
    }

    TARJETAS {
        int id_tarjeta PK
        string codigo_rfid UK
        int id_usuario FK
        string estado
    }

    INCIDENCIAS_ACCESO {
        int id_incidencia PK
        string folio UK
        int id_usuario FK
        int id_tarjeta_afectada FK
        string motivo
        string codigo_qr_temporal UK
        datetime qr_expiracion
        string estatus_tramite
        int atendido_por FK
    }

    BITACORA_ACCESOS_QR {
        int id_log PK
        int id_incidencia FK
        int id_guardia FK
        string puerta_acceso
        string resultado_validacion
        datetime fecha_hora_escaneo
    }
## 2. Diagrama del Proceso Automatizado (TO-BE)

```mermaid
flowchart TD
    A[Alumno detecta fallo en tarjeta] --> B[Inicia sesión en AccesoTec]
    B --> C[Registra incidencia en línea]
    C --> D[(SQL Server: incidencias_acceso)]
    D --> E[Genera Pase QR Temporal - 72h]
    E --> F[Guardia valida QR en acceso]
    F --> G[(Registra en bitacora_accesos_qr)]
    C --> H[Almacén atiende reporte en panel]
    H --> I{¿Requiere nuevo plástico?}
    I -->|Sí| J[Asigna nuevo RFID y marca Resuelto]
    I -->|No| K[Reactiva chip y marca Resuelto]
    J --> L[QR temporal queda inactivo y tarjeta Activa]
    K --> L



TECinnovaacces/
├── backend/
│   ├── app.py
│   └── requirements.txt
├── database/
│   └── schema_y_datos.sql
├── docs/
├── frontend/
│   ├── static/
│   └── templates/
│       ├── index.html
│       ├── panel_alumno.html
│       ├── panel_guardia.html
│       └── panel_almacen.html
└── README.md







