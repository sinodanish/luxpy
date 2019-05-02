# -*- coding: utf-8 -*-
"""
Module for working with JETI specbos 1211 spectroradiometer (windows)
=====================================================================

Installation:
-------------
 1. Install jeti drivers.
 2. Ready to go.
 
Functions:
----------
 :dvc_detect(): detect number of connected JETI devices.
 :dvc_open(): open device.
 :close_open(): close device.
 :dvc_reset(): reset device (same as disconnecting and reconnecting USB).
 :start_meas(): start measurement on already opened device.
 :check_meas_status(): check status of initiated measurement.
 :wait_until_meas_is_finished(): wait until a initiated measurement is finished.
 :read_spectral_radiance(): read measured spectral radiance (W/m².sr.nm) from device.
 :set_default(): set all measurement parameters to the default values.
 :get_wavelength_params(): get wavelength calibration parameters of polynomial of order 5.
 :measure_flicker_freq(): measure flicker frequency (Hz)
 :get_laser_status(): get pilot laser status of device.
 :set_laser_status(): set pilot laser status of device.
 :set_laser(): turn laser ON (3 modulation types: 7Hz (1), 28 Hz (2) and 255 Hz (3)) or OFF (0) and set laser intensity.
 :get_calibration_range(): get calibration range.
 :get_shutter_status(): get shutter status of device. 
 :set_shutter_status(): set shutter status of device. 
 :get_integration_time(): get default integration time stored in device.
 :get_min_integration_time(): get the minimum integration time (seconds) which can be used with the connected device.
 :get_max_auto_integration_time(): get the maximum integration time which will be used for adaption (automated Tint selection).
 :set_max_auto_integration_time(): set the maximum integration time which will be used for adaption (automated Tint selection).
 :get_spd(): measure spectral radiance (W/nm.sr.m²).

 
Default parameters:
-------------------
 :_TWAIT_STATUS: default time to wait before checking measurement status in wait_until_meas_is_finished().
 :_TINT_MAX: maximum integration time for device. 
 :_TINT_MIN: minimum integration time #set to None -> If None: find it on device (in 'start_meas()' fcn.)
 :_ERROR: error value.
 :_PKG_PATH = path to (sub)-package.
 
.. codeauthor:: Kevin A.G. Smet (ksmet1977 at gmail.com)
"""


import ctypes
from ctypes import wintypes
import numpy as np
import time
import os
import platform

__all__  = ['_TWAIT_STATUS', '_TINT_MIN', '_TINT_MAX', '_ERROR']
__all__ += ['dvc_open','dvc_close', 'dvc_detect', 'start_meas', 'check_meas_status','wait_until_meas_is_finished']
__all__ += ['read_spectral_radiance']
__all__ += ['dvc_reset', 'set_default', 'get_wavelength_params','measure_flicker_freq']
__all__ += ['get_laser_status', 'set_laser_status', 'set_laser', 'get_calibration_range']
__all__ += ['get_shutter_status', 'set_shutter_status']
__all__ += ['get_integration_time', 'get_min_integration_time']
__all__ += ['get_max_auto_integration_time','set_max_auto_integration_time']
__all__ += ['get_spd']


# set ctypes:
DWORD = wintypes.DWORD
DWORD_PTR = ctypes.POINTER(DWORD)
WORD = wintypes.WORD
BOOL = ctypes.c_bool
FLOAT = ctypes.c_float
INT32 = ctypes.c_int32

# Set some general global parameters:
_TWAIT_STATUS = 0.1
_TINT_MAX = 60 
_TINT_MIN = None # If None: find it on device (in 'start_meas()' fcn.)
_ERROR = None
_PKG_PATH = os.path.dirname(__file__)

def load_dlls(path = _PKG_PATH):
    """
    Load dlls.
    
    Args:
        :path:
            | path to dll folder with win32 and win64 subfolders with *.dll files.
            
    Returns:
        :jtc, jtre: handles to the jeti_core and jeti_radio_ex 
    """
    # check windows architecture:
    arch = platform.architecture()
    if 'windows' not in arch[1].lower():
        raise Exception("JETI only supports Window platform.")
    bitversion = arch[0][:2]

    # Load DLL into memory.
    _JETI_DLL_PATH =  os.path.join(path, 'dll', 'win' + bitversion)
    if bitversion != '64':
        bitversion = ''
    jtc = ctypes.WinDLL (os.path.join(_JETI_DLL_PATH, "jeti_core"+bitversion+".dll"))
    jtre = ctypes.WinDLL (os.path.join(_JETI_DLL_PATH, "jeti_radio_ex"+bitversion+".dll"))
    
    return jtc, jtre

jtc, jtre = load_dlls(path = _PKG_PATH)

