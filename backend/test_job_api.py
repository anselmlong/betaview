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


class AnalyzePersonalityTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        self.originals = (main.probe_video_duration, main.process_job)
        main.probe_video_duration = lambda path: 5.0
        main.process_job = lambda *args: None

    def tearDown(self):
        main.probe_video_duration, main.process_job = self.originals

    def test_personality_is_read_from_the_upload_form(self):
        # The frontend sends personality as a multipart field next to the file
        response = self.client.post(
            "/analyze",
            files={"file": ("climb.mp4", b"video", "video/mp4")},
            data={"personality": "abusive"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["personality"], "abusive")
        self.assertEqual(main.jobs[response.json()["job_id"]].personality, "abusive")

    def test_unknown_personality_is_rejected(self):
        response = self.client.post(
            "/analyze",
            files={"file": ("climb.mp4", b"video", "video/mp4")},
            data={"personality": "rude"},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
