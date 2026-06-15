import sys
import os
import unittest
import time
from datetime import datetime
import pytz

# Add parent directory to path to import server
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app, bandwidth_collection, _ipwan_bandwidth_cache, _data_cache, _get_ipwan_totals
from fastapi.testclient import TestClient

VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

class TestIPWANBandwidth(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Clear cache and reset test DB
        _ipwan_bandwidth_cache.clear()
        _data_cache.clear()
        # Clean test records for this IP WAN today
        self.ipwan = "9.9.9.9"
        self.today_str = datetime.now(VIETNAM_TZ).strftime("%d-%m-%Y")
        bandwidth_collection.delete_many({"ipwan": self.ipwan})

    def tearDown(self):
        # Clean up
        bandwidth_collection.delete_many({"ipwan": self.ipwan})

    def test_peak_and_history_updates(self):
        # 1. Send first station data
        payload1 = {
            "name": "Station1",
            "ip": "192.168.1.10",
            "ipwan": self.ipwan,
            "statusapp": 1,
            "sender_mbps": 10.0,
            "receiver_mbps": 20.0
        }
        response = self.client.post("/", json=payload1)
        self.assertEqual(response.status_code, 200)

        # Allow async task to complete
        time.sleep(1)

        # Check DB
        doc = bandwidth_collection.find_one({"_id": f"{self.ipwan}_{self.today_str}"})
        self.assertIsNotNone(doc)
        self.assertEqual(doc["sender_max"], 10.0)
        self.assertEqual(doc["receiver_max"], 20.0)
        self.assertEqual(doc["sender_min"], 10.0)
        self.assertEqual(doc["receiver_min"], 20.0)
        self.assertEqual(len(doc["history"]), 1)
        self.assertEqual(doc["history"][0]["sender"], 10.0)
        self.assertEqual(doc["history"][0]["receiver"], 20.0)

        # 2. Send second station data (shares the same IP WAN)
        payload2 = {
            "name": "Station2",
            "ip": "192.168.1.11",
            "ipwan": self.ipwan,
            "statusapp": 1,
            "sender_mbps": 5.0,
            "receiver_mbps": 15.0
        }
        response = self.client.post("/", json=payload2)
        self.assertEqual(response.status_code, 200)
        time.sleep(1)

        # Totals should now be: sender = 10 + 5 = 15, receiver = 20 + 15 = 35
        # Since both are new peaks, it should immediately write to DB
        doc = bandwidth_collection.find_one({"_id": f"{self.ipwan}_{self.today_str}"})
        self.assertEqual(doc["sender_max"], 15.0)
        self.assertEqual(doc["receiver_max"], 35.0)
        self.assertEqual(doc["sender_min"], 10.0)  # Min stays at 10.0 (previous state was 10.0, current is 15.0, so min is not lower)
        self.assertEqual(doc["receiver_min"], 20.0)  # Min stays at 20.0
        self.assertEqual(len(doc["history"]), 2)
        self.assertEqual(doc["history"][1]["sender"], 15.0)
        self.assertEqual(doc["history"][1]["receiver"], 35.0)

        # 3. Send lower bandwidth from Station 1
        payload1_lower = {
            "name": "Station1",
            "ip": "192.168.1.10",
            "ipwan": self.ipwan,
            "statusapp": 1,
            "sender_mbps": 2.0,
            "receiver_mbps": 5.0
        }
        response = self.client.post("/", json=payload1_lower)
        self.assertEqual(response.status_code, 200)
        time.sleep(1)

        # Totals should now be: sender = 2 + 5 = 7, receiver = 5 + 15 = 20
        # This is lower than the peak (sender peak 15, receiver peak 35),
        # so it should NOT immediately write to MongoDB.
        # History length remains 2.
        doc = bandwidth_collection.find_one({"_id": f"{self.ipwan}_{self.today_str}"})
        self.assertEqual(doc["sender_max"], 15.0)
        self.assertEqual(doc["receiver_max"], 35.0)
        self.assertEqual(len(doc["history"]), 2)

if __name__ == "__main__":
    unittest.main()
