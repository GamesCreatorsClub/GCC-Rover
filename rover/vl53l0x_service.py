#!/usr/bin/python3

import time
import traceback
import pyroslib
import smbus

# VL53L0X sensor service
#
# Based on https://raw.githubusercontent.com/popunder/VL53L0X/master/VL53L0Xtest.py
#
# This service is responsible reading distance.
#

DEBUG = True

I2C_BUS = 1
I2C_ADDRESS = 0x29


VL53L0X_REG_SYSRANGE_START = 0x0
VL53L0X_REG_SYSTEM_SEQUENCE_CONFIG = 0x01
VL53L0X_REG_SYSTEM_INTERMEASUREMENT_PERIOD = 0x04
VL53L0X_REG_SYSTEM_INTERRUPT_CONFIG_GPIO = 0x0A
VL53L0X_REG_SYSTEM_INTERRUPT_CLEAR = 0x0B
VL53L0X_REG_RESULT_INTERRUPT_STATUS = 0x13
VL53L0X_REG_RESULT_RANGE_STATUS = 0x14
VL53L0X_REG_FINAL_RANGE_CONFIG_MIN_COUNT_RATE_RTN_LIMIT = 0x44
VL53L0X_REG_MSRC_CONFIG_TIMEOUT_MACROP = 0x46
VL53L0X_REG_DYNAMIC_SPAD_NUM_REQUESTED_REF_SPAD = 0x4e
VL53L0X_REG_DYNAMIC_SPAD_REF_EN_START_OFFSET = 0x4f
VL53L0X_REG_PRE_RANGE_CONFIG_VCSEL_PERIOD = 0x50
VL53L0X_REG_PRE_RANGE_CONFIG_TIMEOUT_MACROP_HI = 0x51
VL53L0X_REG_MSRC_CONFIG_CONTROL = 0x60
VL53L0X_REG_FINAL_RANGE_CONFIG_VCSEL_PERIOD = 0x70
VL53L0X_REG_FINAL_RANGE_CONFIG_TIMEOUT_MACROP_HI = 0x71
VL53L0X_REG_GPIO_HV_MUX_ACTIVE_HIGH = 0x84

VL53L0X_REG_GLOBAL_CONFIG_SPAD_ENABLES_REF_0 = 0xB0
VL53L0X_REG_GLOBAL_CONFIG_SPAD_ENABLES_REF_1 = 0xB1
VL53L0X_REG_GLOBAL_CONFIG_SPAD_ENABLES_REF_2 = 0xB2
VL53L0X_REG_GLOBAL_CONFIG_SPAD_ENABLES_REF_3 = 0xB3
VL53L0X_REG_GLOBAL_CONFIG_SPAD_ENABLES_REF_4 = 0xB4
VL53L0X_REG_GLOBAL_CONFIG_SPAD_ENABLES_REF_5 = 0xB5
VL53L0X_REG_GLOBAL_CONFIG_REF_EN_START_SELECT = 0xB6

VL53L0X_REG_IDENTIFICATION_MODEL_ID = 0xc0
VL53L0X_REG_IDENTIFICATION_REVISION_ID = 0xc2

VL53L0X_REG_OSC_CALIBRATE_VAL = 0xf8

VcselPeriodPreRange = 0
VcselPeriodFinalRange = 1


SERVO_NUMBER = 8
SERVO_SPEED = 0.14 * 2  # 0.14 seconds per 60º (expecting servo to be twice as slow as per specs

lastServoAngle = 0

stopVariable = 0
i2cBus = None
spad_type_is_aperture = 0
spad_count = 0
io_timeout = 0
didTimeout = False

# SequenceStepEnables
enables = {
    "tcc": True,
    "msrc": True,
    "dss": True,
    "pre_range": True,
    "final_range": True
}

# SequenceStepTimeouts
timeouts = {
    "pre_range_vcsel_period_pclks": 0,
    "final_range_vcsel_period_pclks": 0,

    "msrc_dss_tcc_mclks": 0,
    "pre_range_mclks": 0,
    "final_range_mclks": 0,

    "msrc_dss_tcc_us": 0,
    "pre_range_us": 0,
    "final_range_us": 0
}


