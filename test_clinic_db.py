import unittest
import os
import shutil
import tempfile
import pandas as pd
from database_manager import ClinicDatabase

class TestClinicDatabase(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.input_dir = os.path.join(self.test_dir, "input")
        self.output_dir = os.path.join(self.test_dir, "output")
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        # Create test CSVs
        pd.DataFrame([
            {"id": 1, "nombre": "Juan", "apellido": "Pérez", "edad": 25, "visitas": 2}
        ]).to_csv(os.path.join(self.input_dir, "pacientes.csv"), index=False)

        pd.DataFrame([
            {"id": 1, "nombre": "Dr. Mario", "apellido": "Gómez", "horas_laborales": "09:00-12:00"}
        ]).to_csv(os.path.join(self.input_dir, "especialistas.csv"), index=False)

        pd.DataFrame([
            {"id": 1, "fecha": "2026-10-01", "hora": "09:00", "id_especialista": 1, "id_paciente": 1, "estado": "Programada"}
        ]).to_csv(os.path.join(self.input_dir, "sesiones.csv"), index=False)

        self.db = ClinicDatabase(
            input_dir=self.input_dir,
            output_dir=self.output_dir,
            auto_save=True,
            base_path=self.test_dir
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_disponible_time_calculation(self):
        """Slots 10:00 and 11:00 should be available, while 09:00 is booked."""
        disp = self.db.compute_disponible_time(["2026-10-01"])
        available_hours = disp[disp["fecha"] == "2026-10-01"]["hora"].tolist()
        self.assertNotIn("09:00", available_hours)
        self.assertIn("10:00", available_hours)
        self.assertIn("11:00", available_hours)

    def test_book_session_and_increment_visits(self):
        """Booking a session should succeed, increment patient visits, and remove slot from available time."""
        res = self.db.book_session(
            id_paciente=1,
            id_especialista=1,
            fecha="2026-10-01",
            hora="10:00"
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["visitas_actualizadas"], 3)

        # Check in DataFrame
        patient_row = self.db.df_patients[self.db.df_patients["id"] == 1].iloc[0]
        self.assertEqual(patient_row["visitas"], 3)

        # Check availability
        disp = self.db.compute_disponible_time(["2026-10-01"])
        available_hours = disp[disp["fecha"] == "2026-10-01"]["hora"].tolist()
        self.assertNotIn("10:00", available_hours)
        self.assertIn("11:00", available_hours)

    def test_double_booking_prevention(self):
        """Cannot book the same slot twice."""
        res1 = self.db.book_session(1, 1, "2026-10-01", "11:00")
        self.assertTrue(res1["success"])
        res2 = self.db.book_session(1, 1, "2026-10-01", "11:00")
        self.assertFalse(res2["success"])
        self.assertIn("no tiene disponibilidad", res2["error"])

    def test_cancel_session(self):
        """Canceling session reverts visit count and frees the slot."""
        # Session 1 is at 09:00
        res = self.db.cancel_session(1, revert_visit=True)
        self.assertTrue(res["success"])

        # Visits should have reverted from 2 to 1
        patient_row = self.db.df_patients[self.db.df_patients["id"] == 1].iloc[0]
        self.assertEqual(patient_row["visitas"], 1)

        # Slot 09:00 should now be available again
        disp = self.db.compute_disponible_time(["2026-10-01"])
        available_hours = disp[disp["fecha"] == "2026-10-01"]["hora"].tolist()
        self.assertIn("09:00", available_hours)

    def test_csv_output_persistence(self):
        """Check that output CSVs exist and contain updated data."""
        self.db.add_patient("Carlos", "Santana", 60, 10)
        p_csv = os.path.join(self.output_dir, "pacientes_actualizados.csv")
        self.assertTrue(os.path.exists(p_csv))
        df_disk = pd.read_csv(p_csv)
        self.assertIn("Carlos", df_disk["nombre"].values)

if __name__ == "__main__":
    unittest.main()
