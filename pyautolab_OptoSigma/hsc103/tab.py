from pyautolab import api

from pyautolab_OptoSigma.helper.driver import PARAMETER
from pyautolab_OptoSigma.helper.tab import Cycle, Step, TabUI
from pyautolab_OptoSigma.hsc103.driver import Hsc103
from pyautolab_OptoSigma.widget import StageControlManager


class TabHsc103(api.DeviceTab):
    def __init__(self, device: Hsc103) -> None:
        super().__init__(device)
        self._ui = TabUI()
        self._ui.setup_ui(self)
        self.device = device
        self._setup_ui()

    def _setup_ui(self) -> None:
        self._ui.p_btn_open_control_manager.pressed.connect(self._open_control_manager)  # type: ignore

    def setup_settings(self):
        speed = self._ui.slider_speed.current_value
        acceleration_time = int(api.get_setting("hsc103.accelerationAndDecelerationTime"))
        self.device.set_stage_speed(
            axis=1, min=speed, max=speed, acceleration_time=acceleration_time, original_reset_speed=None
        )

    def get_controller(self) -> api.Controller | None:
        stop_time = self._ui.spinbox_stop_interval.value()
        operation_num = self._ui.spinbox_operation_num.value()
        distance = self._ui.spinbox_distance.value()
        judge_ready_interval = int(api.get_setting("hsc103.judgeReadyInterval"))

        controller_type = Cycle if self._ui.p_btn_cycle_mode.isChecked() else Step
        return controller_type(self.device, stop_time, operation_num, distance, judge_ready_interval)

    def get_parameters(self) -> dict[str, str]:
        return PARAMETER

    def _open_control_manager(self) -> None:
        StageControlManager(self.device).exec()
