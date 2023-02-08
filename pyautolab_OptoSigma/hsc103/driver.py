from typing import Literal

from serial.serialutil import EIGHTBITS, PARITY_NONE, STOPBITS_ONE

from pyautolab_OptoSigma.helper.driver import OSMS26, SGSP26, StageController


class Hsc103(StageController):
    # List of available stages
    _STAGES = {"SGSP26": SGSP26, "OSMS26": OSMS26}

    def __init__(self) -> None:
        super().__init__()

    def open(self) -> None:
        """Connect stage controller(Hsc103)."""
        self._ser.port = self.port
        self._ser.baudrate = 38400
        self._ser.bytesize = EIGHTBITS
        self._ser.stopbits = STOPBITS_ONE
        self._ser.timeout = 1
        self._ser.parity = PARITY_NONE
        self._ser.rtscts = True
        self._ser.open()

    def close(self) -> None:
        """Disconnect stage controller(Hsc103)."""
        self._ser.close()

    def get_speed(self) -> list[list[float]]:
        """Get stages travel speed and acceleration/deceleration time.

        Returns
        -------
        list[List[int]]
            Stages speed[μm/sec] and acceleration/deceleration time[msec] for each axis.
            About data of each element: [first axis, second axis, third axis].
            About data of each axis data:
            [Start-up speed, Maximum speed, Acceleration/deceleration time].
        """
        speeds = []
        for i in range(1, 4):
            speed_str = self._ser.send_query_message(f"?:D{i}").split(",")
            speed_int = [round(int(elem), 2) for elem in speed_str[:2]]
            speed_int.append(int(speed_str[-1]))
            speeds.append(speed_int)
        return speeds

    def measure_positions(self) -> list[float]:
        """Return the current position information of 3 stages axis.

        Returns
        -------
        list[float]
            Current stages position[μm].
            Data format is [first axis, second axis, third axis].
        """
        positions = self._ser.send_query_message("Q:").split(",")
        return [round(int(position) / 100, 2) for position in positions]

    def is_ready(self) -> list[bool]:
        """Check whether the controller is ready for operation or not.

        Returns
        -------
        list[bool]
            Status of stages are ready or not.
        """
        messages = self._ser.send_query_message("!:").split(",")
        return [int(stage_status) == 0 for stage_status in messages]

    def set_stage_speed(
        self,
        axis: Literal[1, 2, 3],
        min: int,
        max: int,
        acceleration_time: int,
        original_reset_speed: int | None,
        mode: Literal["D", "B"] = "D",
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
            normal stage speed. When `B`, set return original speed., by default `D`.
        """
        pre_command = f"{mode}:"
        command = pre_command + f"{axis},{min*100},{max*100},{acceleration_time}"
        if original_reset_speed is not None:
            command += f",{original_reset_speed * 100}"
        self._ser.send_query_message(command)

    def fix_origin(self, axis: tuple[bool, bool, bool]) -> None:
        """Set electronic (logical) origin to current position of each axis.

        Parameters
        ----------
        axis : list[bool], optional
            List that determines the axis to which the settings apply.
        """
        # Convert bool to binary number(False -> 0 -> "0", True -> 1 -> "1")
        converted = [str(int(elem)) for elem in axis]
        self._ser.send_query_message("R:" + ",".join(converted))

    def move_stages(
        self,
        displacements: tuple[int | None, int | None, int | None],
        mode: Literal["A", "M"] = "A",
    ) -> None:
        """Set displacement of stages and move stages. Travel is by means of
        acceleration/deceleration driving.

        Parameters
        ----------
        displacements :  tuple[Optional[int], Optional[int]]
            Displacements of stages. The number of elements must always be 3.
            Unit is [μm].
        mode : str, optional
            Mode of stage drive. When "A", move absolute. When "M", move relative.
            , by default "A"
        """
        displacement_str = [str(elem * 100) if elem is not None else "" for elem in displacements]
        command = f"{mode}:" + ",".join(displacement_str)
        self._ser.send_query_message(command)

    def move_stage_to_mechanical_origin(self, axis: tuple[bool, bool, bool]) -> None:
        """Detect the mechanical origin for a stage and move the stage to the machine origin.
        Set the mechanical origin as the origin.

        Parameters
        ----------
        axis : tuple[bool, bool, bool], optional
            List showing which axis to return to the return origin.
            The number of elements must always be 3.
        """
        # Convert bool to binary number(False -> 0 -> "0", True -> 1 -> "1")
        converted = [str(int(elem)) for elem in axis]
        command = "H:" + ",".join(converted)
        self._ser.send_query_message(command)

    def stop(self, axis: tuple[bool, bool]) -> None:
        """Decelerate and stop the stage.

        Parameters
        ----------
        axis : tuple[bool, bool], optional
            List showing which axis to stop.
            The number of elements must always be 3.
        """
        # Convert bool to binary number(False -> 0 -> "0", True -> 1 -> "1")
        axis_str = [str(int(elem)) for elem in axis]
        command = "L:" + ",".join(axis_str)
        self._ser.send_query_message(command)

    def emergency_stop(self) -> None:
        """Stops all stages immediately, whatever the conditions."""
        self._ser.send_query_message("L:E")

    def jog(
        self,
        directions: tuple[
            Literal["+", "-"] | None,
            Literal["+", "-"] | None,
            Literal["+", "-"] | None,
        ],
    ) -> None:
        """Drives stages continuously (at a constant speed) at the Minimum speed.

        Parameters
        ----------
        directions : tuple[str], optional
                        Drive directions. When "+", move to plus.
                        When "-", move to minus.
        """
        commands = [str(direction) if direction else "" for direction in directions]
        command = "J:" + ",".join(commands)
        self._ser.send_query_message(command)