def moveServo(angle):
    global lastServoAngle
    # angle is between -90 and 90
    angle += 150
    angle = int(angle)

    f = open("/dev/servoblaster", 'w')
    f.write(str(SERVO_NUMBER) + "=" + str(angle) + "\n")
    f.close()

    angleDistance = abs(lastServoAngle - angle)
    sleepAmount = SERVO_SPEED * angleDistance / 60.0

    if DEBUG:
        print("Moved servo to angle " + str(angle) + " for distance " + str(angleDistance) + " so sleepoing for " + str(sleepAmount))

    # wait for servo to reach the destination
    time.sleep(sleepAmount)

    lastServoAngle = angle


def init():
    initVL53L0X()
    startContinuous(0)


def initVL53L0X():
    global i2cBus, stopVariable

    print("  initVL53L0X:")
    i2cBus = smbus.SMBus(I2C_BUS)

    # "Set I2C standard mode"
    i2cBus.write_byte_data(I2C_ADDRESS, 0x88, 0x00)

    i2cBus.write_byte_data(I2C_ADDRESS, 0x80, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x00, 0x00)
    stopVariable = i2cBus.read_byte_data(I2C_ADDRESS, 0x91)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x00, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x80, 0x00)

    # disable SIGNAL_RATE_MSRC (bit 1) and SIGNAL_RATE_PRE_RANGE (bit 4) limit checks
    i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_MSRC_CONFIG_CONTROL, i2cBus.read_byte_data(I2C_ADDRESS, VL53L0X_REG_MSRC_CONFIG_CONTROL) | 0x12)
    setSignalRateLimit(0.25)
    i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_SYSTEM_SEQUENCE_CONFIG, 0xFF)

    print("    checking spad info:")
    if not getSpadInfo():
        return False

    # The SPAD map (RefGoodSpadMap) is read by VL53L0X_get_info_from_device() in
    # the API, but the same data seems to be more easily readable from
    # GLOBAL_CONFIG_SPAD_ENABLES_REF_0 through _6, so read it from there
    ref_spad_map = [None] * 6
    # ref_spad_map = i2cBus.read_i2c_block_data(I2C_ADDRESS, VL53L0X_REG_GLOBAL_CONFIG_SPAD_ENABLES_REF_0, 6)
    ref_spad_map = i2cBus.read_block_data(I2C_ADDRESS, VL53L0X_REG_GLOBAL_CONFIG_SPAD_ENABLES_REF_0)

    # -- VL53L0X_set_reference_spads() begin (assume NVM values are valid)
    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_DYNAMIC_SPAD_REF_EN_START_OFFSET, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_DYNAMIC_SPAD_NUM_REQUESTED_REF_SPAD, 0x2C)
    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_GLOBAL_CONFIG_REF_EN_START_SELECT, 0xB4)

    first_spad_to_enable = spad_type_is_aperture if 12 else 0  # 12 is the first aperture spad
    spads_enabled = 0

    for i in range(0, 48):
        if i < first_spad_to_enable or spads_enabled == spad_count:
            # This bit is lower than the first one that should be enabled, or
            # (reference_spad_count) bits have already been enabled, so zero this bit
            ref_spad_map[i / 8] &= ~(1 << (i % 8))
        elif ref_spad_map[i / 8] >> (i % 8) & 0x1:
            spads_enabled += 1

    i2cBus.write_block_data(I2C_ADDRESS, VL53L0X_REG_GLOBAL_CONFIG_SPAD_ENABLES_REF_0, ref_spad_map)

    # -- VL53L0X_set_reference_spads() end
    #
    # -- VL53L0X_load_tuning_settings() begin
    # DefaultTuningSettings from vl53l0x_tuning.h

    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x00, 0x00)

    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x09, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x10, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x11, 0x00)

    i2cBus.write_byte_data(I2C_ADDRESS, 0x24, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x25, 0xFF)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x75, 0x00)

    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x4E, 0x2C)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x48, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x30, 0x20)

    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x30, 0x09)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x54, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x31, 0x04)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x32, 0x03)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x40, 0x83)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x46, 0x25)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x60, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x27, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x50, 0x06)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x51, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x52, 0x96)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x56, 0x08)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x57, 0x30)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x61, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x62, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x64, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x65, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x66, 0xA0)

    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x22, 0x32)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x47, 0x14)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x49, 0xFF)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x4A, 0x00)

    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x7A, 0x0A)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x7B, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x78, 0x21)

    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x23, 0x34)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x42, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x44, 0xFF)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x45, 0x26)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x46, 0x05)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x40, 0x40)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x0E, 0x06)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x20, 0x1A)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x43, 0x40)

    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x34, 0x03)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x35, 0x44)

    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x31, 0x04)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x4B, 0x09)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x4C, 0x05)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x4D, 0x04)

    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x44, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x45, 0x20)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x47, 0x08)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x48, 0x28)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x67, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x70, 0x04)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x71, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x72, 0xFE)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x76, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x77, 0x00)

    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x0D, 0x01)

    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x80, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x01, 0xF8)

    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x8E, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x00, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x80, 0x00)

    # -- VL53L0X_load_tuning_settings() end
    #
    # "Set interrupt config to new sample ready"
    # -- VL53L0X_SetGpioConfig() begin

    i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_SYSTEM_INTERRUPT_CONFIG_GPIO, 0x04)
    i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_GPIO_HV_MUX_ACTIVE_HIGH, i2cBus.read_byte_data(I2C_ADDRESS, VL53L0X_REG_GPIO_HV_MUX_ACTIVE_HIGH) & ~0x10)  # active low
    i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_SYSTEM_INTERRUPT_CLEAR, 0x01)

    # -- VL53L0X_SetGpioConfig() end
    
    measurement_timing_budget_us = getMeasurementTimingBudget()
    
    # "Disable MSRC and TCC by default"
    # MSRC = Minimum Signal Rate Check
    # TCC = Target CentreCheck
    # -- VL53L0X_SetSequenceStepEnable() begin
    
    i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_SYSTEM_SEQUENCE_CONFIG, 0xE8)
    
    # -- VL53L0X_SetSequenceStepEnable() end
    
    # "Recalculate timing budget"
    setMeasurementTimingBudget(measurement_timing_budget_us)
    
    # VL53L0X_StaticInit() end
    
    # VL53L0X_PerformRefCalibration() begin (VL53L0X_perform_ref_calibration())
    
    # -- VL53L0X_perform_vhv_calibration() begin
    
    i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_SYSTEM_SEQUENCE_CONFIG, 0x01)
    if not performSingleRefCalibration(0x40):
        return False
    
    # -- VL53L0X_perform_vhv_calibration() end
    
    # -- VL53L0X_perform_phase_calibration() begin
    
    i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_SYSTEM_SEQUENCE_CONFIG, 0x02)
    if not performSingleRefCalibration(0x00):
        return False
    
    # -- VL53L0X_perform_phase_calibration() end
    
    # "restore the previous Sequence Config"
    i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_SYSTEM_SEQUENCE_CONFIG, 0xE8)
    
    # VL53L0X_PerformRefCalibration() end
    return True

    # stopVariable = i2cBus.read_byte_data(I2C_ADDRESS, 0x91)