def dvc_open(dwDevice = 0, Errors = {}, out = "dwDevice,Errors", verbosity = 1):
    """
    Open device.
    
    Args:
        :dwDevice:
            | Device handle (class ctypes) or int.
        :Errors:
            | Dict with error messages.
        :out:
            | "dwDevice, Errors", optional
            | Requested return.
        :verbosity:
            | 1, optional
            | 0: no printed error message output.
    
    Returns:
        :dwDevice:
            | Device handle (class ctypes), if succesfull open (_ERROR: failure, nan: closed)
        :Errors:
            | Dict with error messages.
    """
    out = out.replace(' ','')
    try:
        Errors["OpenDevice"] = None
        
        # Initialize device :
        if isinstance(dwDevice, int):
                    
            # Get number of connected JETI devices (stored in dwDevice):
            NumDevices, Errors = dvc_detect(Errors=Errors, out = "NumDevices,Errors", verbosity = verbosity)
            
            if NumDevices > 0:
            
                # Open device:
                dvc_nr = dwDevice
                dwDevice = DWORD_PTR(DWORD(dwDevice))
                dwError = jtc.JETI_OpenDevice(dvc_nr, ctypes.byref(dwDevice))
                Errors["OpenDevice"] = dwError
                if (dwError != 0):
                    if verbosity == 1:
                        print("Could not connect to device. Error code = {}".format(dwError))
                    dwDevice, Errors = dvc_close(dwDevice, Errors = Errors, close_device = True, out = "dwDevice,Errors", verbosity = verbosity)
            else:
                raise Exception('dvc_open(): No devices detected!')
                dwDevice = np.nan
        else: # already open
            Errors["OpenDevice"] = 0
            dvc_nr = dwDevice
    except:
            Errors["OpenDevice"] = "dvc_open() fails."
            dwDevice = dvc_nr # return whatever the orginal input was.
    finally:    
        if out == "dwDevice,Errors":
            return dwDevice, Errors
        elif out == "dwDevice":
            return dwDevice
        elif out == "Errors":
            return Errors
        else:
            raise Exception("Requested output error.")

def dvc_close(dwDevice, Errors = {}, close_device = True, out = "dwDevice,Errors", verbosity = 1):
    """
    Close device.
    
    Args:
        :dwDevice:
            | Device handle (class ctypes) or int.
        :Errors:
            | Dict with error messages.
        close_device:
            | True: try and close device.
            | False: Do nothing.
        :out:
            | "dwDevice, Errors", optional
            | Requested return.
        :verbosity:
            | 1, optional
            | 0: no printed error message output.
    
    Returns:
        :dwDevice,Errors:
            | Device handle (_ERROR: failure; nan: closed; class ctype if dwDevice was opened and close_device == False)
        :Errors:
            | Dict with error messages.
    """
    Errors["CloseDevice"] = None
    out = out.replace(' ','')
    try:
        if _check_dwDevice_open(dwDevice) & (close_device == True):
            dwError = jtc.JETI_CloseDevice(dwDevice)
            Errors["CloseDevice"] = dwError
            dwDevice = np.nan # nan signifies closed device
            if (dwError != 0):
                dwDevice = _ERROR
                if verbosity == 1:
                    print("Could not close JETI device.")
        else:
            Errors["CloseDevice"] = 0
    except:
        Errors["CloseDevice"] = "dvc_close() failed."
    finally:
        if out == "dwDevice,Errors":
            return dwDevice, Errors
        elif out == "dwDevice":
            return dwDevice
        elif out == "Errors":
            return Errors
        else:
            raise Exception("Requested output error.")

def dvc_detect(Errors={}, out = "NumDevices,Errors", verbosity = 1):
    """
    Detect number of connected JETI devices.
    
    Args:
        :Errors:
            | Dict with error messages.
        :out:
            | "NumDevices,Errors", optional
            | Requested return.
        :verbosity:
            | 1, optional
            | 0: no printed error message output.
    
    Returns:
        :NumDevices:
            | Int with number of detected JETI devices.
        :Errors:
            | Dict with error messages.
    """
    out = out.replace(' ','')
    try:
        Errors["GetNumDevices"] = None
        dwNumDevices = DWORD(0) # Number of connected devices
        dwError = jtc.JETI_GetNumDevices(ctypes.byref(dwNumDevices))
        Errors["GetNumDevices"] = dwError
        NumDevices = dwNumDevices.value
        if ((dwError != 0)  | (NumDevices == 0)):
            if verbosity == 1:
                print("No connected JETI devices.")
    except:
        Errors["GetNumDevices"] = "dvc_detect() failed."
    finally:
        if out == "NumDevices,Errors":
            return NumDevices, Errors
        elif out == "NumDevices":
            return NumDevices
        elif out == "Errors":
            return Errors
        else:
            raise Exception("Requested output error.")


def start_meas(dwDevice, Tint = 0.0, autoTint_max = _TINT_MAX, Nscans = 1, wlstep = 1, Errors = {}, out = "Tint,Errors", verbosity = 1):
    """
    Start measurement on already opened device.
    
    Args:
        :dwDevice:
            | Device handle (of class ctypes).
        :Tint:
            | 0 or Float, optional
            | Integration time in seconds. (if 0: find best integration time).
        :autoTint_max:
            | Limit Tint to this value when Tint = 0.
        :Nscans:
            | 1 or Int, optional
            | Number of scans to average.
        :wlstep: 
            | 1 or Int, optional
            | Wavelength step size in nm.
        :out:
            | "Tint, Errors", optional
            | Requested return.
        :Errors:
            | Dict with error messages.
        :verbosity:
            | 1, optional
            | 0: no printed error message output.
    
    Returns:
        :Tint:
            | Integration time (limited to max possible time allowed by device)
        :Errors:
            | Dict with error messages.
    """
    out = out.replace(' ','')
    try:
        Errors["MeasureEx"] = None
        
        # Find minimum integration time for connected device and re-set global variable _TINT_MIN (to avoid having to call the function a second time for this device):
        global _TINT_MIN
        if _TINT_MIN is None:
            _TINT_MIN, Errors = get_min_integration_time(dwDevice, out = "MinTint,Errors", Errors = Errors, verbosity = verbosity)
            
        # Limit integration time to max value:
        Tint = _limit_Tint(Tint, Tint_min = _TINT_MIN, Tint_max = _TINT_MAX)
        autoTint_max = _limit_Tint(autoTint_max, Tint_min = _TINT_MIN, Tint_max = _TINT_MAX)
        
        # For automated Tint:
        if Tint == 0:
            MaxTint,Errors = get_max_auto_integration_time(dwDevice, out = "MaxTint,Errors", Errors = Errors, verbosity = verbosity)
            Errors = set_max_auto_integration_time(dwDevice, MaxTint = autoTint_max, out = "Errors", Errors = Errors, verbosity = verbosity)
          
        
        # Convert measurement parameters to ctypes:
        fTint = FLOAT(Tint*1000) # integration time (seconds -> milliseconds)
        wAver = WORD(np.int(Nscans)) # number of scans to average
        dwStep = DWORD(np.int(wlstep)) # wavelength step in nm
                            
        # Start measurement:
        dwError = jtre.JETI_MeasureEx(dwDevice, fTint, wAver, dwStep)
        Errors["MeasureEx"] = dwError
        if (dwError != 0):
            if (verbosity == 1):
                print("Could not start measurement. Error code = {}".format(dwError))
    except:
        Errors["MeasureEx"] = "start_meas() fails."
    finally:
        if out == "Tint,Errors":
            return Tint, Errors
        elif out == "Errors":
            return Errors
        elif out == "Tint":
            return Tint
        else:
            raise Exception("Requested output error.")

