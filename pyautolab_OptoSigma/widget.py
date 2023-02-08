import qtawesome as qta
from pyautolab import api
from qtpy.QtCore import QSize, Qt, Slot  # type: ignore
from qtpy.QtWidgets import QGridLayout, QGroupBox, QLabel, QSizePolicy, QVBoxLayout
from serial.serialutil import SerialException

from pyautolab_OptoSigma.helper.driver import StageController


class StageControlManager(api.widgets.Manager):
    def __init__(self, device: StageController):
        super().__init__()
        self._device = device
        self._lcd_position = QLabel()
        self._int_slider = api.widgets.IntSlider()
        self._t_btn_up = api.qt.tool_button(
            arrow_type=Qt.ArrowType.UpArrow,
            fixed_height=50,
            fixed_width=50,
            pressed=self.up_stage,
            released=self.stop_stage,
        )
        self._t_btn_down = api.qt.tool_button(
            arrow_type=Qt.ArrowType.DownArrow,
            fixed_height=50,
            fixed_width=50,
            icon_size=QSize(30, 30),
            pressed=self.down_stage,
            released=self.stop_stage,
        )
        self._t_btn_emergency_stop = api.qt.tool_button(
            fixed_width=50,
            fixed_height=50,
            icon=qta.icon("ph.stop-fill", color="red"),
            icon_size=QSize(70, 70),
            clicked=self.emergency_stop,
        )
        self._p_button_fix_zero = api.qt.push_button(clicked=self.fix_zero, text="Fix Zero")
        self._p_button_move_machine_zero = api.qt.push_button(
            clicked=self.move_to_machine_zero, text="Move Machine Zero-Point"
        )
        self._p_button_set_speed = api.qt.push_button(
            clicked=self.set_stage_speed, fixed_width=100, text="Set"
        )

        # timer
        self.timer_measure_position = api.qt.timer(parent=self, timeout=self.measure_position)

        # setup
        self._int_slider.range = (1, 50000)

        # setup layout
        group_control = QGroupBox("Control")
        group_control.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        api.qt.layout(
            self._t_btn_up, self._t_btn_emergency_stop, self._t_btn_down, parent=group_control,
        ).setAlignment(Qt.AlignmentFlag.AlignHCenter)

        group_position = QGroupBox("Current Position")
        api.qt.layout([api.qt.add_unit(self._lcd_position, "μm")], parent=group_position)

        group_origin = QGroupBox("Origin")
        api.qt.layout(self._p_button_fix_zero, self._p_button_move_machine_zero, parent=group_origin)

        v_layout_speed = QVBoxLayout()
        v_layout_speed.addWidget(api.qt.add_unit(self._int_slider, "μm/msec"))
        v_layout_speed.addWidget(self._p_button_set_speed, alignment=Qt.AlignmentFlag.AlignRight)
        group_speed = QGroupBox("Speed Setting")
        group_speed.setLayout(v_layout_speed)

        g_layout = QGridLayout(self)
        g_layout.addWidget(group_control, 1, 1, 2, 1)
        g_layout.addWidget(group_position, 1, 2)
        g_layout.addWidget(group_origin, 2, 2)
        g_layout.addWidget(group_speed, 3, 1, 1, 2)

    @Slot()
    @api.qt.popup_exception(SerialException)
    def up_stage(self) -> None:
        self._device.jog(("+", None, None))
        self.timer_measure_position.start(60)

    @Slot()
    @api.qt.popup_exception(SerialException)
    def down_stage(self) -> None:
        self._device.jog(("-", None, None))
        self.timer_measure_position.start(60)

    @Slot()
    @api.qt.popup_exception(SerialException)
    def stop_stage(self) -> None:
        self._device.stop((True, False, False))
        self.timer_measure_position.stop()

    @Slot()
    @api.qt.popup_exception(SerialException)
    def emergency_stop(self) -> None:
        self._device.emergency_stop()
        self.timer_measure_position.stop()

    @Slot()
    @api.qt.popup_exception(SerialException)
    def move_to_machine_zero(self) -> None:
        self._device.move_stage_to_mechanical_origin((True, False, False))
        self.timer_measure_position.start(60)

    @Slot()
    @api.qt.popup_exception(SerialException)
    def fix_zero(self) -> None:
        self._device.fix_origin((True, False, False))
        self._lcd_position.setText(str(self._device.measure_positions()[0]))

    @Slot()
    @api.qt.popup_exception(SerialException)
    def set_stage_speed(self) -> None:
        max_speed = self._int_slider.current_value
        self._device.set_stage_speed(1, max_speed, max_speed, 100, None, mode="D")
        self._device.set_stage_speed(1, max_speed, max_speed, 100, max_speed, mode="B")

    @Slot()
    @api.qt.popup_exception(SerialException)
    def measure_position(self) -> None:
        self._lcd_position.setText(str(self._device.measure_positions()[0]))
        if self._device.is_ready():
            self.timer_measure_position.stop()