def startContinuous(period_ms):

    i2cBus.write_byte_data(I2C_ADDRESS, 0x80, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x00, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x91, stopVariable)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x00, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x80, 0x00)

    if period_ms != 0:
        # continuous timed mode

        # VL53L0X_SetInterMeasurementPeriodMilliSeconds() begin

        osc_calibrate_val = readReg16Bit(VL53L0X_REG_OSC_CALIBRATE_VAL)

        if osc_calibrate_val != 0:
            period_ms *= osc_calibrate_val

        writeReg32Bit(VL53L0X_REG_SYSTEM_INTERMEASUREMENT_PERIOD, period_ms)

        # VL53L0X_SetInterMeasurementPeriodMilliSeconds() end

        i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_SYSRANGE_START, 0x04)  # VL53L0X_REG_SYSRANGE_MODE_TIMED
    else:
        # continuous back-to-back mode
        i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_SYSRANGE_START, 0x02)  # VL53L0X_REG_SYSRANGE_MODE_BACKTOBACK


def stopContinuous():
    i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_SYSRANGE_START, 0x01)  # VL53L0X_REG_SYSRANGE_MODE_SINGLESHOT

    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x00, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x91, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x00, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x00)


def readRangeContinuousMillimeters():
    global didTimeout

    timeout_start_ms = time.time() * 1000
    while (i2cBus.read_byte_data(I2C_ADDRESS, VL53L0X_REG_RESULT_INTERRUPT_STATUS) & 0x07) == 0:
        if io_timeout > 0 and time.time() * 1000 - timeout_start_ms > io_timeout:
            didTimeout = True
            return 65535

    # assumptions: Linearity Corrective Gain is 1000(default);
    # fractional ranging is not enabled
    resultRange = readReg16Bit(VL53L0X_REG_RESULT_RANGE_STATUS + 10)

    i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_SYSTEM_INTERRUPT_CLEAR, 0x01)

    return resultRange


