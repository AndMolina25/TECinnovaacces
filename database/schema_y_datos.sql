-- ============================================================================
-- Proyecto: Sistema de Control de Acceso y Reposición de Tarjetas (AccesoTec)
-- Empresa Consultora: BitStream Innova
-- Cliente: Instituto Tecnológico de Matehuala
-- Motor: Microsoft SQL Server (T-SQL)
-- ============================================================================

IF DB_ID('bitstream_accesotec') IS NOT NULL
BEGIN
    ALTER DATABASE bitstream_accesotec SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE bitstream_accesotec;
END
GO

CREATE DATABASE bitstream_accesotec;
GO

USE bitstream_accesotec;
GO

-- 1. Tabla de Usuarios (Roles: Alumno, Guardia, Almacen)
CREATE TABLE usuarios (
    id_usuario INT IDENTITY(1,1) PRIMARY KEY,
    identificador VARCHAR(20) NOT NULL UNIQUE,
    nombre_completo VARCHAR(100) NOT NULL,
    correo VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol VARCHAR(20) NOT NULL CHECK (rol IN ('Alumno', 'Guardia', 'Almacen')),
    carrera_o_area VARCHAR(100) NOT NULL,
    fecha_registro DATETIME DEFAULT GETDATE()
);
GO

-- 2. Tabla de Tarjetas de Acceso Institucional
CREATE TABLE tarjetas (
    id_tarjeta INT IDENTITY(1,1) PRIMARY KEY,
    codigo_rfid VARCHAR(50) NOT NULL UNIQUE,
    id_usuario INT NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'Activa' CHECK (estado IN ('Activa', 'Dañada', 'En_Reposicion', 'Bloqueada')),
    ultima_actualizacion DATETIME DEFAULT GETDATE(),
    CONSTRAINT FK_tarjetas_usuarios FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE
);
GO

-- 3. Tabla de Incidencias y Pases QR Temporales (Sustituye libretas de papel)
CREATE TABLE incidencias_acceso (
    id_incidencia INT IDENTITY(1,1) PRIMARY KEY,
    folio VARCHAR(20) NOT NULL UNIQUE,
    id_usuario INT NOT NULL,
    id_tarjeta_afectada INT NOT NULL,
    motivo VARCHAR(50) NOT NULL CHECK (motivo IN ('Falla de lectura en torniquete', 'Daño físico del plástico', 'Extravío o robo')),
    descripcion_alumno NVARCHAR(MAX) NULL,
    codigo_qr_temporal VARCHAR(100) NOT NULL UNIQUE,
    qr_expiracion DATETIME NOT NULL,
    estatus_tramite VARCHAR(20) NOT NULL DEFAULT 'Pendiente' CHECK (estatus_tramite IN ('Pendiente', 'En_Proceso', 'Resuelto', 'Cancelado')),
    fecha_reporte DATETIME DEFAULT GETDATE(),
    fecha_resolucion DATETIME NULL,
    atendido_por INT NULL,
    CONSTRAINT FK_incidencias_usuario FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario),
    CONSTRAINT FK_incidencias_tarjeta FOREIGN KEY (id_tarjeta_afectada) REFERENCES tarjetas(id_tarjeta),
    CONSTRAINT FK_incidencias_atendido FOREIGN KEY (atendido_por) REFERENCES usuarios(id_usuario)
);
GO

-- 4. Tabla de Bitácora de Accesos Temporales (Auditoría para Guardias)
CREATE TABLE bitacora_accesos_qr (
    id_log INT IDENTITY(1,1) PRIMARY KEY,
    id_incidencia INT NOT NULL,
    id_guardia INT NOT NULL,
    puerta_acceso VARCHAR(50) DEFAULT 'Entrada Principal',
    resultado_validacion VARCHAR(20) NOT NULL CHECK (resultado_validacion IN ('Acceso Permitido', 'QR Expirado', 'QR Inválido')),
    fecha_hora_escaneo DATETIME DEFAULT GETDATE(),
    CONSTRAINT FK_bitacora_incidencia FOREIGN KEY (id_incidencia) REFERENCES incidencias_acceso(id_incidencia),
    CONSTRAINT FK_bitacora_guardia FOREIGN KEY (id_guardia) REFERENCES usuarios(id_usuario)
);
GO

-- ============================================================================
-- INSERCIÓN DE DATOS SIMULADOS (PRUEBAS DE DESARROLLO Y USABILIDAD)
-- ============================================================================

INSERT INTO usuarios (identificador, nombre_completo, correo, password_hash, rol, carrera_o_area) VALUES
('24669001', 'Carlos Mendoza Rivera', 'l24669001@matehuala.tecnm.mx', 'Tec2026*', 'Alumno', 'Ing. en Sistemas Computacionales'),
('24669002', 'Sofía Valdés Hernández', 'l24669002@matehuala.tecnm.mx', 'Tec2026*', 'Alumno', 'Ing. Industrial'),
('24669003', 'Luis Fernando Ortiz', 'l24669003@matehuala.tecnm.mx', 'Tec2026*', 'Alumno', 'Ing. en Gestión Empresarial'),
('SEG-01', 'Roberto Juárez Castro', 'vigilancia01@matehuala.tecnm.mx', 'Tec2026*', 'Guardia', 'Seguridad y Vigilancia'),
('ALM-01', 'Elena Torres Martínez', 'almacen.acceso@matehuala.tecnm.mx', 'Tec2026*', 'Almacen', 'Departamento de Almacén');
GO

INSERT INTO tarjetas (codigo_rfid, id_usuario, estado) VALUES
('RFID-884120A', 1, 'Dañada'),
('RFID-992310B', 2, 'Activa'),
('RFID-771045C', 3, 'En_Reposicion');
GO

INSERT INTO incidencias_acceso (folio, id_usuario, id_tarjeta_afectada, motivo, descripcion_alumno, codigo_qr_temporal, qr_expiracion, estatus_tramite) VALUES
('INC-2026-001', 1, 1, 'Falla de lectura en torniquete', 'El lector marca luz roja desde ayer por la mañana.', 'QR-TEMP-24669001-X9A2', DATEADD(HOUR, 72, GETDATE()), 'Pendiente'),
('INC-2026-002', 3, 3, 'Daño físico del plástico', 'Se quebró una esquina de la credencial y dejó de leer.', 'QR-TEMP-24669003-M4K1', DATEADD(HOUR, 48, GETDATE()), 'En_Proceso');
GO

INSERT INTO bitacora_accesos_qr (id_incidencia, id_guardia, puerta_acceso, resultado_validacion) VALUES
(1, 4, 'Torniquete Entrada Principal', 'Acceso Permitido');
GO