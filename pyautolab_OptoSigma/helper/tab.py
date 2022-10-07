import qtawesome as qta
from pyautolab import api
from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import QButtonGroup, QFormLayout, QGridLayout, QGroupBox, QSpinBox, QWidget

from pyautolab_OptoSigma.helper.driver import StageController


class TabUI:
    def setup_ui(self, parent: QWidget) -> None:
        # member
        self.p_btn_step_mode = api.qt_helpers.create_push_button(fixed_width=250, text="Step Mode")
        self.p_btn_cycle_mode = api.qt_helpers.create_push_button(fixed_width=250, text="Cycle Mode")
        self.p_btn_open_control_manager = api.qt_helpers.create_push_button(
            fixed_width=40, fixed_height=40, icon=qta.icon("fa.arrows")
        )
        self.spinbox_distance = QSpinBox()
        self.spinbox_operation_num = QSpinBox()
        self.slider_speed = api.widgets.IntSlider()
        self.spinbox_stop_interval = QSpinBox()

        self._group_mode = QGroupBox()

        # Setup button
        self.p_btn_step_mode.setCheckable(True)
        self.p_btn_cycle_mode.setCheckable(True)
        self._btn_group = QButtonGroup(parent)
        self._btn_group.addButton(self.p_btn_step_mode)
        self._btn_group.addButton(self.p_btn_cycle_mode)
        self._btn_group.setExclusive(True)
        self.p_btn_cycle_mode.setChecked(True)

        # Setup ui
        self.spinbox_distance.setRange(-100000, 300000)
        self.spinbox_operation_num.setRange(1, 100000)
        self.slider_speed.range = 1, 50000
        self.spinbox_stop_interval.setRange(0, 100_000_000)
        self.spinbox_operation_num.setValue(100)
        self.slider_speed.update_current_value(5000)

        # Setup layout
        h_layout_mode = api.qt_helpers.create_h_box_layout(
            [self.p_btn_step_mode, self.p_btn_cycle_mode, self.p_btn_open_control_manager]
        )
        self._group_mode.setLayout(h_layout_mode)

        f_layout = QFormLayout()
        f_layout.addRow("Displacement: ", api.qt_helpers.add_unit(self.spinbox_distance, "μm"))
        f_layout.addRow("Number of Operations: ", self.spinbox_operation_num)
        f_layout.addRow("Speed: ", api.qt_helpers.add_unit(self.slider_speed, "μm/sec"))
        f_layout.addRow("Stop Interval: ", api.qt_helpers.add_unit(self.spinbox_stop_interval, "msec"))

        g_layout = QGridLayout(parent)
        g_layout.addWidget(self._group_mode, 0, 0)
        g_layout.addWidget(self.p_btn_open_control_manager, 0, 1)
        g_layout.addLayout(f_layout, 1, 0, 1, 2)


class Step(api.Controller):
    def __init__(
        self, device: StageController, stop_time: int, step_num: int, distance: int, judge_ready_interval: int
    ) -> None:
        super().__init__()
        self._device = device
        self._stop_time = stop_time
        self._step_num = step_num
        self._distance = distance
        self._count = 1
        self._judge_ready_interval = judge_ready_interval

    def start(self) -> None:
        # TODO: When implement thread, remove timer.
        self._timer_move_stage = api.qt_helpers.create_timer(
            self, timeout=self._step, enable_count=True, timer_type=Qt.TimerType.PreciseTimer
        )
        self._device.fix_origin((True, False, False))
        self._timer_move_stage.start(self._judge_ready_interval)

    @Slot()
    def _step(self) -> None:
        # TODO: When implement thread, change event loop sleep to built-in sleep.
        if self._device.is_ready()[0]:
            self._device.move_stages((self._distance, None, None), "M")
            self._count += 1
            if self._step_num <= self._count:
                self.stop()
                return
            api.qt_helpers.sleep_nonblock_window(self._stop_time)

    def stop(self) -> None:
        self._timer_move_stage.stop()
        return super().stop()


class Cycle(api.Controller):
    def __init__(
        self, device: StageController, stop_time: int, cycle_num: int, distance: int, judge_ready_interval: int
    ) -> None:
        super().__init__()
        self._device = device
        self._cycle_num = cycle_num * 2
        self._count = 1
        self._distance = distance
        self._stop_time = stop_time
        self._judge_ready_interval = judge_ready_interval

    def start(self) -> None:
        # TODO: When implement thread, remove timer.
        self._timer_move_stage = api.qt_helpers.create_timer(
            self, timeout=self._cycle, enable_count=True, timer_type=Qt.TimerType.PreciseTimer
        )
        self._device.fix_origin((True, False, False))
        self._timer_move_stage.start(self._judge_ready_interval)

    def _cycle(self) -> None:
        # TODO: When implement thread, remove timer
        if self._device.is_ready()[0]:
            move_position = self._distance if self._count % 2 else 0
            self._device.move_stages((move_position, None, None))
            self._count += 1
            if self._cycle_num <= self._count - 2:
                self.stop()
                return
            api.qt_helpers.sleep_nonblock_window(self._stop_time)

    def stop(self) -> None:
        self._timer_move_stage.stop()
        self._device.emergency_stop()
        return super().stop()