def check_meas_status(dwDevice, out = "status,Errors", Errors = {}, verbosity = 1):
    """
    Check status of initiated measurement.
    
    Args:
        :dwDevice:
            | Device handle (of class ctypes).
        :out:
            | "Tint, Errors", optional
            | Requested return.
        :Errors:
            | Dict with error messages.
        :verbosity:
            | 1, optional
            | 0: no printed error message output.
    
    Returns:
        :status:
            | Bool or _ERROR with status (True: meas. in progress, False: meas. finished, _ERROR: error)
        :Errors:
            | Dict with error messages.
    """
    out = out.replace(' ','')
    try:
        Errors["MeasureStatusEx"] = None
        boStatus = BOOL(True)
        dwError = jtre.JETI_MeasureStatusEx(dwDevice, ctypes.byref(boStatus))
        Errors["MeasureStatusEx"] = dwError
        if (dwError != 0):
            status = _ERROR
            if (verbosity == 1):
                print("Could not determine measurement status. Error code = {}".format(dwError))
        else:
            status = boStatus.value
    except:
        Errors["MeasureStatusEx"] = "check_meas_status() fails."
        status = _ERROR
    finally:
        if out == "status,Errors":
            return status, Errors
        elif out == "status":
            return status
        elif out == "Errors":
            return Errors
        else:
            raise Exception("Requested output error.")
        
     
def wait_until_meas_is_finished(dwDevice, Tint = None, twait = _TWAIT_STATUS, out = "status,Errors", Errors = {}, verbosity = 1):
    """
    Wait until measurement is finished.
    
    Args:
        :dwDevice:
            | Device handle (of class ctypes).
        :Tint:
            | 0 or Float, optional
            | Integration time in seconds. (if 0: find best integration time).
        :twait:
            | Time to wait (in seconds) between checking the measurement status. 
            | If twait == 0 & Tint > 0: set twait to Tint + _TWAIT_STATUS
            | If twait == 0 & Tint == 0: set twait to _TWAIT_STATUS
        :out:
            | "status,Errors", optional
            | Requested return.
        :Errors:
            | Dict with error messages.
        :verbosity:
            | 1, optional
            | 0: no printed error message output.
    
    Returns:
        :status:
            | Bool or _ERROR with status (True: meas. in progress, False: meas. finished, _ERROR: error)
        :Errors:
            | Dict with error messages.
    """
    out = out.replace(' ','')
    try:
        Errors["MeasureStatusEx"] = None
        if Tint is not None:
        # wait until measurement is finished (check intermediate status every twait seconds):
            if (twait == 0) & (Tint > 0):
                twait = Tint + _TWAIT_STATUS # + _TWAIT__STATUS to ensure measurement is really finished
            elif (twait == 0) & (Tint == 0):
                twait = _TWAIT_STATUS            
            
        status = True
        while status:
            time.sleep(twait)
            status, Error = check_meas_status(dwDevice, out = "status,Errors", Errors = Errors, verbosity = verbosity)
    except:
        Errors["MeasureStatusEx"] = "wait_until_meas_is_finished() fails."
        status = _ERROR
    finally:
        if out == "status,Errors":
            return status, Errors
        elif out == "status":
            return status
        elif out == "Errors":
            return Errors
        else:
            raise Exception("Requested output error.")
        
def read_spectral_radiance(dwDevice, wlstart = 360, wlend = 830, wlstep = 1, out = "spd,Errors", Errors = {}, verbosity = 1):
    """
    Read measured spectral radiance (W/m².sr.nm) from device.
    
    Args:
        :dwDevice:
            | Device handle (of class ctypes).
        :wlstart:
            | 360 or Int, optional
            | Start wavelength in nm. (min = 350 nm)
        :wlend:
            | 830 or Int, optional
            | Start wavelength in nm. (max = 1000 nm)
        :out:
            | "status,Errors", optional
            | Requested return.
        :Errors:
            | Dict with error messages.
        :verbosity:
            | 1, optional
            | 0: no printed error message output.
    
    Returns:
        :spd:
            | ndarray with wavelengths (1st row) and spectral radiance (2nd row; nan's if error).
        :Errors:
            | Dict with error messages.

    """
    out = out.replace(' ','')
    
    # Get wavelength range:
    wls = np.arange(np.int(wlstart), np.int(wlend)+np.int(wlstep), np.int(wlstep), dtype=np.float32)
    
    # Initialize spd filled with nan's:
    spd = np.vstack((wls, np.nan*np.ones(wls.shape)))
    
