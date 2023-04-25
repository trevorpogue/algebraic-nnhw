from enum import IntEnum
# exports:
from .device_controller import DeviceController


class pcie_pkg(IntEnum):
    """Python equivalent for instruc_pkg in design sv code."""
    FIFO_WIDTH = 32
