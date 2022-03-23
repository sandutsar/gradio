"""Contains tests for networking.py and app.py"""

import os
import unittest
import unittest.mock as mock

from fastapi.testclient import TestClient

from gradio import Interface, queueing, reset_all

os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"


class TestRoutes(unittest.TestCase):
    def setUp(self) -> None:
        self.io = Interface(lambda x: x, "text", "text")
        self.app, _, _ = self.io.launch(prevent_thread_lock=True)
        self.client = TestClient(self.app)

    def test_get_main_route(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_get_api_route(self):
        response = self.client.get("/api/")
        self.assertEqual(response.status_code, 200)

    def test_static_files_served_safely(self):
        # Make sure things outside the static folder are not accessible
        response = self.client.get(r"/static/..%2findex.html")
        self.assertEqual(response.status_code, 404)
        response = self.client.get(r"/static/..%2f..%2fapi_docs.html")
        self.assertEqual(response.status_code, 404)

    def test_get_config_route(self):
        response = self.client.get("/config/")
        self.assertEqual(response.status_code, 200)

    def test_predict_route(self):
        response = self.client.post("/api/predict/", json={"data": ["test"]})
        self.assertEqual(response.status_code, 200)
        output = dict(response.json())
        self.assertEqual(output["data"], ["test"])
        self.assertTrue("durations" in output)
        self.assertTrue("avg_durations" in output)

    def test_state(self):
        def predict(input, history=""):
            history += input
            return history, history

        io = Interface(predict, ["textbox", "state"], ["textbox", "state"])
        app, _, _ = io.launch(prevent_thread_lock=True)
        client = TestClient(app)
        response = client.post("/api/predict/", json={"data": ["test", None]})
        output = dict(response.json())
        print("output", output)
        self.assertEqual(output["data"], ["test", None])
        response = client.post("/api/predict/", json={"data": ["test", None]})
        output = dict(response.json())
        self.assertEqual(output["data"], ["testtest", None])

    def test_queue_push_route(self):
        queueing.push = mock.MagicMock(return_value=(None, None))
        response = self.client.post(
            "/api/queue/push/", json={"data": "test", "action": "test"}
        )
        self.assertEqual(response.status_code, 200)

    def test_queue_push_route_2(self):
        queueing.get_status = mock.MagicMock(return_value=(None, None))
        response = self.client.post("/api/queue/status/", json={"hash": "test"})
        self.assertEqual(response.status_code, 200)

    def tearDown(self) -> None:
        self.io.close()
        reset_all()


class TestAuthenticatedRoutes(unittest.TestCase):
    def setUp(self) -> None:
        self.io = Interface(lambda x: x, "text", "text")
        self.app, _, _ = self.io.launch(
            auth=("test", "correct_password"), prevent_thread_lock=True
        )
        self.client = TestClient(self.app)

    def test_post_login(self):
        response = self.client.post(
            "/login", data=dict(username="test", password="correct_password")
        )
        self.assertEqual(response.status_code, 302)
        response = self.client.post(
            "/login", data=dict(username="test", password="incorrect_password")
        )
        self.assertEqual(response.status_code, 400)

    def tearDown(self) -> None:
        self.io.close()
        reset_all()


if __name__ == "__main__":
    unittest.main()
