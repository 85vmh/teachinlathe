import json


class Fixture:
    def __init__(self, fixture_index, description, max_rpm, z_minus_limit, image_url=None, diameter=None, units=None):
        self.fixture_index = fixture_index
        self.image_url = image_url
        self.description = description
        self.diameter = diameter
        self.units = units
        self.max_rpm = max_rpm
        self.z_minus_limit = z_minus_limit

    def __repr__(self):
        return f"Fixture({self.fixture_index}, '{self.description}', {self.diameter}, {self.units}, {self.max_rpm}, {self.z_minus_limit})"


class LatheFixtures:

    def __init__(self, file_path):
        self.file_path = file_path
        self.data = self._load_json()

    def _load_json(self):
        with open(self.file_path, 'r') as file:
            return json.load(file)

    def _save_json(self):
        with open(self.file_path, 'w') as file:
            json.dump(self.data, file, indent=4)

    def getFixtures(self):
        return [
            Fixture(
                f.get('fixture_index'),
                f.get('description'),
                f.get('max_rpm'),
                f.get('z_minus_limit'),
                f.get('image_url', None),  # Use .get with default of None
                f.get('diameter', None),  # Use .get with default of None
                f.get('units', None)  # Use .get with default of None
            )
            for f in self.data['fixtures']
        ]

    def getCurrentIndex(self):
        return self.data['current_fixture_index']

    def reloadFixtures(self):
        self._load_json()
        return self.reloadFixtures()

    def reloadCurrentIndex(self):
        self._load_json()
        return self.getCurrentIndex()

    def updateCurrentFixtureIndex(self, new_index):
        print("new_index: ", new_index)
        self.data['current_fixture_index'] = new_index
        self._save_json()

    def updateZMinusLimit(self, fixture_index, new_limit):
        for fixture in self.data['fixtures']:
            if fixture['fixture_index'] == fixture_index:
                fixture['z_minus_limit'] = new_limit
                self._save_json()
                break
