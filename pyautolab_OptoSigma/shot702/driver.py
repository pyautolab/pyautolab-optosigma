from __future__ import annotations

import re
from math import floor
from typing import Any

from serial.serialutil import EIGHTBITS, PARITY_NONE, STOPBITS_ONE
from typing_extensions import Literal

from pyautolab_OptoSigma.helper.driver import OSMS26, SGSP26, Stage, StageController


class Shot702(StageController):
    _STAGES = {"SGSP26": SGSP26, "OSMS26": OSMS26}
    PORT_FILTER = "ATEN"

    def __init__(self) -> None:
        super().__init__()
        # μm/pulse
        self._resolution = 0.0
        self.stage: Stage | None = None

    def open(self) -> None:
        """Connect stage controller(Shot702)."""
        self._ser.port = self.port
        self._ser.baudrate = 38400
        self._ser.bytesize = EIGHTBITS
        self._ser.stopbits = STOPBITS_ONE
        self._ser.timeout = 1
        self._ser.parity = PARITY_NONE
        self._ser.rtscts = True
        self._ser.open()
        self.initialize("OSMS26")

    def close(self) -> None:
        """Disconnect stage controller(Shot702)."""
        self._ser.close()

    def initialize(self, stage: str) -> None:
        """Initialize stage controller(Shot702).

        Parameters
        ----------
        stage : str
            Stage controlled by controller
        """
        self.stage = Shot702._STAGES[stage]
        division = 40
        self._set_division(division)
        self._resolution = round(self.stage.resolution_full / division, 2)

    def _set_division(self, division: int):
        """Change motor step angle (number of steps). Select one of the following 15
        step angles built into the driver. First specify an axis, then set the value.
        S: 180 Divides the step angle of the first axis into 80 angles. S: 280 Divides
        the step angle of the second axis into 80 angles. If the base step (full step)
        angle is to 0.72 degrees, the stepping motor makes one full turn every 500
        pulses. The motor is said to have a minimum resolution of 0.72 degrees(if the
        motor moves 10 mm for each turn, minimum resolution=10 mm ÷ 500 pulses=20μm).
        You can change the minimum resolution by dividing the motor step angle
        (1/2=0.36 degrees)

        Parameters
        ----------
        division : int
            Divisions of a stepping motor.
        """
        self._ser.send_query_message(f"S:1{division}")
        self._ser.send_query_message(f"S:2{division}")

    def _get_status(self) -> list[str]:
        """Get the coordinates for each axis and the current state of each stage.

        Returns
        -------
        list[str]
            The status of controller and stage. The first element is the first-axis
            coordinates. The second element is the second-axis coordinates. The third
            and subsequent ones represent the state of the controller.
        """
        return self._ser.send_query_message("Q:").split(",")

    def get_speed(self) -> list[list[int]]:
        """Get stages travel speed and acceleration/deceleration time.

        Returns
        -------
        list[List[int]]
            Stages speed[μm/sec] and acceleration/deceleration time[msec].
            The first element is the first axis. The second element is  the second axis.
        """
        speeds = self._ser.send_query_message("?:DW")
        speeds = re.split("[SFR]", speeds)[1:]
        speeds = [int(elem) for elem in speeds]
        speed_1_pps, speed_2_pps = speeds[:3], speeds[3:]
        speed_1_s = [self._pps_to_speed(elem) for elem in speed_1_pps[:2]]
        speed_1_s.append(speed_1_pps[-1])
        speed_2_s = [self._pps_to_speed(elem) for elem in speed_2_pps[:2]]
        speed_2_s.append(speed_2_pps[-1])
        return [speed_1_s, speed_2_s]

    def measure_positions(self) -> list[float]:
        """Return the current position information of 2 stages axis.

        Returns
        -------
        list[float]
            Current stages position[μm].
            Data format is [first axis, second axis]
        """
        positions = self._get_status()[:2]  # unit is [pulse]
        return [round(int(position.replace(" ", "")) * self._resolution, 2) for position in positions]

    def is_ready(self) -> list[bool]:
        """Check whether the controller is ready for operation or not.

        Returns
        -------
        list[bool]
            Status of stage is ready.
        """
        return [self._ser.send_query_message("!:") == "R"]

    def _pps_to_speed(self, pps: int) -> int:
        """Convert pps to speed.

        Parameters
        ----------
        pps : int
            Unit is [pulse/sec]

        Returns
        -------
        float
            Speed[μm]
        """
        return floor(pps * self._resolution)

    def _speed_to_pps(self, speed: int) -> int:
        """Convert speed to pps.

        Parameters
        ----------
        speed : int
            Unit is [μm/sec].

        Returns
        -------
        int
            pps[pulse/sec]
        """
        return floor(speed / self._resolution)

    def set_stage_speed(
        self,
        axis: Literal[1, 2],
        min: int,
        max: int,
        acceleration_time: int,
        original_reset_speed: int | None,
        mode: Literal["D", "V"] = "D",
    ) -> None:
        """Set stage speed.

        Parameters
        ----------
        axis : int
            Number of stage to set speed.
        min_speed : int
            Minimum speed[μm/sec]
        max_speed : int
            Maximum speed[μm/sec]
        acceleration_time : int
            [msec]
        mode : str, optional
            Mode of Deciding which setting you want to set the speed. When `D`, set
            normal stage speed. When `V`, set return original speed., by default `V`
        """
        command = f"{mode}:{axis}"
        min_pps = self._speed_to_pps(min)
        max_pps = self._speed_to_pps(max)
        command += f"S{min_pps}F{max_pps}R{acceleration_time}"
        self._ser.send_query_message(command)

    def _drive_stage(self) -> None:
        """When a drive command is issued, the stage starts moving.
        The G command is used after M, A, and J commands.
        """
        self._ser.send_query_message("G:")

    def fix_origin(self, axis: tuple[bool, bool]) -> None:
        """Set electronic (logical) origin to current position of each axis.

        Parameters
        ----------
        axis : list[bool], optional
            List that determines the axis to which the settings apply. The number of
            elements must always be 2.
        """
        command = f"R:{self._get_axis_option(axis)}"
        self._ser.send_query_message(command)

    def _get_axis_option(self, axis_data: tuple[Any, Any]) -> str:
        """Decide axis option

        Parameters
        ----------
        axis_data : tuple[Any, Any]
            Data of each axis

        Returns
        -------
        str
            When only the first axis, return "1". When only the second axis, return "2".
            When double axis, return "W".
        """
        return "W" if all(axis_data) else ("1" if axis_data[0] is not None else "2")

    def move_stages(
        self,
        displacements: tuple[int | None, int | None],
        mode: Literal["A", "M"] = "A",
    ) -> None:
        """Set displacement of stages and move stages. Travel is by means of
        acceleration/deceleration driving.

        Parameters
        ----------
        displacements : tuple[Optional[int], Optional[int]]
            Displacements of stages. The number of elements must always be 2.
        mode : str, optional
            Mode of stage drive. When "A", move absolute. When "M", move relative.
            , by default "A".
        """
        axis = self._get_axis_option(displacements[:2])
        command = f"{mode}:{axis}"
        for displacement in displacements[:2]:
            if displacement is None:
                continue
            direction = "-" if displacement < 0 else "+"
            pulse = floor(displacement / self._resolution)
            command += f"{direction}P{abs(pulse)}"
        self._ser.send_query_message(command)
        self._drive_stage()

    def move_stage_to_mechanical_origin(self, axis: tuple[bool, bool]) -> None:
        """Detect the mechanical origin for a stage and move the stage to the machine origin.
        Set the mechanical origin as the origin.

        Parameters
        ----------
        axis : tuple[bool, bool], optional
            List showing which stage to return to the return origin.
            The number of elements must always be 2.
        """
        self._ser.send_query_message(f"H:{self._get_axis_option(axis[:2])}")

    def stop(self, axis: tuple[bool, bool]) -> None:
        """Decelerate and stop the stage.

        Parameters
        ----------
        axis : tuple[bool, bool], optional
            List showing which axis to stop.
            The number of elements must always be 2.
        """
        self._ser.send_query_message(f"L:{self._get_axis_option(axis[:2])}")

    def emergency_stop(self) -> None:
        """Stops all stages immediately, whatever the conditions."""
        self._ser.send_query_message("L:E")

    def jog(
        self,
        directions: tuple[Literal["+", "-"] | None, Literal["+", "-"] | None],
    ) -> None:
        """Drives stages continuously (at a constant speed) at the Minimum speed.

        Parameters
        ----------
        direction : tuple[str], optional
            Drive directions. When "+", move to plus. When "-", move to minus.
        """
        commands = [str(direction) for direction in directions if direction]
        command = f"J:{self._get_axis_option(directions[:2])}{''.join(commands)}"
        self._ser.send_query_message(command)
        self._drive_stage()