#    try:
    Errors["SpecRadEx"] = None
    
    # Convert measurement parameters to ctypes:
    dwBeg = DWORD(np.int(wlstart)) # wavelength start in nm
    dwEnd = DWORD(np.int(wlend)) # wavelength end in nm
    
    # create buffer for spectral radiance data:
    fSprad = (FLOAT * wls.shape[0])() 
    
    # get pointer to start of spectral radiance 
    dwError = jtre.JETI_SpecRadEx(dwDevice, dwBeg, dwEnd, ctypes.byref(fSprad)) 
    Errors["SpecRadEx"] = dwError
    if (dwError != 0):
        if (verbosity == 1):
            print("Could not read spectral radiance data from device. Error code = {}".format(dwError))
    else:
        # Read spectral radiance from buffer:
        Sprad= np.frombuffer(fSprad, np.float32)
            
        # Overwrite 2nd row of spd array with measured spectral radiance values:
        spd[1,:] = Sprad  
#    except:
#        Errors["SpecRadEx"] = "read_spectral_radiance() fails."
#    finally:
    # Generate requested return:
    if out == "spd,Errors":
        return spd, Errors
    elif out == "spd":
        return spd
    elif out == "Errors":
        return Errors
    else:
        raise Exception("Requested output error.")


def dvc_reset(dwDevice, Errors = {}, verbosity = 1):
    """
    Reset device. (same as disconnecting and reconnecting USB)
    
    Args:
        :dwDevice:
            | Device handle (class ctypes) or int.
        :Errors:
            | Dict with error messages.
        :verbosity:
            | 1, optional
            | 0: no printed error message output.
    
    Returns:
        :Errors:
            | Dict with error messages.
    """
    try:
        Errors["HardReset"] = None
        dwError = jtc.JETI_HardReset(dwDevice)
        Errors["HardReset"] = dwError
        if (dwError != 0):
            dwDevice = _ERROR
            if verbosity == 1:
                print("Could not do a hard reset of JETI device.")
    except:
        Errors["HardReset"] = "dvc_reset() fails."
    finally:
        return Errors

def set_default(dwDevice, out = "Errors", Errors = {}, verbosity = 1):
    """
    Set all measurement parameters to the default values.
    
    Args:
        :dwDevice:
            | Device handle (class ctypes) or int.
        :out:
            | "MaxTint,Errors", optional
            | Requested return.
        :Errors:
            | Dict with error messages.
        :verbosity:
            | 1, optional
            | 0: no printed error message output.
    
    Returns:
        :Errors:
            | Dict with error messages.
    """
    out = out.replace(' ','')
    
    try:
        Errors["SetDefault"] = None
        dwError = jtc.JETI_SetDefault(dwDevice)
        Errors["SetDefault"] = dwError
        if (dwError != 0):
            if verbosity == 1:
                print("Could not set the default parameter values.")
    except:
        Errors["SetDefault"] = "set_default() fails."
    finally:
        if out == "Errors":
            return Errors 
        else:
            raise Exception("Requested output error.")

def get_wavelength_params(dwDevice, out = "wlsFit,Errors", Errors = {}, verbosity = 1):
    """
    Get wavelength calibration parameters of polynomial of order 5.
    
    Args:
        :dwDevice:
            | Device handle (class ctypes) or int.
        :out:
            | "wlsFit,Errors", optional
            | Requested return.
        :Errors:
            | Dict with error messages.
        :verbosity:
            | 1, optional
            | 0: no printed error message output.
    
    Returns:
        :wlsFit:
            | ndarray with parameter values of wavelength calibration.
        :Errors:
            | Dict with error messages.
    """
    out = out.replace(' ','')
    wlsFit = np.nan*np.ones((5,),dtype=np.float32) # initialize parameter array with nan's
    try:
        Errors["GetFit"] = None
        
        # create and initialize buffer for polynomial parameters:
        fFit = (FLOAT * 5)(*[0,0,0,0,0]) 
        
        # get pointer to start of parameter array: 
        dwError = jtc.JETI_GetFit(dwDevice, ctypes.byref(fFit))
        Errors["GetFit"] = dwError
        if (dwError != 0):
            if verbosity == 1:
                print("Could not get the wavelength calibration parameters.")
        else:
            # Read parameters from buffer:
            wlsFit= np.frombuffer(fFit, np.float32)
    except:
        Errors["GetFit"] = "get_wavelength_params() fails."
    finally:
        if out == "wlsFit,Errors":
            return wlsFit,Errors
        elif out == "wlsFit":
            return wlsFit
        elif out == "Errors":
            return Errors
        else:
            raise Exception("Requested output error.")
    

def measure_flicker_freq(dwDevice, out = "flHz,warning,Errors", Errors = {}, verbosity = 1):
    """
    Measure flicker frequency (Hz).
    
    Args:
        :dwDevice:
            | Device handle (class ctypes) or int.
        :out:
            | "flHz,dwWarning,Errors", optional
            | Requested return.
        :Errors:
            | Dict with error messages.
        :verbosity:
            | 1, optional
            | 0: no printed error message output.
    
    Returns:
        :flHz:
            | Measured flicker frequency.
        :warning:
            |  0 – no warning; 11 – no modulation; 12 – fuzzy modulation
        :Errors:
            | Dict with error messages.
    """
    out = out.replace(' ','')
    try:
        warnings = {0: "no warning", 11: "no modulation", 12: "fuzzy modulation"}
        Errors["GetFlickerFreq"] = None
        fFlickerFreq = FLOAT(0.0)
        dwWarning = DWORD(0)
        dwError = jtc.JETI_GetFlickerFreq (dwDevice, ctypes.byref(fFlickerFreq), ctypes.byref(dwWarning))
        Errors["GetFlickerFreq"] = dwError
        if (dwError != 0):
            flHz = _ERROR
            warning = _ERROR
            if verbosity == 1:
                print("Could not measure the flicker frequency.")
        else:
            flHz = fFlickerFreq.value
            warning= warnings[dwWarning.value]
    except:
        Errors["GetFlickerFreq"] = "measure_flicker_freq() fails."
        flHz = _ERROR
        warning = _ERROR
    finally:
        if out == "flHz,warning,Errors":
            return flHz,warning,Errors
        elif out == "flHz,Errors":
            return flHz,Errors
        elif out == "flHz,warning":
            return flHz,warning
        elif out == "warning,Errors":
            return warning,Errors
        elif out == "flHz":
            return flHz
        elif out == "warning":
            return warning
        elif out == "Errors":
            return Errors
        else:
            raise Exception("Requested output error.")

