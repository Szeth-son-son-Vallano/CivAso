"""
Clinic Database Manager (Regazo de Amor)
A centralized and continuous Pandas-based data management engine for:
- Patients (Pacientes): ID, Name, Surname, Age, Number of Visits
- Specialists (Especialistas): ID, Name, Surname, Hours where they can work
- Sessions (Sesiones): ID, Date, Hour, Specialist, Patient, Status
- Available Time (Tiempo Disponible): Hours without a session with an available specialist

Automatically loads from input CSV files, validates actions, updates dataframes in memory,
and continuously writes updated state to output CSV files.
"""

import os
import re
from datetime import datetime, date, timedelta
from typing import List, Optional, Union
import pandas as pd


class ClinicDatabase:
    def __init__(
        self,
        input_dir: str = "data/input",
        output_dir: str = "data/output",
        auto_save: bool = True,
        base_path: Optional[str] = None
    ):
        """
        Initializes the centralized Clinic Database.
        
        :param input_dir: Relative or absolute directory containing initial CSV archives.
        :param output_dir: Relative or absolute directory where updated CSVs are continuously saved.
        :param auto_save: Whether to automatically persist changes to output CSVs after every mutation.
        :param base_path: Base directory for resolving relative paths (defaults to current working directory).
        """
        self.base_path = base_path or os.path.dirname(os.path.abspath(__file__))
        self.input_dir = os.path.join(self.base_path, input_dir) if not os.path.isabs(input_dir) else input_dir
        self.output_dir = os.path.join(self.base_path, output_dir) if not os.path.isabs(output_dir) else output_dir
        self.auto_save = auto_save

        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        # Core DataFrames
        self.df_patients: pd.DataFrame = pd.DataFrame()
        self.df_specialists: pd.DataFrame = pd.DataFrame()
        self.df_sessions: pd.DataFrame = pd.DataFrame()
        self.df_disponible_time: pd.DataFrame = pd.DataFrame()

        # Load initial data or initialize empty structures
        self.load_all()

    # ==========================================
    # Initialization & Schema Normalization
    # ==========================================

    def _init_empty_tables(self):
        """Creates empty DataFrames with standard schema."""
        self.df_patients = pd.DataFrame(columns=["id", "nombre", "apellido", "edad", "visitas"])
        self.df_specialists = pd.DataFrame(columns=["id", "nombre", "apellido", "horas_laborales"])
        self.df_sessions = pd.DataFrame(columns=["id", "fecha", "hora", "id_especialista", "id_paciente", "estado"])
        self.df_disponible_time = pd.DataFrame(columns=["fecha", "hora", "id_especialista", "especialista"])

    def load_all(self):
        """Loads data from input CSV files, falling back to existing output CSVs or initializing empty."""
        patients_in = self._find_file(self.input_dir, ["pacientes.csv", "patients.csv"])
        specialists_in = self._find_file(self.input_dir, ["especialistas.csv", "specialists.csv"])
        sessions_in = self._find_file(self.input_dir, ["sesiones.csv", "sessions.csv"])

        self._init_empty_tables()

        if patients_in and os.path.exists(patients_in):
            self.df_patients = pd.read_csv(patients_in)
            self._normalize_patient_columns()
        elif os.path.exists(os.path.join(self.output_dir, "pacientes_actualizados.csv")):
            self.df_patients = pd.read_csv(os.path.join(self.output_dir, "pacientes_actualizados.csv"))
            self._normalize_patient_columns()

        if specialists_in and os.path.exists(specialists_in):
            self.df_specialists = pd.read_csv(specialists_in)
            self._normalize_specialist_columns()
        elif os.path.exists(os.path.join(self.output_dir, "especialistas_actualizados.csv")):
            self.df_specialists = pd.read_csv(os.path.join(self.output_dir, "especialistas_actualizados.csv"))
            self._normalize_specialist_columns()

        if sessions_in and os.path.exists(sessions_in):
            self.df_sessions = pd.read_csv(sessions_in)
            self._normalize_session_columns()
        elif os.path.exists(os.path.join(self.output_dir, "sesiones_actualizadas.csv")):
            self.df_sessions = pd.read_csv(os.path.join(self.output_dir, "sesiones_actualizadas.csv"))
            self._normalize_session_columns()

        # Compute initial available time slots
        self.compute_disponible_time()

        if self.auto_save:
            self.save_all()

    def _find_file(self, folder: str, candidates: List[str]) -> Optional[str]:
        for candidate in candidates:
            p = os.path.join(folder, candidate)
            if os.path.exists(p):
                return p
        return None

    def _normalize_patient_columns(self):
        col_map = {
            "ID": "id",
            "Id": "id",
            "name": "nombre",
            "Name": "nombre",
            "surname": "apellido",
            "Surname": "apellido",
            "last_name": "apellido",
            "age": "edad",
            "Age": "edad",
            "visits": "visitas",
            "Visits": "visitas",
            "number of visits": "visitas",
            "número de asistencia": "visitas"
        }
        self.df_patients = self.df_patients.rename(columns=col_map)
        for col in ["id", "nombre", "apellido", "edad", "visitas"]:
            if col not in self.df_patients.columns:
                self.df_patients[col] = 0 if col in ["id", "edad", "visitas"] else ""
        self.df_patients["id"] = pd.to_numeric(self.df_patients["id"], errors="coerce").fillna(0).astype(int)
        self.df_patients["edad"] = pd.to_numeric(self.df_patients["edad"], errors="coerce").fillna(0).astype(int)
        self.df_patients["visitas"] = pd.to_numeric(self.df_patients["visitas"], errors="coerce").fillna(0).astype(int)

    def _normalize_specialist_columns(self):
        col_map = {
            "ID": "id",
            "Id": "id",
            "name": "nombre",
            "Name": "nombre",
            "surname": "apellido",
            "Surname": "apellido",
            "work_hours": "horas_laborales",
            "Work_Hours": "horas_laborales",
            "hours": "horas_laborales",
            "Hours": "horas_laborales"
        }
        self.df_specialists = self.df_specialists.rename(columns=col_map)
        for col in ["id", "nombre", "apellido", "horas_laborales"]:
            if col not in self.df_specialists.columns:
                self.df_specialists[col] = 0 if col == "id" else ""
        self.df_specialists["id"] = pd.to_numeric(self.df_specialists["id"], errors="coerce").fillna(0).astype(int)

    def _normalize_session_columns(self):
        col_map = {
            "ID": "id",
            "Id": "id",
            "date": "fecha",
            "Date": "fecha",
            "hour": "hora",
            "Hour": "hora",
            "specialist": "id_especialista",
            "Specialist": "id_especialista",
            "specialist_id": "id_especialista",
            "pacient": "id_paciente",
            "Pacient": "id_paciente",
            "patient": "id_paciente",
            "Patient": "id_paciente",
            "patient_id": "id_paciente",
            "status": "estado"
        }
        self.df_sessions = self.df_sessions.rename(columns=col_map)
        if "fecha" not in self.df_sessions.columns:
            self.df_sessions["fecha"] = datetime.now().strftime("%Y-%m-%d")
        if "estado" not in self.df_sessions.columns:
            self.df_sessions["estado"] = "Programada"

        for col in ["id", "fecha", "hora", "id_especialista", "id_paciente", "estado"]:
            if col not in self.df_sessions.columns:
                self.df_sessions[col] = 0 if "id" in col else ""

        self.df_sessions["id"] = pd.to_numeric(self.df_sessions["id"], errors="coerce").fillna(0).astype(int)
        self.df_sessions["id_especialista"] = pd.to_numeric(self.df_sessions["id_especialista"], errors="coerce").fillna(0).astype(int)
        self.df_sessions["id_paciente"] = pd.to_numeric(self.df_sessions["id_paciente"], errors="coerce").fillna(0).astype(int)
        self.df_sessions["hora"] = self.df_sessions["hora"].astype(str).str.strip().apply(self._format_hour)

    # ==========================================
    # Persistence (Continuous CSV sync)
    # ==========================================

    def save_all(self, target_dir: Optional[str] = None):
        """
        Saves all DataFrames to target CSV files.
        """
        dest = target_dir or self.output_dir
        os.makedirs(dest, exist_ok=True)

        patients_path = os.path.join(dest, "pacientes_actualizados.csv")
        specialists_path = os.path.join(dest, "especialistas_actualizados.csv")
        sessions_path = os.path.join(dest, "sesiones_actualizadas.csv")
        disponible_path = os.path.join(dest, "tiempo_disponible.csv")

        self.df_patients.to_csv(patients_path, index=False, encoding="utf-8")
        self.df_specialists.to_csv(specialists_path, index=False, encoding="utf-8")
        self.df_sessions.to_csv(sessions_path, index=False, encoding="utf-8")
        self.df_disponible_time.to_csv(disponible_path, index=False, encoding="utf-8")

        return {
            "pacientes": patients_path,
            "especialistas": specialists_path,
            "sesiones": sessions_path,
            "tiempo_disponible": disponible_path,
        }

    # ==========================================
    # Working Hours & Available Time Engine
    # ==========================================

    @staticmethod
    def _format_hour(hour_str: str) -> str:
        """Formats hour to HH:00 format."""
        hour_str = str(hour_str).strip()
        match = re.match(r"^(\d{1,2})(?::?(\d{2}))?$", hour_str)
        if match:
            h = int(match.group(1))
            return f"{h:02d}:00"
        return hour_str

    @classmethod
    def parse_hours(cls, hours_expr: str) -> List[str]:
        """
        Parses working hours expression into a list of 1-hour slots.
        Supports:
        - Ranges: "09:00-14:00" or "9-14"
        - Comma lists: "09:00, 10:00, 11:00"
        - Mixed combinations: "09:00-12:00, 14:00-17:00"
        """
        slots = set()
        if not hours_expr or pd.isna(hours_expr):
            return []

        parts = str(hours_expr).split(",")
        for part in parts:
            part = part.strip()
            if "-" in part:
                range_match = re.match(r"(\d{1,2})(?::(\d{2}))?\s*-\s*(\d{1,2})(?::(\d{2}))?", part)
                if range_match:
                    start_h = int(range_match.group(1))
                    end_h = int(range_match.group(3))
                    for h in range(start_h, end_h):
                        slots.add(f"{h:02d}:00")
            else:
                formatted = cls._format_hour(part)
                if formatted:
                    slots.add(formatted)

        return sorted(list(slots))

    def compute_disponible_time(self, dates: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Computes the real-time available time slots:
        Hours where a specialist is scheduled to work and currently has NO booked session.
        
        :param dates: Optional list of date strings (YYYY-MM-DD). If None, considers dates
                      from existing sessions plus the current date and next 7 days.
        :return: DataFrame of available slots.
        """
        if dates is None:
            active_dates = set()
            today = date.today()
            for i in range(7):
                active_dates.add((today + timedelta(days=i)).strftime("%Y-%m-%d"))

            if not self.df_sessions.empty and "fecha" in self.df_sessions.columns:
                session_dates = self.df_sessions["fecha"].dropna().astype(str).tolist()
                active_dates.update(session_dates)

            dates = sorted(list(active_dates))

        available_records = []

        # Map active sessions: (fecha, hora, id_especialista)
        active_sessions = set()
        if not self.df_sessions.empty:
            for _, s_row in self.df_sessions.iterrows():
                if str(s_row.get("estado", "")).lower() != "cancelada":
                    s_date = str(s_row["fecha"]).strip()
                    s_hour = str(s_row["hora"]).strip()
                    s_spec = int(s_row["id_especialista"])
                    active_sessions.add((s_date, s_hour, s_spec))

        # Check each specialist's working hours against active sessions
        for _, spec in self.df_specialists.iterrows():
            spec_id = int(spec["id"])
            spec_name = f"{spec['nombre']} {spec['apellido']}".strip()
            work_slots = self.parse_hours(str(spec["horas_laborales"]))

            for d in dates:
                for slot in work_slots:
                    if (d, slot, spec_id) not in active_sessions:
                        available_records.append({
                            "fecha": d,
                            "hora": slot,
                            "id_especialista": spec_id,
                            "especialista": spec_name
                        })

        self.df_disponible_time = pd.DataFrame(
            available_records,
            columns=["fecha", "hora", "id_especialista", "especialista"]
        )
        return self.df_disponible_time

    # ==========================================
    # Patient Management
    # ==========================================

    def add_patient(self, nombre: str, apellido: str, edad: int, visitas: int = 0) -> int:
        """Adds a new patient and persists changes."""
        next_id = 1 if self.df_patients.empty else int(self.df_patients["id"].max()) + 1
        new_row = pd.DataFrame([{
            "id": next_id,
            "nombre": str(nombre).strip(),
            "apellido": str(apellido).strip(),
            "edad": int(edad),
            "visitas": int(visitas)
        }])
        self.df_patients = pd.concat([self.df_patients, new_row], ignore_index=True)

        if self.auto_save:
            self.save_all()
        return next_id

    def update_patient_visits(self, patient_id: int, delta: int = 1) -> Optional[int]:
        """Adjusts the visit count for a patient by delta (e.g. +1 or -1)."""
        idx = self.df_patients.index[self.df_patients["id"] == patient_id]
        if len(idx) == 0:
            return None
        current = int(self.df_patients.loc[idx[0], "visitas"])
        updated = max(0, current + delta)
        self.df_patients.loc[idx[0], "visitas"] = updated

        if self.auto_save:
            self.save_all()
        return updated

    # ==========================================
    # Specialist Management
    # ==========================================

    def add_specialist(self, nombre: str, apellido: str, horas_laborales: str) -> int:
        """Adds a new specialist with their working hours."""
        next_id = 1 if self.df_specialists.empty else int(self.df_specialists["id"].max()) + 1
        new_row = pd.DataFrame([{
            "id": next_id,
            "nombre": str(nombre).strip(),
            "apellido": str(apellido).strip(),
            "horas_laborales": str(horas_laborales).strip()
        }])
        self.df_specialists = pd.concat([self.df_specialists, new_row], ignore_index=True)
        self.compute_disponible_time()

        if self.auto_save:
            self.save_all()
        return next_id

    def update_specialist_hours(self, specialist_id: int, new_hours: str) -> bool:
        """Updates working hours for a specialist."""
        idx = self.df_specialists.index[self.df_specialists["id"] == specialist_id]
        if len(idx) == 0:
            return False
        self.df_specialists.loc[idx[0], "horas_laborales"] = str(new_hours).strip()
        self.compute_disponible_time()

        if self.auto_save:
            self.save_all()
        return True

    # ==========================================
    # Session Booking & Management
    # ==========================================

    def is_slot_available(self, specialist_id: int, fecha: str, hora: str) -> bool:
        """Checks if a specialist is available at the specified date and hour."""
        formatted_hour = self._format_hour(hora)
        self.compute_disponible_time([fecha])
        match = self.df_disponible_time[
            (self.df_disponible_time["id_especialista"] == specialist_id) &
            (self.df_disponible_time["fecha"] == fecha) &
            (self.df_disponible_time["hora"] == formatted_hour)
        ]
        return not match.empty

    def book_session(
        self,
        id_paciente: int,
        id_especialista: int,
        fecha: str,
        hora: str
    ) -> dict:
        """
        Centralized booking operation:
        1. Validates patient existence.
        2. Validates specialist existence and availability.
        3. Records the session.
        4. Continuously updates the patient's visit count (+1).
        5. Recomputes available time slots.
        6. Automatically saves updated dataframes to output CSV.
        """
        # Validate patient
        p_match = self.df_patients[self.df_patients["id"] == id_paciente]
        if p_match.empty:
            return {"success": False, "error": f"Paciente con ID {id_paciente} no encontrado."}

        # Validate specialist
        s_match = self.df_specialists[self.df_specialists["id"] == id_especialista]
        if s_match.empty:
            return {"success": False, "error": f"Especialista con ID {id_especialista} no encontrado."}

        formatted_hour = self._format_hour(hora)

        # Check availability
        if not self.is_slot_available(id_especialista, fecha, formatted_hour):
            return {
                "success": False,
                "error": f"El especialista {id_especialista} no tiene disponibilidad el {fecha} a las {formatted_hour}."
            }

        # Create session
        next_session_id = 1 if self.df_sessions.empty else int(self.df_sessions["id"].max()) + 1
        new_session = pd.DataFrame([{
            "id": next_session_id,
            "fecha": fecha,
            "hora": formatted_hour,
            "id_especialista": int(id_especialista),
            "id_paciente": int(id_paciente),
            "estado": "Programada"
        }])
        self.df_sessions = pd.concat([self.df_sessions, new_session], ignore_index=True)

        # Continuously increment patient visits
        updated_visits = self.update_patient_visits(id_paciente, delta=1)

        # Recompute available time
        self.compute_disponible_time()

        if self.auto_save:
            self.save_all()

        return {
            "success": True,
            "session_id": next_session_id,
            "fecha": fecha,
            "hora": formatted_hour,
            "id_paciente": id_paciente,
            "id_especialista": id_especialista,
            "visitas_actualizadas": updated_visits
        }

    def cancel_session(self, session_id: int, revert_visit: bool = True) -> dict:
        """
        Cancels an existing session:
        - Marks status as 'Cancelada'.
        - Optionally reverts patient visit counter (-1).
        - Returns slot to available time.
        - Persists to output CSVs.
        """
        idx = self.df_sessions.index[self.df_sessions["id"] == session_id]
        if len(idx) == 0:
            return {"success": False, "error": f"Sesión con ID {session_id} no encontrada."}

        current_status = self.df_sessions.loc[idx[0], "estado"]
        if current_status == "Cancelada":
            return {"success": False, "error": f"La sesión {session_id} ya estaba cancelada."}

        self.df_sessions.loc[idx[0], "estado"] = "Cancelada"
        patient_id = int(self.df_sessions.loc[idx[0], "id_paciente"])

        if revert_visit:
            self.update_patient_visits(patient_id, delta=-1)

        # Recompute available time
        self.compute_disponible_time()

        if self.auto_save:
            self.save_all()

        return {
            "success": True,
            "message": f"Sesión {session_id} cancelada exitosamente.",
            "session_id": session_id
        }

    # ==========================================
    # Summary & Reporting
    # ==========================================

    def get_summary(self) -> dict:
        """Returns statistics of all tables in the centralized database."""
        return {
            "total_pacientes": len(self.df_patients),
            "total_especialistas": len(self.df_specialists),
            "total_sesiones": len(self.df_sessions),
            "sesiones_activas": len(self.df_sessions[self.df_sessions["estado"] != "Cancelada"]) if not self.df_sessions.empty else 0,
            "horarios_disponibles": len(self.df_disponible_time)
        }

    def print_all(self):
        """Pretty prints all DataFrames."""
        print("\n" + "=" * 50)
        print(" CENTRAL CLINIC DATABASE (Regazo de Amor)")
        print("=" * 50)
        
        print("\n--- PACIENTES (Patients) ---")
        print(self.df_patients.to_string(index=False) if not self.df_patients.empty else "(Vacío)")
        
        print("\n--- ESPECIALISTAS (Specialists) ---")
        print(self.df_specialists.to_string(index=False) if not self.df_specialists.empty else "(Vacío)")
        
        print("\n--- SESIONES (Sessions) ---")
        print(self.df_sessions.to_string(index=False) if not self.df_sessions.empty else "(Vacío)")
        
        print("\n--- TIEMPO DISPONIBLE (Available Time) [Primeros 10 registros] ---")
        print(self.df_disponible_time.head(10).to_string(index=False) if not self.df_disponible_time.empty else "(Vacío)")
        print("=" * 50 + "\n")


# ==========================================
# Interactive CLI Loop
# ==========================================

def run_interactive_menu():
    db = ClinicDatabase()
    while True:
        print("\n==========================================")
        print(" REGISTRO CLÍNICO - MENÚ CONTINUO")
        print("==========================================")
        print("1. Ver todas las tablas (DataFrames)")
        print("2. Registrar nuevo paciente")
        print("3. Registrar nuevo especialista")
        print("4. Agendar sesión (actualiza visitas y disponibilidad)")
        print("5. Cancelar sesión")
        print("6. Ver tiempo disponible para una fecha")
        print("7. Recargar datos desde CSV de entrada")
        print("8. Guardar explícitamente en CSV de salida")
        print("9. Salir")
        print("------------------------------------------")
        choice = input("Seleccione una opción (1-9): ").strip()

        if choice == "1":
            db.print_all()
        elif choice == "2":
            nombre = input("Nombre del paciente: ").strip()
            apellido = input("Apellido del paciente: ").strip()
            try:
                edad = int(input("Edad: ").strip())
                visitas = int(input("Número inicial de visitas [0]: ").strip() or "0")
                pid = db.add_patient(nombre, apellido, edad, visitas)
                print(f"Paciente registrado con ID: {pid}")
            except ValueError:
                print("Error: Edad o visitas inválidas.")
        elif choice == "3":
            nombre = input("Nombre del especialista: ").strip()
            apellido = input("Apellido del especialista: ").strip()
            horas = input("Horario laboral (ej. '09:00-14:00' o '09:00, 10:00'): ").strip()
            sid = db.add_specialist(nombre, apellido, horas)
            print(f"Especialista registrado con ID: {sid}")
        elif choice == "4":
            print("\nHorarios disponibles próximos:")
            print(db.df_disponible_time.head(8).to_string(index=False))
            try:
                id_paciente = int(input("\nID del paciente: ").strip())
                id_especialista = int(input("ID del especialista: ").strip())
                fecha = input("Fecha (YYYY-MM-DD) [hoy]: ").strip() or date.today().strftime("%Y-%m-%d")
                hora = input("Hora (HH:00): ").strip()
                res = db.book_session(id_paciente, id_especialista, fecha, hora)
                if res["success"]:
                    print(f"Sesión #{res['session_id']} agendada. Visitas del paciente ahora: {res['visitas_actualizadas']}")
                else:
                    print(f"Error: {res['error']}")
            except ValueError:
                print("Error: Datos numéricos inválidos.")
        elif choice == "5":
            try:
                session_id = int(input("ID de la sesión a cancelar: ").strip())
                res = db.cancel_session(session_id)
                if res["success"]:
                    print(res["message"])
                else:
                    print(f"Error: {res['error']}")
            except ValueError:
                print("Error: ID inválido.")
        elif choice == "6":
            fecha = input("Fecha a consultar (YYYY-MM-DD) [hoy]: ").strip() or date.today().strftime("%Y-%m-%d")
            db.compute_disponible_time([fecha])
            disp = db.df_disponible_time[db.df_disponible_time["fecha"] == fecha]
            print(f"\nTiempo disponible el {fecha}:")
            print(disp.to_string(index=False) if not disp.empty else "No hay horarios disponibles.")
        elif choice == "7":
            db.load_all()
            print("Datos recargados desde archivos CSV de entrada.")
        elif choice == "8":
            paths = db.save_all()
            print("Datos guardados en:")
            for k, v in paths.items():
                print(f" - {k}: {v}")
        elif choice == "9":
            print("¡Hasta luego!")
            break
        else:
            print("Opción no válida. Intente nuevamente.")


if __name__ == "__main__":
    import sys
    if "--interactive" in sys.argv:
        run_interactive_menu()
    else:
        # Default self-demonstration run
        print("Iniciando base de datos centralizada de Regazo de Amor...")
        db = ClinicDatabase()
        db.print_all()
        print("\nPara iniciar el menú continuo e interactivo, ejecute:")
        print("  python database_manager.py --interactive")