def readRangeSingleMillimeters():
    global didTimeout

    i2cBus.write_byte_data(I2C_ADDRESS, 0x80, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x00, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x91, stopVariable)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x00, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x80, 0x00)

    i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_SYSRANGE_START, 0x01)

    timeout_start_ms = time.time() * 1000
    while (i2cBus.read_byte_data(I2C_ADDRESS, VL53L0X_REG_SYSRANGE_START) & 0x01) == 0:
        if io_timeout > 0 and time.time() * 1000 - timeout_start_ms > io_timeout:
            didTimeout = True
            return 65535

    return readRangeContinuousMillimeters()


def getSpadInfo():
    global spad_count, spad_type_is_aperture

    i2cBus.write_byte_data(I2C_ADDRESS, 0x80, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x00, 0x00)

    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x06)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x83, i2cBus.read_byte_data(I2C_ADDRESS, 0x83) | 0x04)
    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x07)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x81, 0x01)

    i2cBus.write_byte_data(I2C_ADDRESS, 0x80, 0x01)

    i2cBus.write_byte_data(I2C_ADDRESS, 0x94, 0x6b)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x83, 0x00)

    timeout_start_ms = time.time() * 1000
    while i2cBus.read_byte_data(I2C_ADDRESS, 0x83) == 0x00:
        if io_timeout > 0 and time.time() * 1000 - timeout_start_ms > io_timeout:
            return False

    i2cBus.write_byte_data(I2C_ADDRESS, 0x83, 0x01)
    tmp = i2cBus.read_byte_data(I2C_ADDRESS, 0x92)

    spad_count = tmp & 0x7f
    spad_type_is_aperture = (tmp >> 7) & 0x01

    i2cBus.write_byte_data(I2C_ADDRESS, 0x81, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x06)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x83, i2cBus.read_byte_data(I2C_ADDRESS, 0x83 & ~0x04))
    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x00, 0x01)

    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x80, 0x00)

    return True


def setMeasurementTimingBudget(budget_us):

    StartOverhead = 1320  # note that this is different than the value in get_
    EndOverhead = 960
    MsrcOverhead = 660
    TccOverhead = 590
    DssOverhead = 690
    PreRangeOverhead = 660
    FinalRangeOverhead = 550

    MinTimingBudget = 20000

    if budget_us < MinTimingBudget:
        return False

    used_budget_us = StartOverhead + EndOverhead

    getSequenceStepEnables()
    getSequenceStepTimeouts()

    if enables["tcc"]:
        used_budget_us += (timeouts["msrc_dss_tcc_us"] + TccOverhead)

    if enables["dss"]:
        used_budget_us += 2 * (timeouts["msrc_dss_tcc_us"] + DssOverhead)
    elif enables["msrc"]:
        used_budget_us += (timeouts["msrc_dss_tcc_us"] + MsrcOverhead)

    if enables["pre_range"]:
        used_budget_us += (timeouts["pre_range_us"] + PreRangeOverhead)

    if enables["final_range"]:
        used_budget_us += FinalRangeOverhead

    # // "Note that the final range timeout is determined by the timing
    # // budget and the sum of all other timeouts within the sequence.
    # // If there is no room for the final range timeout, then an error
    # // will be set. Otherwise the remaining time will be applied to
    # // the final range."

    if used_budget_us > budget_us:
        return False         # // "Requested timeout too big."

    final_range_timeout_us = budget_us - used_budget_us

    # // set_sequence_step_timeout() begin
    # // (SequenceStepId == VL53L0X_SEQUENCESTEP_FINAL_RANGE)
    #
    # // "For the final range timeout, the pre-range timeout
    # //  must be added. To do this both final and pre-range
    # //  timeouts must be expressed in macro periods MClks
    # //  because they have different vcsel periods."

    final_range_timeout_mclks = timeoutMicrosecondsToMclks(final_range_timeout_us, timeouts["final_range_vcsel_period_pclks"])

    if enables["pre_range"]:
        final_range_timeout_mclks += timeouts["pre_range_mclks"]

    writeReg16Bit(VL53L0X_REG_FINAL_RANGE_CONFIG_TIMEOUT_MACROP_HI, encodeTimeout(final_range_timeout_mclks))

    # // set_sequence_step_timeout() end

    measurement_timing_budget_us = budget_us  # // store for internal reuse
    return True