def get_laser_status(dwDevice, out = "status,Errors", Errors = {}, verbosity = 1):
    """
    Get pilot laser status of device.
    
    Args:
        :dwDevice:
            | Device handle (class ctypes) or int.
        :out:
            | "status,Errors", optional
            | Requested return.
        :Errors:
            | Dict with error messages.
        :verbosity:
            | 1, optional
            | 0: no printed error message output.
    
    Returns:
        :status:
            | status of pilot laser (True: ON, False: OFF).
        :Errors:
            | Dict with error messages.
    """
    out = out.replace(' ','')
    try:
        Errors["GetLaserStat"] = None
        boLaserStat = BOOL(True)
        dwError = jtc.JETI_GetLaserStat(dwDevice, ctypes.byref(boLaserStat))
        Errors["GetLaserStat"] = dwError
        if (dwError != 0):
            status = _ERROR
            if verbosity == 1:
                print("Could not get the pilot laser status.")
        else:
            status = boLaserStat.value
    except:
        Errors["GetLaserStat"] = "get_laser_status() fails."
        status = _ERROR
    finally:
        if out == "status,Errors":
            return status,Errors
        elif out == "status":
            return status
        elif out == "Errors":
            return Errors
        else:
            raise Exception("Requested output error.")

def set_laser_status(dwDevice, status = False, out = "Errors", Errors = {}, verbosity = 1):
    """
    Set pilot laser status of device.
    
    Args:
        :dwDevice:
            | Device handle (class ctypes) or int.
        :status:
            | status of pilot laser (True: ON, False: OFF).
        :out:
            | "Errors", optional
            | Requested return.
        :Errors:
            | Dict with error messages.
        :verbosity:
            | 1, optional
            | 0: no printed error message output.
    
    Returns:
        :Errors:
            | Dict with error messages.
    """
    out = out.replace(' ','')
    try:
        Errors["SetLaserStat"] = None
        boLaserStat = BOOL(status)
        dwError = jtc.JETI_SetLaserStat(dwDevice, boLaserStat)
        Errors["SetLaserStat"] = dwError
        if (dwError != 0):
            if verbosity == 1:
                print("Could not set the pilot laser status.")
    except:
        Errors["SetLaserStat"] = "set_laser_status() fails."
    finally:
        if out == "Errors":
            return Errors
        else:
            raise Exception("Requested output error.")


def set_laser(dwDevice, laser_on = True, laser_intensity = 1000, Errors = {}, verbosity = 1):
    """
    Turn laser ON (3 modulation types: 7Hz (1), 28 Hz (2) and 255 Hz (3)) or OFF (0) and set laser intensity.
    
    Args:
        :dwDevice:
            | Device handle.
        :laser_on:
            | 0: OFF, >0: ON -> 1: PWM 7Hz, 2: PWM 28 Hz, 3: 255 Hz, optional
            | True (>0): turn laser on to select measurement area; False (0): turn off. 
            | (Can only be ON when "spd" is not in out.split(","))
        :laser_intensity: 
            | 1000.0, optional
            | Laser intensity in ‰ (pro-mille).
        :Errors:
            | Dict with error messages.
        :verbosity:
            | 1, optional
            | 0: no printed error message output.
    
    Returns:
        :Errors:
            | Dict with error messages.
    """
    try:
        Errors["SetLaserIntensity"] = None
        
        # Open device if not already opened!
        if not _check_dwDevice_open(dwDevice):
            dwDevice_was_open = False
            dwDevice, Errors = dvc_open(dwDevice = dwDevice, Errors = Errors, out = "dwDevice,Errors", verbosity = verbosity)    
        else:
            dwDevice_was_open = True
            
        # Set laser intensity and modulation:   
        if laser_intensity > 1000:
            laser_intensity = 1000
        if np.int(laser_on) not in [0,1,2,3]:
            laser_on = 3
        if (bool(laser_on) == True) & (_check_dwDevice_open(dwDevice)):
            dwError = jtc.JETI_SetLaserIntensity(dwDevice, DWORD(laser_intensity), DWORD(np.int(laser_on)))
            if dwError != 0:    
                if (verbosity == 1):
                    print("Could not set pilot laser intensity and/or modulation. Error code = {}".format(dwError))
            Errors["SetLaserIntensity"] = dwError
        elif (bool(laser_on) == False) & (_check_dwDevice_open(dwDevice)):
            dwError = jtc.JETI_SetLaserIntensity(dwDevice, DWORD(np.int(laser_intensity)), DWORD(0))
            if dwError != 0:    
                if (verbosity == 1):
                    print("Could not turn OFF pilot laser. Error code = {}".format(dwError))
            Errors["SetLaserIntensity"] = dwError
        
        # Toggle laser status:  
        Errors = set_laser_status(dwDevice, status = bool(laser_on), out = "Errors", Errors = Errors, verbosity = verbosity)

    except:
        Errors["SetLaserIntensity"] = "set_laser() fails."
    finally:
        dwDevice, Errors = dvc_close(dwDevice, Errors = Errors, close_device = (dwDevice_was_open == False), out = "dwDevice,Errors", verbosity = verbosity)
        return Errors

 
