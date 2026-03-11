from locust import HttpUser, task, between

class TripUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def get_root(self):
        self.client.get("/")

    @task
    def get_report(self):
        # Query for a specific region
        self.client.get("/report/weekly_average?region=Prague")

    @task
    def get_spatial_report(self):
        # Query with a bounding box
        self.client.get("/report/weekly_average?min_lat=40.0&min_lon=5.0&max_lat=55.0&max_lon=20.0")
