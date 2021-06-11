#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import os.path

class HardwarePWMException(Exception):
    pass



class HardwarePWM:
    """
    Control the hardware PWM on the Raspberry Pi. Need to first add `dtoverlay=pwm-2chan` to `/boot/config.txt`.

    pwm0 is GPIO pin 18 is physical pin 12
    pwm1 is GPIO pin 19 is physical pin 13

    Example
    ----------
    >pwm = HardwarePWM(0, hz=20)
    >pwm.start(100)
    >
    >pwm.change_duty_cycle(50)
    >pwm.change_frequency(50)
    >
    >pwm.stop()

    Notes
    --------
     - If you get "write error: Invalid argument" - you have to set duty_cycle to 0 before changing period
     - /sys/ pwm interface described here: https://jumpnowtek.com/rpi/Using-the-Raspberry-Pi-Hardware-PWM-timers.html

    """

    chippath = "/sys/class/pwm/pwmchip0"

    def __init__(self, pwm_channel, hz):
        assert pwm_channel in {0, 1}, "Only channel 0 and 1 are available on the Rpi."
        assert hz > 0.1, "Frequency can't be lower than 0.1 on the Rpi."

        self.pwm_channel = pwm_channel
        self.pwm_dir = f"{self.chippath}/pwm{self.pwm_channel}"
        self._duty_cycle = 0

        if not self.is_overlay_loaded():
            raise HardwarePWMException(
                "Need to add 'dtoverlay=pwm-2chan' to /boot/config.txt and reboot"
            )
        if not self.is_export_writable():
            raise HardwarePWMException(f"Need write access to files in '{self.chippath}'")
        if not self.does_pwmX_exists():
            self.create_pwmX()

        while True:
            try:
                self.change_frequency(hz)
                break
            except PermissionError:
                continue


    def is_overlay_loaded(self):
        return os.path.isdir(self.chippath)

    def is_export_writable(self):
        return os.access(os.path.join(self.chippath, "export"), os.W_OK)

    def does_pwmX_exists(self):
        return os.path.isdir(self.pwm_dir)

    def echo(self, m, fil):
        with open(fil, "w") as f:
            f.write(f"{m}\n")

    def create_pwmX(self):
        self.echo(self.pwm_channel, os.path.join(self.chippath, "export"))

    def start(self, initial_duty_cycle):
        self.change_duty_cycle(initial_duty_cycle)
        self.echo(1, os.path.join(self.pwm_dir, "enable"))

    def stop(self):
        self.change_duty_cycle(0)
        self.echo(0, os.path.join(self.pwm_dir, "enable"))

    def change_duty_cycle(self, duty_cycle):
        """
        a value between 0 and 100
        0 represents always low.
        100 represents always high.
        """
        assert 0 <= duty_cycle <= 100
        self._duty_cycle = duty_cycle
        per = 1 / float(self._hz)
        per *= 1000  # now in milliseconds
        per *= 1_000_000  # now in nanoseconds
        dc = int(per * duty_cycle / 100)
        self.echo(dc, os.path.join(self.pwm_dir, "duty_cycle"))

    def change_frequency(self, hz):
        self._hz = hz

        # we first have to change duty cycle, since https://stackoverflow.com/a/23050835/1895939
        if self._duty_cycle:
            self.change_duty_cycle(self._duty_cycle)

        per = 1 / float(self._hz)
        per *= 1000  # now in milliseconds
        per *= 1_000_000  # now in nanoseconds
        self.echo(int(per), os.path.join(self.pwm_dir, "period"))