def get_calibration_range(dwDevice, out = "CalibRange,Errors", Errors = {}, verbosity = 1):
    """
    Get calibration range.
    
    Args:
        :dwDevice:
            | Device handle (class ctypes) or int.
        :out:
            | "Tint,Errors", optional
            | Requested return.
        :Errors:
            | Dict with error messages.
        :verbosity:
            | 1, optional
            | 0: no printed error message output.
    
    Returns:
        :CalibRange:
            | calibration wavelength range [start, end, step].
        :Errors:
            | Dict with error messages.
    """
    out = out.replace(' ','')
    try:
        Errors["GetCalibRange"] = None
        dwBegin = DWORD(0)
        dwEnd = DWORD(0)
        dwStep = DWORD(0)
        dwError = jtc.JETI_GetCalibRange(dwDevice, ctypes.byref(dwBegin),ctypes.byref(dwEnd), ctypes.byref(dwStep))
        Errors["GetCalibRange"] = dwError
        if (dwError != 0):
            CalibRange = [_ERROR]*3
            if verbosity == 1:
                print("Could not get the calibration wavelength range.")
        else:
            CalibRange = [dwBegin.value,dwEnd.value,dwStep.value]
    except:
        Errors["GetCalibRange"] = "get_calibration_range() fails."
        CalibRange = [_ERROR]*3
    finally:
        if out == "CalibRange,Errors":
            return CalibRange,Errors
        elif out == "CalibRange":
            return CalibRange
        elif out == "Errors":
            return Errors   
        else:
            raise Exception("Requested output error.")
  
def get_shutter_status(dwDevice, out = "status,Errors", Errors = {}, verbosity = 1):
    """
    Get shutter status of device.
    
    Args:
        :dwDevice:
            | Device handle (class ctypes) or int.
        :out:
            | "Errors", optional
            | Requested return.
        :Errors:
            | Dict with error messages.
        :verbosity:
            | 1, optional
            | 0: no printed error message output.
    
    Returns:
        :status:
            | status of shutter (True (1): OPEN, False (0): CLOSED).
        :Errors:
            | Dict with error messages.
    """
    out = out.replace(' ','')
    try:
        Errors["GetShutterStat"] = None
        boShutterStat = BOOL(0)
        dwError = jtc.JETI_GetLaserStat(dwDevice, ctypes.byref(boShutterStat))
        Errors["GetShutterStat"] = dwError
        if (dwError != 0):
            status = _ERROR
            if verbosity == 1:
                print("Could not get the shutter status.")
        else:
            status = boShutterStat.value
    except:
        Errors["GetShutterStat"] = "get_shutter_status() fails."
        status = _ERROR
    finally:
        if out == "status,Errors":
            return status,Errors
        elif out == "status":
            return status
        elif out == "Errors":
            return Errors
        else:
            raise Exception("Requested output error.")

def set_shutter_status(dwDevice, status = False, out = "Errors", Errors = {}, verbosity = 1):
    """
    Set shutter status of device.
    
    Args:
        :dwDevice:
            | Device handle (class ctypes) or int.
        :status:
            | status of shutter (True(1): OPEN, False(0): CLOSED).
        :out:
            | "Errors", optional
            | Requested return.
        :Errors:
            | Dict with error messages.
        :verbosity:
            | 1, optional
            | 0: no printed error message output.
    
    Returns:
        :Errors:
            | Dict with error messages.
    """
    out = out.replace(' ','')
    try:
        Errors["SetShutterStat"] = None
        boShutterStat = BOOL(status)
        dwError = jtc.JETI_SetLaserStat(dwDevice, boShutterStat)
        Errors["SetShutterStat"] = dwError
        if (dwError != 0):
            if verbosity == 1:
                print("Could not set the shutter status.")
    except:
        Errors["SetShutterStat"] = "set_shutter_status() fails."
    finally:
        if out == "Errors":
            return Errors
        else:
            raise Exception("Requested output error.")
   
def get_integration_time(dwDevice, out = "Tint,Errors", Errors = {}, verbosity = 1):
    """
    Get (default) integration time stored in device.
    
    Args:
        :dwDevice:
            | Device handle (class ctypes) or int.
        :out:
            | "Tint,Errors", optional
            | Requested return.
        :Errors:
            | Dict with error messages.
        :verbosity:
            | 1, optional
            | 0: no printed error message output.
    
    Returns:
        :Tint:
            | integration time stored in device.
        :Errors:
            | Dict with error messages.
    """
    out = out.replace(' ','')
    try:
        Errors["GetTint"] = None
        fTint = FLOAT(0.0)
        dwError = jtc.JETI_GetTint(dwDevice, ctypes.byref(fTint))
        Errors["GetTint"] = dwError
        if (dwError != 0):
            Tint = _ERROR
            if verbosity == 1:
                print("Could not get the integration time.")
        else:
            Tint = fTint.value / 1000 # in seconds
    except:
        Errors["GetTint"] = "get_integration_time() fails."
        Tint = _ERROR
    finally:
        if out == "Tint,Errors":
            return Tint,Errors
        elif out == "Tint":
            return Tint
        elif out == "Errors":
            return Errors
        else:
            raise Exception("Requested output error.")

