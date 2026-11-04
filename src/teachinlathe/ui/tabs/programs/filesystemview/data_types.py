from dataclasses import dataclass
from enum import Enum


class LocationType(Enum):
    GENERATED = "generated"
    USB_STICK = "usb_stick"
    SYNCTHING = "syncthing"
    HOME = "home"
    MOUNTED_MEDIA = "mounted_media"


@dataclass
class FileSystemEntry:
    name: str
    relative_path: str
    absolute_path: str
    is_dir: bool
    is_up: bool
    size_bytes: int          # bytes for files, 0 for directories
    item_count: int          # direct child count (dirs + .ngc files) for directories, 0 for files
    modified_timestamp: float  # Unix epoch


@dataclass
class FileSystemLocation:
    name: str
    root_path: str
    location_type: LocationType