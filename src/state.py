class MeasurementState:
    def __init__(self):
        self.is_measuring = False
        self.is_recording = False
        self.current_data = {}
        self.measurement_thread = None
        self.data_buffer = []
        self.excel_filename = "pt100_measurements.xlsx"


    def add_measurement(self, data):
        self.data_buffer.append(data)

    def get_last_measurement(self):
        return self.data_buffer[-1] if self.data_buffer else None