def get_min_integration_time(dwDevice, out = "MinTint,Errors", Errors = {}, verbosity = 1):
    """
    Get the minimum integration time (seconds) which can be used with the connected device.
    
    Args:
        :dwDevice:
            | Device handle (class ctypes) or int.
        :out:
            | "MinTint,Errors", optional
            | Requested return.
        :Errors:
            | Dict with error messages.
        :verbosity:
            | 1, optional
            | 0: no printed error message output.
    
    Returns:
        :MinTint:
            | minimum integration time (seconds) which can be used with the connected device.
        :Errors:
            | Dict with error messages.
    """
    out = out.replace(' ','')
    try:
        Errors["GetMinTintConf"] = None
        fMinTint = FLOAT(0.0)
        dwError = jtc.JETI_GetMinTintConf(dwDevice, ctypes.byref(fMinTint))
        Errors["GetMinTintConf"] = dwError
        if (dwError != 0):
            MinTint = _ERROR
            if verbosity == 1:
                print("Could not get the minimum integration time.")
        else:
            MinTint = fMinTint.value / 1000 # in seconds
    except:
        Errors["GetMinTintConf"] = "get_min_integration_time() fails."
        MinTint = _ERROR
    finally:
        if out == "MinTint,Errors":
            return MinTint,Errors
        elif out == "MinTint":
            return MinTint
        elif out == "Errors":
            return Errors
        else:
            raise Exception("Requested output error.")

       
def get_max_auto_integration_time(dwDevice, out = "MaxTint,Errors", Errors = {}, verbosity = 1):
    """
    Get the maximum integration time which will be used for adaption (automated Tint selection).
    
    Args:
        :dwDevice:
            | Device handle (class ctypes) or int.
        :out:
            | "MaxTint,Errors", optional
            | Requested return.
        :Errors:
            | Dict with error messages.
        :verbosity:
            | 1, optional
            | 0: no printed error message output.
    
    Returns:
        :MaxTint:
            | maximum integration time which will be used for adaption (automated Tint selection).
        :Errors:
            | Dict with error messages.
    """
    out = out.replace(' ','')
    try:
        Errors["GetMaxTintConf"] = None
        fMaxTint = FLOAT(0.0)
        dwError = jtc.JETI_GetMaxTintConf(dwDevice, ctypes.byref(fMaxTint))
        Errors["GetMaxTintConf"] = dwError
        if (dwError != 0):
            MaxTint = _ERROR
            if verbosity == 1:
                print("Could not get the maximum (automated) integration time.")
        else:
            MaxTint = fMaxTint.value/1000 # in seconds
    except:
        Errors["GetMaxTintConf"] = "get_max_auto_integration_time() fails."
        MaxTint = _ERROR
    finally:
        if out == "MaxTint,Errors":
            return MaxTint,Errors
        elif out == "MaxTint":
            return MaxTint
        elif out == "Errors":
            return Errors
        else:
            raise Exception("Requested output error.")
        
    
def set_max_auto_integration_time(dwDevice, MaxTint = _TINT_MAX, out = "Errors", Errors = {}, verbosity = 1):
    """
    Set the maximum integration time which will be used for adaption (automated Tint selection).
    
    Args:
        :dwDevice:
            | Device handle (class ctypes) or int.
        :MaxTint:
            | maximum integration time which will be used for adaption (automated Tint selection).
        :out:
            | "MaxTint,Errors", optional
            | Requested return.
        :Errors:
            | Dict with error messages.
        :verbosity:
            | 1, optional
            | 0: no printed error message output.
    
    Returns:
        :Errors:
            | Dict with error messages.
    """
    out = out.replace(' ','')
    try:
        Errors["SetMaxTintConf"] = None
        fMaxTint = FLOAT(MaxTint*1000) # seconds -> milliseconds
        dwError = jtc.JETI_SetMaxTintConf(dwDevice, fMaxTint)
        Errors["SetMaxTintConf"] = dwError
        if (dwError != 0):
            if verbosity == 1:
                print("Could not set the maximum (automated) integration time.")
    except:
        Errors["SetMaxTintConf"] = "set_max_auto_integration_time() fails."
    finally:
        if out == "Errors":
            return Errors
        else:
            raise Exception("Requested output error.")
   
    
def _limit_Tint(Tint, Tint_min = _TINT_MIN, Tint_max = _TINT_MAX):
    """
    Limit the integration time to be between Tint_min and Tint_max (except when Tint = 0, i.e. automated Tint determination). 
    """
    if Tint_min is None:
        Tint_min = 0
    if Tint > 0:
        if Tint < Tint_min:
            Tint = Tint_min
        if Tint > Tint_max:
            Tint = Tint_max
    return Tint
    
def _check_dwDevice_open(dwDevice):
    """
    Check if device has been opened (dwDevice is of class 'ctypes'). Returns bool.
    """
    return ("ctypes" in str(type(dwDevice)))

    
    