def encodeTimeout(timeout_mclks):
    # // format: "(LSByte * 2^MSByte) + 1"

    ls_byte = 0
    ms_byte = 0

    if timeout_mclks > 0:
        ls_byte = timeout_mclks - 1

        while (ls_byte & 0xFFFFFF00) > 0:
            ls_byte >>= 1
            ms_byte += 1

        return (ms_byte << 8) | (ls_byte & 0xFF)

    else:
        return 0


def timeoutMicrosecondsToMclks(timeout_period_us, vcsel_period_pclks):
    macro_period_ns = calcMacroPeriod(vcsel_period_pclks)

    return ((timeout_period_us * 1000) + (macro_period_ns / 2)) / macro_period_ns


def getSequenceStepEnables():
    sequence_config = i2cBus.read_byte_data(I2C_ADDRESS, VL53L0X_REG_SYSTEM_SEQUENCE_CONFIG)

    enables["tcc"] = (sequence_config >> 4) & 0x1
    enables["dss"] = (sequence_config >> 3) & 0x1
    enables["msrc"] = (sequence_config >> 2) & 0x1
    enables["pre_range"] = (sequence_config >> 6) & 0x1
    enables["final_range"] = (sequence_config >> 7) & 0x1


def decodeVcselPeriod(reg_val):
    return (reg_val + 1) << 1


def getVcselPulsePeriod(tpe):
    if tpe == VcselPeriodPreRange:
        return decodeVcselPeriod(i2cBus.read_byte_data(I2C_ADDRESS, VL53L0X_REG_PRE_RANGE_CONFIG_VCSEL_PERIOD))
    elif tpe == VcselPeriodFinalRange:
        return decodeVcselPeriod(i2cBus.read_byte_data(I2C_ADDRESS, VL53L0X_REG_FINAL_RANGE_CONFIG_VCSEL_PERIOD))
    else:
        return 255


def calcMacroPeriod(vcsel_period_pclks):
    return ((2304 * vcsel_period_pclks * 1655) + 500) / 1000


def timeoutMclksToMicroseconds(timeout_period_mclks, vcsel_period_pclks):
    macro_period_ns = calcMacroPeriod(vcsel_period_pclks)

    return ((timeout_period_mclks * macro_period_ns) + (macro_period_ns / 2)) / 1000


def decodeTimeout(reg_val):
    # format: "(LSByte * 2^MSByte) + 1"
    return ((reg_val & 0x00FF) << ((reg_val & 0xFF00) >> 8)) + 1


