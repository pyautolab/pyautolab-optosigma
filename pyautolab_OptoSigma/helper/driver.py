from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass

from serial import Serial
from typing_extensions import Final, Literal

from pyautolab import api

PARAMETER = {"Displacement": "μm"}


class _StageControllerSerial(Serial):
    def __init__(self):
        super().__init__(timeout=0)
        self._delimiter = b"\r\n"

    def send_message(self, message: str) -> None:
        self.write(message.encode("ascii") + self._delimiter)

    def receive_message(self) -> str:
        return (self.readline()[: -1 * len(self._delimiter)]).decode("utf-8")

    def send_query_message(self, message: str) -> str:
        self.send_message(message)
        return self.receive_message()


@dataclass(frozen=True)
class Stage:
    name: str
    # μm/pulse
    resolution_full: int
    # x_micro_per_pulse_full: int
    # mm/sec
    max_speed: int


SGSP26: Final = Stage(name="SGSP26", resolution_full=4, max_speed=30)
OSMS26: Final = Stage(name="OSMS26", resolution_full=4, max_speed=10)


class StageController(api.Device):
    def __init__(self) -> None:
        super().__init__()
        self._ser = _StageControllerSerial()

    def receive(self) -> str:
        return self._ser.receive_message()

    def send(self, message: str) -> None:
        self._ser.send_message(message)

    def reset_buffer(self) -> None:
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()

    @abstractmethod
    def get_speed(self) -> list[list[float]]:
        """Get stages travel speed and acceleration/deceleration time.

        Returns
        -------
        list[int]
            Stages speed[μm/sec] and acceleration/deceleration time[msec] for each axis.
        """
        pass

    @abstractmethod
    def set_stage_speed(
        self,
        axis: Literal[1, 2],
        min: int,
        max: int,
        acceleration_time: int,
        original_reset_speed: int | None,
        mode: str,
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
            Mode of Deciding which setting you want to set the speed.
        """
        pass

    @abstractmethod
    def measure_positions(self) -> list[float]:
        """Return the current position information of 3 stages axis.

        Returns
        -------
        list[float]
            Current stages position[μm].
        """
        pass

    @abstractmethod
    def move_stages(self, displacements: tuple[int | None, ...], mode: Literal["A", "M"] = "A") -> None:
        """Set displacement of stages and move stages. Travel is by means of
        acceleration/deceleration driving.

        Parameters
        ----------
        displacements : tuple[int, int]
            Displacements of stages. The number of elements must always be maximum
            number of stages.
        mode : str, optional
            Mode of stage drive. When "A", move absolute. When "M", move relative.
            , by default "A".
        """
        pass

    @abstractmethod
    def is_ready(self) -> list[bool]:
        """Check whether the controller is ready for operation or not.

        Returns
        -------
        list[bool]
            Status of stages are ready or not.
        """
        pass

    @abstractmethod
    def fix_origin(self, axis: tuple[bool, ...]) -> None:
        """Set electronic (logical) origin to current position of each axis.

        Parameters
        ----------
        axis : list[bool], optional
            List that determines the axis to which the settings apply.
        """
        pass

    @abstractmethod
    def move_stage_to_mechanical_origin(self, axis: tuple[bool, ...]) -> None:
        """Detect the mechanical origin for a stage and move the stage to the machine origin.
        Set the mechanical origin as the origin.

        Parameters
        ----------
        axis : tuple[bool, bool, bool], optional
            List showing which axis to return to the return origin.
            The number of elements must always be maximum number of stages.
        """
        pass

    @abstractmethod
    def stop(self, axis: tuple[bool, ...]) -> None:
        """Decelerate and stop the stage.

        Parameters
        ----------
        axis : tuple[bool, bool], optional
            List showing which axis to stop.
            The number of elements must always be maximum number of stages.
        """
        pass

    @abstractmethod
    def emergency_stop(self) -> None:
        """Stops all stages immediately, whatever the conditions."""
        pass

    @abstractmethod
    def jog(
        self,
        directions: tuple[Literal["+", "-"] | None, ...],
    ) -> None:
        """Drives stages continuously (at a constant speed) at the Minimum speed.

        Parameters
        ----------
        directions : tuple[str], optional
                        Drive directions. When `+`, move to plus.
                        When `-`, move to minus.
        """
        pass

    def measure(self) -> dict[str, float]:
        return {list(PARAMETER)[0]: self.measure_positions()[0]}