def get_spd(Tint = 0.0, autoTint_max = _TINT_MAX, Nscans = 1, wlstep = 1, wlstart = 360, wlend = 830, 
           dwDevice = 0, twait = _TWAIT_STATUS, out = "spd", close_device = True, 
           laser_on = 0, laser_intensity = 1000, verbosity = 1):
    """
    Measure spectral radiance (W/nm.sr.m²).
    
    Args:
        :Tint:
            | 0 or Float, optional
            | Integration time in seconds. (if 0: find best integration time).
        :autoTint_max:
            | Limit Tint to this value when Tint = 0.
        :Nscans:
            | 1 or Int, optional
            | Number of scans to average.
        :wlstep: 
            | 1 or Int, optional
            | Wavelength step size in nm.
        :wlstart:
            | 360 or Int, optional
            | Start wavelength in nm. (min = 350 nm)
        :wlend:
            | 830 or Int, optional
            | Start wavelength in nm. (max = 1000 nm)
        :dwDevice:
            | 0 or Int or ctypes.wintypes.LP_c_ulong, optional
            | Number of spectrometer device to load (0 = 1st) or handle (ctypes) to pre_initialized device.
        :twait:
            | 0.1 or Float, optional
            | Time in seconds to wait before checking status of device. 
            | (If 0: wait :Tint: seconds, unless :Tint: == 0, then wait _TWAIT_STATUS seconds)
        :out:
            | "spd" [",dwDevice, Errors"], optional
            | Requested return. If "spd" in out.split(","):do spectral measurement, else: initialize dwDevice handle [and turn laser ON or OFF].
        :close_device:
            | True or False, optional
            | Close device at the end of the measurement.
            | If 'dwDevice' not in out.split(','): always close!!!
        :laser_on:
            | 0: OFF, >0: ON -> 1: PWM 7Hz, 2: PWM 28 Hz, 3: 255 Hz, optional
            | True (>0): turn laser on to select measurement area; False (0): turn off. 
            | (Can only be ON when "spd" is not in out.split(","))
        :laser_intensity: 
            | 1000.0, optional
            | Laser intensity in ‰ (pro-mille).
        :verbosity:
            | 1, optional
            | 0: no printed error message output.
    Returns:
        :returns: 
            | spd [,dwDevice, Errors] (as specified in :out:)
            | - "spd": ndarray with wavelengths (1st row) and spectral radiance (2nd row).
            | - "dwDevice": ctypes handle to device (if open) or nan (if closed).
            | - "Errors": dict with error message returned by device during various steps of the spectral measurement process.
    """
    # Initialize dict with errors messages for each of the different measurement steps:
    Errors = {} 
    Errors["get_spd"] = None
    Errors["GetNumDevices"] = None
    Errors["OpenDevice"] = None
    Errors["SetLaserIntensity"] = None
    Errors["MeasureEx"] = None
    Errors["MeasureStatusEx"] = None
    Errors["SpecRadEx"] = None
    Errors["CloseDevice"] = None
    out = out.replace(' ','')
    
    # Get wavelength range:
    wls = np.arange(np.int(wlstart), np.int(wlend)+np.int(wlstep), np.int(wlstep), dtype=np.float32)
    
    # Initialize spd filled with nan's:
    spd = np.vstack((wls, np.nan*np.ones(wls.shape)))

    try:
        # Initialize device :
        dwDevice, Errors = dvc_open(dwDevice = dwDevice, Errors = Errors, out = "dwDevice,Errors", verbosity = verbosity)    
        
        if (_check_dwDevice_open(dwDevice)) & ("spd" in out.split(",")):
            
            # Turn off laser before starting measurement:
            Errors = set_laser(dwDevice, laser_on = False, laser_intensity = laser_intensity, Errors = Errors, verbosity = verbosity)
                    
                            
            # Start measurement:
            Tint, Errors = start_meas(dwDevice, Tint = Tint, autoTint_max = autoTint_max, Nscans = Nscans, wlstep = wlstep, Errors = Errors, out = "Tint, Errors", verbosity = verbosity)
            
            # wait until measurement is finished (check intermediate status every twait seconds):
            status, Errors = wait_until_meas_is_finished(dwDevice, Tint = Tint, twait = twait, out = "status,Errors", Errors = Errors, verbosity = verbosity)
            
            if status == False:
                # Read measured spectral radiance from device:
                spd, Errors = read_spectral_radiance(dwDevice, wlstart = wlstart, wlend = wlend, wlstep = wlstep, out = "spd,Errors", Errors = Errors, verbosity = verbosity)    
            
            # Close device:
            dwDevice, Errors = dvc_close(dwDevice, Errors = Errors, close_device = close_device, out = "dwDevice,Errors", verbosity = verbosity)
        
        elif (_check_dwDevice_open(dwDevice)) & ("spd" not in out.split(",")): # only dwDevice handle was requested or to turn laser ON.
            Errors = set_laser(dwDevice, laser_on = laser_on, laser_intensity = laser_intensity, Errors = Errors, verbosity = verbosity)
        
        if np.isnan(dwDevice):
            Errors["get_spd"] = 0
        else:
            Errors["get_spd"] = "No open device."
        
    except:
        Errors["get_spd"] = "get_spd fails."
    finally:
        # Generate requested return:
        if out == "spd":
            return spd
        elif out == "dwDevice":
            return dwDevice
        elif out == "Errors":
            return Errors
        elif out == "spd,Errors":
            return spd, Errors
        elif out == "spd,dwDevice":
            return spd, dwDevice
        elif out == "spd,Errors,dwDevice":
            return spd, Errors, dwDevice
        elif out == "spd,dwDevice,Errors":
            return spd, dwDevice, Errors
        else:
            raise Exception("Requested output error.")



if __name__ == "__main__":   
    
    import luxpy as lx
    
    runtests = True
        
    if runtests == True:
    
        # Make a spectral radiance measurement:
        spd,dwDevice,Errors = get_spd(Tint = 0, autoTint_max = _TINT_MAX, Nscans = 1, wlstep = 1, wlstart = 360, wlend = 830,
                     dwDevice = 0, twait = _TWAIT_STATUS, out = "spd,dwDevice,Errors", close_device = True, 
                     laser_on = False, laser_intensity = 1000.0, verbosity = 1)
        
        # Print dwDevice and Errors:
        print("dwDevice: ",dwDevice)
        print("Errors: ",Errors)
        
        # Plot spd:
        lx.SPD(spd).plot(ylabel='Spectral radiance (W/nm.m².sr)')

    
    