def getSequenceStepTimeouts():

    timeouts["pre_range_vcsel_period_pclks"] = getVcselPulsePeriod(VcselPeriodPreRange)

    timeouts["msrc_dss_tcc_mclks"] = i2cBus.read_byte_data(I2C_ADDRESS, VL53L0X_REG_MSRC_CONFIG_TIMEOUT_MACROP) + 1
    timeouts["msrc_dss_tcc_us"] = timeoutMclksToMicroseconds(timeouts["msrc_dss_tcc_mclks"], timeouts["pre_range_vcsel_period_pclks"])

    timeouts["pre_range_mclks"] = decodeTimeout(readReg16Bit(VL53L0X_REG_PRE_RANGE_CONFIG_TIMEOUT_MACROP_HI))
    timeouts["pre_range_us"] = timeoutMclksToMicroseconds(timeouts["pre_range_mclks"], timeouts["pre_range_vcsel_period_pclks"])

    timeouts["final_range_vcsel_period_pclks"] = getVcselPulsePeriod(VcselPeriodFinalRange)

    timeouts["final_range_mclks"] = decodeTimeout(readReg16Bit(VL53L0X_REG_FINAL_RANGE_CONFIG_TIMEOUT_MACROP_HI))

    if enables["pre_range"]:
        timeouts["final_range_mclks"] -= timeouts["pre_range_mclks"]

    timeouts["final_range_us"] = timeoutMclksToMicroseconds(timeouts["final_range_mclks"], timeouts["final_range_vcsel_period_pclks"])


def getMeasurementTimingBudget():

    StartOverhead = 1910  # note that this is different than the value in set_
    EndOverhead = 960
    MsrcOverhead = 660
    TccOverhead = 590
    DssOverhead = 690
    PreRangeOverhead = 660
    FinalRangeOverhead = 550

    # "Start and end overhead times always present"
    budget_us = StartOverhead + EndOverhead

    getSequenceStepEnables()
    getSequenceStepTimeouts()

    if enables["tcc"]:
        budget_us += timeouts["msrc_dss_tcc_us"] + TccOverhead

    if enables["dss"]:
        budget_us += 2 * (timeouts["msrc_dss_tcc_us"] + DssOverhead)
    elif enables["msrc"]:
        budget_us += (timeouts["msrc_dss_tcc_us"] + MsrcOverhead)

    if enables["pre_range"]:
        budget_us += (timeouts["pre_range_us"] + PreRangeOverhead)

    if enables["final_range"]:
        budget_us += (timeouts["final_range_us"] + FinalRangeOverhead)

    measurement_timing_budget_us = budget_us  # store for internal reuse
    return budget_us


def performSingleRefCalibration(vhv_init_byte):
    i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_SYSRANGE_START, 0x01 | vhv_init_byte)  # VL53L0X_REG_SYSRANGE_MODE_START_STOP

    timeout_start_ms = time.time() * 1000
    while (i2cBus.read_byte_data(I2C_ADDRESS, VL53L0X_REG_RESULT_INTERRUPT_STATUS) & 0x07) == 0:
        if io_timeout > 0 and time.time() * 1000 - timeout_start_ms > io_timeout:
            return False

    i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_SYSTEM_INTERRUPT_CLEAR, 0x01)

    i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_SYSRANGE_START, 0x00)

    return True


def setSignalRateLimit(limit_Mcps):
    if limit_Mcps < 0 or limit_Mcps > 511.99:
        return False

    # Q9.7 fixed point format (9 integer bits, 7 fractional bits)
    writeReg16Bit(VL53L0X_REG_FINAL_RANGE_CONFIG_MIN_COUNT_RATE_RTN_LIMIT, limit_Mcps * (1 << 7))
    return True


def writeReg16Bit(reg, value):
    block = [(int(value) >> 8) & 0xFF, int(value) & 0xFF]
    i2cBus.write_block_data(I2C_ADDRESS, reg, block)


def writeReg32Bit(reg, value):
    block = [(int(value) >> 24) & 0xFF, (int(value) >> 16) & 0xFF, (int(value) >> 8) & 0xFF, int(value) & 0xFF]
    i2cBus.write_block_data(I2C_ADDRESS, reg, block)


def readReg16Bit(reg):
    # block = i2cBus.read_i2c_block_data(I2C_ADDRESS, reg, 2)
    block = i2cBus.read_block_data(I2C_ADDRESS, reg, 2)
    return ((block[0] & 0xFF) << 8) | (block[1] & 0xFF)


