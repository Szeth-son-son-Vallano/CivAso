"""
Regazo de Amor - Base de Datos Centralizada con Pandas
Este script centraliza y mantiene actualizadas las tablas de:
- Pacientes (ID, Nombre, Apellido, Edad, Número de visitas)
- Especialistas (ID, Nombre, Apellido, Horas donde pueden trabajar)
- Sesiones (Hora, Especialista, Paciente)
- Tiempo disponible (Horas sin sesión con un especialista disponible)

Lee datos desde los CSV de entrada (data/input/) y actualiza continuamente los CSV de salida (data/output/).
"""

from database_manager import ClinicDatabase

def main():
    print("=" * 65)
    print("SISTEMA DE BASE DE DATOS CENTRALIZADA - REGAZO DE AMOR")
    print("=" * 65)

    # 1. Inicializar base de datos centralizada (Carga automática desde CSV)
    db = ClinicDatabase(input_dir="data/input", output_dir="data/output", auto_save=True)

    # 2. Mostrar estado inicial cargado desde CSV
    print("\n[ESTADO INICIAL CARGADO]")
    db.print_all()

    # 3. Demostración de modificaciones continuas y sincronizadas:
    print("\n--- Ejecutando operaciones de ejemplo ---")

    # A. Registrar un nuevo paciente
    nuevo_id = db.add_patient(nombre="Lucía", apellido="Valenzuela", edad=31, visitas=0)
    print(f"-> Nuevo paciente registrado: Lucía Valenzuela (ID: {nuevo_id})")

    # B. Consultar slots disponibles para mañana
    fecha_agenda = "2026-09-17"
    disponibles = db.compute_disponible_time([fecha_agenda])
    print(f"\nSlots disponibles el {fecha_agenda} antes de agendar:")
    print(disponibles.head(6).to_string(index=False))

    # C. Agendar una sesión para Lucía con Dr. Carlos Ramírez a las 10:00
    print(f"\n-> Agendando sesión: Paciente {nuevo_id} con Especialista 1 a las 10:00 ({fecha_agenda})...")
    res = db.book_session(
        id_paciente=nuevo_id,
        id_especialista=1,
        fecha=fecha_agenda,
        hora="10:00"
    )

    if res["success"]:
        print(f"  [ÉXITO] Sesión #{res['session_id']} confirmada!")
        print(f"  [VISITAS ACTUALIZADAS] El paciente {nuevo_id} ahora tiene {res['visitas_actualizadas']} visita(s).")
    else:
        print(f"  [ERROR] {res['error']}")

    # D. Intentar agendar en el mismo horario (debe ser rechazado por falta de disponibilidad)
    print("\n-> Intentando agendar conflicto en el mismo horario (10:00 con Especialista 1)...")
    conflicto = db.book_session(id_paciente=1, id_especialista=1, fecha=fecha_agenda, hora="10:00")
    if not conflicto["success"]:
        print(f"  [VALIDACIÓN CORRECTA] Se previno el choque de horario: {conflicto['error']}")

    # 4. Mostrar estado final sincronizado
    print("\n[ESTADO FINAL TRAS MODIFICACIONES (Guardado automático en data/output/)]")
    db.print_all()

    # 5. Resumen de archivos actualizados
    print("\nArchivos CSV actualizados en 'data/output/':")
    for nombre, ruta in db.save_all().items():
        print(f" - {nombre}: {ruta}")

    print("\nNota: Para ejecutar el menú interactivo continuo por consola, ejecute:")
    print("  python database_manager.py --interactive")


if __name__ == "__main__":
    main()
