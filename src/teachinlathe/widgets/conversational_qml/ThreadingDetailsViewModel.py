from PyQt5.QtCore import QObject, pyqtSlot


class ThreadingDetailsViewModel(QObject):
    EXTERNAL_THREAD_HEIGHT_FACTOR = 0.61344
    INTERNAL_THREAD_HEIGHT_FACTOR = 0.54127

    @pyqtSlot(str, "QVariant", "QVariant", "QVariant", result="QVariantMap")
    def calculateThreadDiameter(self, location, pitch, major_diameter, minor_diameter):
        try:
            pitch_value = float(pitch)
        except (TypeError, ValueError):
            return {"valid": False}

        location_value = str(location or "OD").upper()
        try:
            major_value = float(major_diameter)
        except (TypeError, ValueError):
            major_value = 0.0
        try:
            minor_value = float(minor_diameter)
        except (TypeError, ValueError):
            minor_value = 0.0

        if location_value == "ID":
            major_value = minor_value + self.INTERNAL_THREAD_HEIGHT_FACTOR * pitch_value * 2.0
            calculated_diameter = major_value
        else:
            minor_value = major_value - self.EXTERNAL_THREAD_HEIGHT_FACTOR * pitch_value * 2.0
            calculated_diameter = minor_value

        return {
            "valid": True,
            "majorDiameter": round(major_value, 3),
            "minorDiameter": round(minor_value, 3),
            "calculatedDiameter": round(calculated_diameter, 3),
        }
