import os
import tempfile
import unittest
from pathlib import Path

_tmp = tempfile.mkdtemp()
os.environ["UPLOAD_DIR"] = os.path.join(_tmp, "uploads")
os.environ["OUTPUT_DIR"] = os.path.join(_tmp, "outputs")

from fastapi.testclient import TestClient  # noqa: E402
import main  # noqa: E402


class DeleteJobTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        self.other = main.OUTPUT_DIR / "6f1c2a3e-0000-4000-8000-000000000000_clean.mp4"
        self.other.write_bytes(b"video")

    def tearDown(self):
        self.other.unlink(missing_ok=True)

    def test_wildcard_job_ids_do_not_delete_other_jobs(self):
        for job_id in ["[0-z]", "6", "%3F"]:
            response = self.client.delete(f"/job/{job_id}")
            self.assertEqual(response.status_code, 404)
            self.assertTrue(self.other.exists())

    def test_valid_job_id_deletes_its_files(self):
        response = self.client.delete("/job/6f1c2a3e-0000-4000-8000-000000000000")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.other.exists())


if __name__ == "__main__":
    unittest.main()
