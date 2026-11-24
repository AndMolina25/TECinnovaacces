import io
import base64
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash
import pyodbc
import qrcode

app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static"
)
app.secret_key = "bitstream_innova_accesotec_secret_key"

# Configuración de conexión a Microsoft SQL Server
SQL_SERVER_CONFIG = {
    "driver": "{ODBC Driver 17 for SQL Server}",
    "server": "localhost",
    "database": "bitstream_accesotec",
    "trusted_connection": "yes"  # Autenticación de Windows
}

def get_db_connection():
    conn_str = (
        f"DRIVER={SQL_SERVER_CONFIG['driver']};"
        f"SERVER={SQL_SERVER_CONFIG['server']};"
        f"DATABASE={SQL_SERVER_CONFIG['database']};"
        f"Trusted_Connection={SQL_SERVER_CONFIG['trusted_connection']};"
        "TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)

def rows_to_dicts(cursor):
    """Convierte las filas devueltas por pyodbc en lista de diccionarios."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def row_to_dict(cursor, row):
    """Convierte una sola fila de pyodbc en diccionario."""
    if row is None:
        return None
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))

def generar_qr_base64(texto_qr: str) -> str:
    """Genera una imagen QR en formato Base64 para incrustar directamente en HTML."""
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(texto_qr)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#003366", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

# ============================================================================
# RUTAS DE AUTENTICACIÓN
# ============================================================================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identificador = request.form.get("identificador", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM usuarios WHERE identificador = ? AND password_hash = ?",
            (identificador, password)
        )
        usuario = row_to_dict(cursor, cursor.fetchone())
        cursor.close()
        conn.close()

        if usuario:
            session["id_usuario"] = usuario["id_usuario"]
            session["identificador"] = usuario["identificador"]
            session["nombre"] = usuario["nombre_completo"]
            session["rol"] = usuario["rol"]

            if usuario["rol"] == "Alumno":
                return redirect(url_for("panel_alumno"))
            elif usuario["rol"] == "Guardia":
                return redirect(url_for("panel_guardia"))
            elif usuario["rol"] == "Almacen":
                return redirect(url_for("panel_almacen"))
        else:
            flash("Credenciales incorrectas. Verifica tu identificador y contraseña.", "danger")

    return render_template("index.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ============================================================================
# MÓDULO ALUMNO: REPORTE DE FALLAS Y PASE QR TEMPORAL
# ============================================================================

@app.route("/alumno", methods=["GET", "POST"])
def panel_alumno():
    if session.get("rol") != "Alumno":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    id_usuario = session["id_usuario"]

    cursor.execute("SELECT TOP 1 * FROM tarjetas WHERE id_usuario = ?", (id_usuario,))
    tarjeta = row_to_dict(cursor, cursor.fetchone())

    if request.method == "POST":
        motivo = request.form.get("motivo")
        descripcion = request.form.get("descripcion", "").strip()

        cursor.execute(
            "SELECT id_incidencia FROM incidencias_acceso WHERE id_usuario = ? AND estatus_tramite IN ('Pendiente', 'En_Proceso')",
            (id_usuario,)
        )
        activa = cursor.fetchone()

        if activa:
            flash("Ya cuentas con un reporte activo en proceso.", "warning")
        elif tarjeta:
            folio = f"INC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
            codigo_qr = f"QR-TEMP-{session['identificador']}-{uuid.uuid4().hex[:5].upper()}"
            expiracion = datetime.now() + timedelta(hours=72)

            cursor.execute(
                """
                INSERT INTO incidencias_acceso 
                (folio, id_usuario, id_tarjeta_afectada, motivo, descripcion_alumno, codigo_qr_temporal, qr_expiracion, estatus_tramite)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Pendiente')
                """,
                (folio, id_usuario, tarjeta["id_tarjeta"], motivo, descripcion, codigo_qr, expiracion)
            )
            cursor.execute(
                "UPDATE tarjetas SET estado = 'Dañada', ultima_actualizacion = GETDATE() WHERE id_tarjeta = ?",
                (tarjeta["id_tarjeta"],)
            )
            conn.commit()
            flash(f"Reporte {folio} registrado. Se ha generado tu Pase QR Temporal válido por 72 horas.", "success")

        cursor.close()
        conn.close()
        return redirect(url_for("panel_alumno"))

    cursor.execute(
        "SELECT * FROM incidencias_acceso WHERE id_usuario = ? ORDER BY fecha_reporte DESC",
        (id_usuario,)
    )
    incidencias = rows_to_dicts(cursor)

    qr_img_base64 = None
    incidencia_activa = None
    for inc in incidencias:
        if inc["estatus_tramite"] in ("Pendiente", "En_Proceso"):
            incidencia_activa = inc
            qr_img_base64 = generar_qr_base64(inc["codigo_qr_temporal"])
            break

    cursor.close()
    conn.close()

    return render_template(
        "panel_alumno.html",
        tarjeta=tarjeta,
        incidencias=incidencias,
        incidencia_activa=incidencia_activa,
        qr_img=qr_img_base64
    )

# ============================================================================
# MÓDULO GUARDIA: VALIDACIÓN DE PASES QR EN TORNIQUETES
# ============================================================================

@app.route("/guardia", methods=["GET", "POST"])
def panel_guardia():
    if session.get("rol") != "Guardia":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    resultado_busqueda = None

    if request.method == "POST":
        codigo_qr = request.form.get("codigo_qr", "").strip()
        cursor.execute(
            """
            SELECT i.*, u.nombre_completo, u.identificador, u.carrera_o_area
            FROM incidencias_acceso i
            JOIN usuarios u ON i.id_usuario = u.id_usuario
            WHERE i.codigo_qr_temporal = ?
            """,
            (codigo_qr,)
        )
        incidencia = row_to_dict(cursor, cursor.fetchone())

        if not incidencia:
            resultado_busqueda = {"valido": False, "mensaje": "Código QR no encontrado en el sistema."}
        else:
            ahora = datetime.now()
            if incidencia["estatus_tramite"] in ("Pendiente", "En_Proceso") and incidencia["qr_expiracion"] > ahora:
                estado_log = "Acceso Permitido"
                resultado_busqueda = {
                    "valido": True,
                    "mensaje": "PASE VIGENTE — AUTORIZAR ACCESO POR TORNIQUETE",
                    "datos": incidencia
                }
            else:
                estado_log = "QR Expirado"
                resultado_busqueda = {
                    "valido": False,
                    "mensaje": "PASE EXPIRADO O TRÁMITE YA CERRADO — REMITIR A ALMACÉN",
                    "datos": incidencia
                }

            cursor.execute(
                """
                INSERT INTO bitacora_accesos_qr (id_incidencia, id_guardia, puerta_acceso, resultado_validacion)
                VALUES (?, ?, 'Torniquete Entrada Principal', ?)
                """,
                (incidencia["id_incidencia"], session["id_usuario"], estado_log)
            )
            conn.commit()

    cursor.execute(
        """
        SELECT TOP 10 b.*, i.folio, u.nombre_completo, u.identificador
        FROM bitacora_accesos_qr b
        JOIN incidencias_acceso i ON b.id_incidencia = i.id_incidencia
        JOIN usuarios u ON i.id_usuario = u.id_usuario
        ORDER BY b.fecha_hora_escaneo DESC
        """
    )
    bitacora = rows_to_dicts(cursor)

    cursor.close()
    conn.close()

    return render_template("panel_guardia.html", resultado=resultado_busqueda, bitacora=bitacora)

# ============================================================================
# MÓDULO ALMACÉN: GESTIÓN Y REPOSICIÓN DE TARJETAS
# ============================================================================

@app.route("/almacen", methods=["GET", "POST"])
def panel_almacen():
    if session.get("rol") != "Almacen":
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        id_incidencia = request.form.get("id_incidencia")
        nuevo_estatus = request.form.get("nuevo_estatus")
        nuevo_rfid = request.form.get("nuevo_rfid", "").strip()

        cursor.execute("SELECT id_tarjeta_afectada FROM incidencias_acceso WHERE id_incidencia = ?", (id_incidencia,))
        inc = row_to_dict(cursor, cursor.fetchone())

        if inc:
            if nuevo_estatus == "En_Proceso":
                cursor.execute(
                    "UPDATE incidencias_acceso SET estatus_tramite = 'En_Proceso', atendido_por = ? WHERE id_incidencia = ?",
                    (session["id_usuario"], id_incidencia)
                )
                cursor.execute(
                    "UPDATE tarjetas SET estado = 'En_Reposicion', ultima_actualizacion = GETDATE() WHERE id_tarjeta = ?",
                    (inc["id_tarjeta_afectada"],)
                )
                flash("Incidencia marcada En Proceso (reposición/reactivación en curso).", "info")

            elif nuevo_estatus == "Resuelto":
                cursor.execute(
                    """
                    UPDATE incidencias_acceso 
                    SET estatus_tramite = 'Resuelto', fecha_resolucion = GETDATE(), atendido_por = ? 
                    WHERE id_incidencia = ?
                    """,
                    (session["id_usuario"], id_incidencia)
                )
                if nuevo_rfid:
                    cursor.execute(
                        "UPDATE tarjetas SET codigo_rfid = ?, estado = 'Activa', ultima_actualizacion = GETDATE() WHERE id_tarjeta = ?",
                        (nuevo_rfid, inc["id_tarjeta_afectada"])
                    )
                else:
                    cursor.execute(
                        "UPDATE tarjetas SET estado = 'Activa', ultima_actualizacion = GETDATE() WHERE id_tarjeta = ?",
                        (inc["id_tarjeta_afectada"],)
                    )
                flash("Trámite resuelto. Tarjeta reactivada y Pase QR temporal desactivado.", "success")

            conn.commit()

        cursor.close()
        conn.close()
        return redirect(url_for("panel_almacen"))

    cursor.execute(
        """
        SELECT i.*, u.identificador, u.nombre_completo, u.carrera_o_area, t.codigo_rfid, t.estado AS estado_tarjeta
        FROM incidencias_acceso i
        JOIN usuarios u ON i.id_usuario = u.id_usuario
        JOIN tarjetas t ON i.id_tarjeta_afectada = t.id_tarjeta
        ORDER BY 
            CASE i.estatus_tramite 
                WHEN 'Pendiente' THEN 1 
                WHEN 'En_Proceso' THEN 2 
                WHEN 'Resuelto' THEN 3 
                ELSE 4 
            END,
            i.fecha_reporte DESC
        """
    )
    todas_incidencias = rows_to_dicts(cursor)

    cursor.close()
    conn.close()

    return render_template("panel_almacen.html", incidencias=todas_incidencias)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5000)