def readDistance():
    def makeuint16(lsb, msb):
        return ((msb & 0xFF) << 8) | (lsb & 0xFF)

    i2cBus.write_byte_data(I2C_ADDRESS, 0x80, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x00, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x91, stopVariable)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x00, 0x01)
    i2cBus.write_byte_data(I2C_ADDRESS, 0xFF, 0x00)
    i2cBus.write_byte_data(I2C_ADDRESS, 0x80, 0x00)

    if DEBUG:
        print("    Initiating read...")
    i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_SYSRANGE_START, 0x01)

    count = 0
    while count < 10:  # 0.1 second waiting time max
        time.sleep(0.010)
        val = i2cBus.read_byte_data(I2C_ADDRESS, VL53L0X_REG_RESULT_RANGE_STATUS)
        if val & 0x01:
            break
        count += 1

    data = i2cBus.read_block_data(I2C_ADDRESS, 0x14, 12)

    status = ((data[0] & 0x78) >> 3)

    i2cBus.write_byte_data(I2C_ADDRESS, VL53L0X_REG_SYSTEM_INTERRUPT_CLEAR, 0x01)

    if DEBUG:
        # if status == 0:
        #     print("    Data OK!")
        if status == 0x01:
            print("    VCSEL CONTINUITY TEST FAILURE!")
        if status == 0x02:
            print("    VCSEL WATCHDOG TEST FAILURE!")
        if status == 0x03:
            print("    NO VHV VALUE FOUND!")
        if status == 0x04:
            print("    MSRC NO TARGET!")
        if status == 0x05:
            print("    SNR CHECK!")
        if status == 0x06:
            print("    RANGE PHASE CHECK!")
        if status == 0x07:
            print("    SIGMA THRESHOLD CHECK!")
        if status == 0x08:
            print("    TCC!")
        if status == 0x09:
            print("    PHASE CONSISTENCY!")
        if status == 0x0A:
            print("    MIN CLIP!")
        # if status == 0x0B:
        #     print("    RANGE COMPLETE!")
        if status == 0x0C:
            print("    ALGO UNDERFLOW!")
        if status == 0x0D:
            print("    ALGO OVERFLOW!")
        if status == 0x0E:
            print("    RANGE IGNORE THRESHOLD!")

        print("    Got result after " + str(count) + " checks. Status " + bin(status))

    if status == 0x0B or status == 0:
        distance = makeuint16(data[11], data[10])
    else:
        distance = -1

    if DEBUG:
        print("  Distance is " + str(distance) + "mm")

    return distance


def handleRead(topic, payload, groups):
    angle = float(payload)
    if DEBUG:
        print("Got read - moving to angle " + str(angle))

    moveServo(angle)
    distance = readDistance()
    # print ("   distance =" + str(distance))
    pyroslib.publish("sensor/distance", str(angle) + ":" + str(distance))


def handleScan(topic, payload, groups):
    startScan = True

    if DEBUG:
        print("  Got scan...")

    distances = {}
    angle = -90
    while angle <= 90:
        moveServo(float(angle))
        distance = readDistance()
        if distance < 0:
            distance = 2000
        distances[angle] = distance
        angle += 22.5

    angle = 90
    while angle >= -90:
        moveServo(float(angle))
        distance = readDistance()
        if distance < 0:
            distance = 2000
            distances[angle] = 2000
        elif distance < distances[angle]:
            distances[angle] = distance
        angle -= 22.5

    angles = list(distances.keys())
    angles.sort()

    distancesList = []
    for angle in angles:
        distancesList.append(str(angle) + ":" + str(distances[angle]))

    # print ("   distance =" + str(distance))
    pyroslib.publish("sensor/distance", str(",".join(distancesList)))


if __name__ == "__main__":
    try:
        print("Starting vl53l0x sensor service...")

        init()

        moveServo(lastServoAngle)

        time.sleep(1)

        pyroslib.subscribe("sensor/distance/read", handleRead)
        pyroslib.subscribe("sensor/distance/scan", handleScan)
        pyroslib.init("vl53l0x-sensor-service")

        print("Started vl53l0x sensor service.")

        pyroslib.forever(0.02)

    except Exception as ex:
        print("ERROR: " + str(ex) + "\n" + ''.join(traceback.format_tb(ex.__traceback__)))
