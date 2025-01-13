# -*-coding:utf-8 -*-
'''
@Time    :   2024/06/26 18:30:20
@Author  :   Daniel Persaud
@Version :   1.2
@Contact :   da.persaud@mail.utoronto.ca
@Desc    :   this is a run script for running automated corrosion tests
'''

#%%
# IMPORT DEPENDENCIES------------------------------------------------------------------------------
import json
import os
import logging
from datetime import datetime
import sys
import time

from opentrons import opentronsClient

from ardu import Arduino

from biologic import connect, BANDWIDTH, I_RANGE, E_RANGE
from biologic.techniques.ocv import OCVTechnique, OCVParams
from biologic.techniques.peis import PEISTechnique, PEISParams, SweepMode
from biologic.techniques.ca import CATechnique, CAParams, CAStep
from biologic.techniques.cpp import CPPTechnique, CPPParams

import pandas as pd

# HELPER FUNCTIONS---------------------------------------------------------------------------------

# define helper functions to manage solution
def fillWell(opentronsClient,
             strLabwareName_from,
             strWellName_from,
             strOffsetStart_from,
             strPipetteName,
             strLabwareName_to,
             strWellName_to,
             strOffsetStart_to,
             intVolume: int,
             fltOffsetX_from: float = 0,
             fltOffsetY_from: float = 0,
             fltOffsetZ_from: float = 0,
             fltOffsetX_to: float = 0,
             fltOffsetY_to: float = 0,
             fltOffsetZ_to: float = 0,
             intMoveSpeed : int = 100
             ) -> None:
    '''
    function to manage solution in a well because the maximum volume the opentrons can move is 1000 uL
    
    Parameters
    ----------
    opentronsClient : opentronsClient
        instance of the opentronsClient class

    strLabwareName_from : str
        name of the labware to aspirate from

    strWellName_from : str
        name of the well to aspirate from

    strOffset_from : str
        offset to aspirate from
        options: 'bottom', 'center', 'top'

    strPipetteName : str
        name of the pipette to use

    strLabwareName_to : str
        name of the labware to dispense to

    strWellName_to : str
        name of the well to dispense to

    strOffset_to : str
        offset to dispense to
        options: 'bottom', 'center', 'top'  

    intVolume : int
        volume to transfer in uL    

    intMoveSpeed : int
        speed to move in mm/s
        default: 100
    '''
    
    # while the volume is greater than 1000 uL
    while intVolume > 1000:
        # move to the well to aspirate from
        opentronsClient.moveToWell(strLabwareName = strLabwareName_from,
                                   strWellName = strWellName_from,
                                   strPipetteName = strPipetteName,
                                   strOffsetStart = 'top',
                                   fltOffsetX = fltOffsetX_from,
                                   fltOffsetY = fltOffsetY_from,
                                   intSpeed = intMoveSpeed)
        
        # aspirate 1000 uL
        opentronsClient.aspirate(strLabwareName = strLabwareName_from,
                                 strWellName = strWellName_from,
                                 strPipetteName = strPipetteName,
                                 intVolume = 1000,
                                 strOffsetStart = strOffsetStart_from,
                                 fltOffsetX = fltOffsetX_from,
                                 fltOffsetY = fltOffsetY_from,
                                 fltOffsetZ = fltOffsetZ_from)
        
        # move to the well to dispense to
        opentronsClient.moveToWell(strLabwareName = strLabwareName_to,
                                   strWellName = strWellName_to,
                                   strPipetteName = strPipetteName,
                                   strOffsetStart = 'top',
                                   fltOffsetX = fltOffsetX_to,
                                   fltOffsetY = fltOffsetY_to,
                                   intSpeed = intMoveSpeed)
        
        # dispense 1000 uL
        opentronsClient.dispense(strLabwareName = strLabwareName_to,
                                 strWellName = strWellName_to,
                                 strPipetteName = strPipetteName,
                                 intVolume = 1000,
                                 strOffsetStart = strOffsetStart_to,
                                 fltOffsetX = fltOffsetX_to,
                                 fltOffsetY = fltOffsetY_to,
                                 fltOffsetZ = fltOffsetZ_to)
        
        # subtract 1000 uL from the volume
        intVolume -= 1000


    # move to the well to aspirate from
    opentronsClient.moveToWell(strLabwareName = strLabwareName_from,
                               strWellName = strWellName_from,
                               strPipetteName = strPipetteName,
                               strOffsetStart = 'top',
                               fltOffsetX = fltOffsetX_from,
                               fltOffsetY = fltOffsetY_from,
                               intSpeed = intMoveSpeed)
    
    # aspirate the remaining volume
    opentronsClient.aspirate(strLabwareName = strLabwareName_from,
                             strWellName = strWellName_from,
                             strPipetteName = strPipetteName,
                             intVolume = intVolume,
                             strOffsetStart = strOffsetStart_from,
                             fltOffsetX = fltOffsetX_from,
                             fltOffsetY = fltOffsetY_from,
                             fltOffsetZ = fltOffsetZ_from)
    
    # move to the well to dispense to
    opentronsClient.moveToWell(strLabwareName = strLabwareName_to,
                               strWellName = strWellName_to,
                               strPipetteName = strPipetteName,
                               strOffsetStart = 'top',
                               fltOffsetX = fltOffsetX_to,
                               fltOffsetY = fltOffsetY_to,
                               intSpeed = intMoveSpeed)
    
    # dispense the remaining volume
    opentronsClient.dispense(strLabwareName = strLabwareName_to,
                             strWellName = strWellName_to,
                             strPipetteName = strPipetteName,
                             intVolume = intVolume,
                             strOffsetStart = strOffsetStart_to,
                             fltOffsetX = fltOffsetX_to,
                             fltOffsetY = fltOffsetY_to,
                             fltOffsetZ = fltOffsetZ_to)
    
    return

# define helper function to wash electrode
def washElectrode(opentronsClient,
                  strLabwareName,
                  arduinoClient):
    '''
    function to wash electrode

    Parameters
    ----------
    opentronsClient : opentronsClient
        instance of the opentronsClient class

    strLabwareName : str
        name of the labware to wash electrode in

    intCycle : int
        number of cycles to wash electrode

    '''

    # fill wash station with Di water
    arduinoClient.dispense_ml(pump=4, volume=20)

    # move to wash station
    opentronsClient.moveToWell(strLabwareName = strLabwareName,
                               strWellName = 'A2',
                               strPipetteName = 'p1000_single_gen2',
                               strOffsetStart = 'top',
                               intSpeed = 50)

    # move to wash station
    opentronsClient.moveToWell(strLabwareName = strLabwareName,
                               strWellName = 'A2',
                               strPipetteName = 'p1000_single_gen2',
                               strOffsetStart = 'bottom',
                               fltOffsetY = -15,
                               fltOffsetZ = -10,
                               intSpeed = 50)
    
    arduinoClient.set_ultrasound_on(cartridge = 0, time = 30)

    # drain wash station
    arduinoClient.dispense_ml(pump=3, volume=20)
        
    return


#%%
# SETUP LOGGING------------------------------------------------------------------------------------

# get the path to the current directory
strWD = os.getcwd()
# get the name of this file
strLogFileName = os.path.basename(__file__)
# split the file name and the extension
strLogFileName = os.path.splitext(strLogFileName)[0]
# add .log to the file name
strLogFileName = strLogFileName + ".log"
# join the log file name to the current directory
strLogFilePath = os.path.join(strWD, strLogFileName)

# Initialize logging
logging.basicConfig(
    level = logging.DEBUG,                                                      # Can be changed to logging.INFO to see less
    format = "%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(strLogFilePath, mode="a"),
        logging.StreamHandler(sys.stdout),
    ],
)

#%%
# INITIALIZE EXPERIMENT----------------------------------------------------------------------------
robotIP = "100.67.86.197"
# initialize an the opentrons client
oc = opentronsClient(strRobotIP = robotIP)
# initialize an the arduino client
ac = Arduino()#arduino_search_string = "USB Serial")

# make a variable to store the well in the autodial cell to be used
strWell2Test_autodialCell = 'A2'

# make a variable to store the well in the test solution to be used
strWell2Test_vialRack = 'A1'

#%%
# SETUP OPENTRONS PLATFORM-------------------------------------------------------------------------

# -----LOAD OPENTRONS STANDARD LABWARE-----

    # -----LOAD OPENTRONS TIP RACK-----
# load opentrons tip rack in slot 1
strID_pipetteTipRack = oc.loadLabware(intSlot = 1,
                                      strLabwareName = 'opentrons_96_tiprack_1000ul')

# -----LOAD CUSTOM LABWARE-----

# get path to current directory
strCustomLabwarePath = os.getcwd()
# join "labware" folder to current directory
strCustomLabwarePath = os.path.join(strCustomLabwarePath, 'labware')

    # -----LOAD WASH STATION-----
# join "nis_2_wellplate_30000ul.json" to labware directory
strCustomLabwarePath_temp = os.path.join(strCustomLabwarePath, 'nis_2_wellplate_30000ul.json')
# read json file
with open(strCustomLabwarePath_temp) as f:
    dicCustomLabware_temp = json.load(f)
# load custom labware in slot 3
strID_washStation = oc.loadCustomLabware(dicLabware = dicCustomLabware_temp,
                                         intSlot = 3)

    # -----LOAD AUTODIAL CELL-----
# join "nis_1_autodial_cell_10000ul.json" to labware directory
strCustomLabwarePath_temp = os.path.join(strCustomLabwarePath, 'autodial_25_reservoir_4620ul.json')
# read json file
with open(strCustomLabwarePath_temp) as f:
    dicCustomLabware_temp = json.load(f)
# load custom labware in slot 4
strID_autodialCell = oc.loadCustomLabware(dicLabware = dicCustomLabware_temp,
                                          intSlot = 4)

    # -----LOAD 50ml BEAKERS-----
# join "tlg_1_reservoir_50000ul.json" to labware directory
strCustomLabwarePath_temp = os.path.join(strCustomLabwarePath, 'tlg_1_reservoir_50000ul.json')

# read json file
with open(strCustomLabwarePath_temp) as f:
    dicCustomLabware_temp = json.load(f)

strID_dIBeaker = oc.loadCustomLabware(dicLabware = dicCustomLabware_temp,
                                      intSlot = 5)

    # -----LOAD 25ml VIAL RACK-----
# join "nis_8_reservoir_25000ul.json" to labware directory
strCustomLabwarePath_temp = os.path.join(strCustomLabwarePath, 'nis_8_reservoir_25000ul.json')
# read json file
with open(strCustomLabwarePath_temp) as f:
    dicCustomLabware_temp = json.load(f)
# load custom labware in slot 7
strID_vialRack = oc.loadCustomLabware(dicLabware = dicCustomLabware_temp,
                                      intSlot = 7)

    # -----LOAD ELECTRODE TIP RACK-----
# join "nis_4_tiprack_1ul.json" to labware directory
strCustomLabwarePath_temp = os.path.join(strCustomLabwarePath, 'nistall_4_tiprack_1ul.json')

# read json file
with open(strCustomLabwarePath_temp) as f:
    dicCustomLabware_temp = json.load(f)

# load custom labware in slot 10
strID_electrodeTipRack = oc.loadCustomLabware(dicLabware = dicCustomLabware_temp,
                                              intSlot = 10)



# LOAD OPENTRONS STANDARD INSTRUMENTS--------------------------------------------------------------
# add pipette
oc.loadPipette(strPipetteName = 'p1000_single_gen2',
               strMount = 'right')

#%%
# MOVE OPENTRONS INSTRUMENTS-----------------------------------------------------------------------

# turn the lights on 
oc.lights(True)

# home robot
oc.homeRobot()

# -----USE OPENTRONS TO MOVE CORROSIVE SOLUTIONS-----
# move to pipette tip rack
oc.moveToWell(strLabwareName = strID_pipetteTipRack,
              strWellName = 'A1',
              strPipetteName = 'p1000_single_gen2',
              strOffsetStart = 'top',
              fltOffsetY = 1,
              intSpeed = 100)
# pick up pipette tip
oc.pickUpTip(strLabwareName = strID_pipetteTipRack,
             strPipetteName = 'p1000_single_gen2',
             strWellName = 'A1',
             fltOffsetY = 1)

fillWell(opentronsClient = oc,
         strLabwareName_from = strID_vialRack,
         strWellName_from = strWell2Test_vialRack,
         strOffsetStart_from = 'bottom',
         strPipetteName = 'p1000_single_gen2',
         strLabwareName_to = strID_autodialCell,
         strWellName_to = strWell2Test_autodialCell,
         strOffsetStart_to = 'center',
         intVolume = 400,
         fltOffsetX_from = 0,
         fltOffsetY_from = 0,
         fltOffsetZ_from = 2,
         fltOffsetX_to = -1,
         fltOffsetY_to = 0.5,
         fltOffsetZ_to = 0,
         intMoveSpeed = 100
         )


# move back to pipette tip rack
oc.moveToWell(strLabwareName = strID_pipetteTipRack,
              strWellName = 'A1',
              strPipetteName = 'p1000_single_gen2',
              strOffsetStart = 'top',
              fltOffsetY = 1,
              intSpeed = 100)
# drop pipette tip
oc.dropTip(strLabwareName = strID_pipetteTipRack,
           strPipetteName = 'p1000_single_gen2',
           strWellName = 'A1',
           strOffsetStart = 'bottom',
           fltOffsetY = 1,
           fltOffsetZ = 7)

# move to the other tip in the pipette tip rack
oc.moveToWell(strLabwareName = strID_pipetteTipRack,
              strWellName = 'A12',
              strPipetteName = 'p1000_single_gen2',
              strOffsetStart = 'top',
              fltOffsetY = 1,
              intSpeed = 100)
# pick up pipette tip
oc.pickUpTip(strLabwareName = strID_pipetteTipRack,
             strPipetteName = 'p1000_single_gen2',
             strWellName = 'A12',
             fltOffsetY = 1)

fillWell(opentronsClient = oc,
         strLabwareName_from = strID_dIBeaker,
         strWellName_from = 'A1',
         strOffsetStart_from = 'bottom',
         strPipetteName = 'p1000_single_gen2',
         strLabwareName_to = strID_autodialCell,
         strWellName_to = strWell2Test_autodialCell,
         strOffsetStart_to = 'center',
         intVolume = 3600,
         fltOffsetX_from = 0,
         fltOffsetY_from = 0,
         fltOffsetZ_from = 2,
         fltOffsetX_to = -1,
         fltOffsetY_to = 0.5,
         fltOffsetZ_to = 0,
         intMoveSpeed = 100
         )

# move to the other tip in the pipette tip rack
oc.moveToWell(strLabwareName = strID_pipetteTipRack,
              strWellName = 'A12',
              strPipetteName = 'p1000_single_gen2',
              strOffsetStart = 'top',
              fltOffsetY = 1,
              intSpeed = 100)
# drop pipette tip
oc.dropTip(strLabwareName = strID_pipetteTipRack,
           strPipetteName = 'p1000_single_gen2',
           strWellName = 'A12',
           strOffsetStart = 'bottom',
           fltOffsetY = 1,
           fltOffsetZ = 7)



# -----USE OPENTRONS TO MOVE ELECTRODES-----

# move to electrode tip rack
oc.moveToWell(strLabwareName = strID_electrodeTipRack,
              strWellName = 'A2',
              strPipetteName = 'p1000_single_gen2',
              strOffsetStart = 'top',
              fltOffsetX = 0.6,
              fltOffsetY = 0.5,
              fltOffsetZ = 3,
              intSpeed = 100)
# pick up electrode tip
oc.pickUpTip(strLabwareName = strID_electrodeTipRack,
             strPipetteName = 'p1000_single_gen2',
             strWellName = 'A2',
             fltOffsetX = 0.6,
             fltOffsetY = 0.5)
# move to autodial cell                                        *** NEED TO ADDRESS THIS POSITION ***
oc.moveToWell(strLabwareName = strID_autodialCell,
              strWellName = strWell2Test_autodialCell,
              strPipetteName = 'p1000_single_gen2',
              strOffsetStart = 'top',
              fltOffsetX = 0.5,
              fltOffsetY = 0.5,
              fltOffsetZ = -25,
              intSpeed = 50)

#%%
# RUN ELECTROCHEMICAL EXPERIMENT-------------------------------------------------------------------

# -----PEIS-----
# create PEIS parameters
peisParams = PEISParams(
    vs_initial = False,
    initial_voltage_step = 0.0,
    duration_step = 3,
    record_every_dT = 0.5,
    record_every_dI = 0.01,
    final_frequency = 0.1,
    initial_frequency = 100000,
    sweep = SweepMode.Logarithmic,
    amplitude_voltage = 0.01,
    frequency_number = 60,
    average_n_times = 3,
    correction = False,
    wait_for_steady = 0.1,
    bandwidth = BANDWIDTH.BW_7,
    E_range = E_RANGE.E_RANGE_10V,
    )

# create PEIS technique
peisTech = PEISTechnique(peisParams)

# initialize an empty list to store the results
peisResults = []

# -----OCV-----
# create OCV parameters
ocvParams = OCVParams(
    rest_time_T = 300,
    record_every_dT = 0.5,
    record_every_dI = 0.01,
    E_range = E_RANGE.E_RANGE_10V,
    bandwidth = BANDWIDTH.BW_7,
    )

# create OCV technique
ocvTech = OCVTechnique(ocvParams)

# initialize an empty list to store the results
ocvResults = []

# -----CA-----
# make the only CA step
caStep = CAStep(
    voltage = -1.0,
    duration = 300,
    vs_initial = False
    )


# create CA parameters
caParams = CAParams(
    record_every_dT = 0.5,
    record_every_dI = 0.01,
    n_cycles = 0,
    steps = [caStep],
    I_range = I_RANGE.I_RANGE_10mA,
    )

# create CA technique
caTech = CATechnique(caParams)

# initialize an empty list to store the results
caResults = []

# ----CPP-----
# create CPP parameters
cppParams = CPPParams(
    record_every_dEr = 0.01,
    rest_time_T = 300,
    record_every_dTr = 0.5,
    vs_initial_scan = (True,True,True),
    voltage_scan = (-0.25, 1.5, -0.25),
    scan_rate = (0.01, 0.01, 0.01),
    I_pitting = 0.01,
    t_b = 10,
    record_every_dE = 0.01,                 # record every 0.167mv/s
    average_over_dE = False,
    begin_measuring_I = 0.75,
    end_measuring_I = 1.0,
    record_every_dT = 0.5,
    I_RANGE = I_RANGE.I_RANGE_10mA,)

# create CPP technique
cppTech = CPPTechnique(cppParams)

# initialize an empty list to store the results
cppResults = []


# run all techniques
with connect('USB0', force_load = True) as bl:
    channel = bl.get_channel(1)

    # get the current time
    strTime_start = datetime.now().strftime("%Y%m%d%H%M%S")

    # run the PEIS technique
    peisRunner = channel.run_techniques([peisTech])
    for result_temp in peisRunner:
        try:
            peisResults.append(result_temp.data)
            # log 
            logging.info(peisResults.data)
        except:
            time.sleep(0.5)
    else:
        time.sleep(1)

    # make the results a dataframe
    dfResults_peis = pd.DataFrame(peisResults)
    dfResults_peis.to_csv("peis" + strTime_start + ".csv")

    # run the OCV technique
    ocvRunner = channel.run_techniques([ocvTech])
    for result_temp in ocvRunner:
        try:
            ocvResults.append(result_temp.data)
            # log 
            logging.info(ocvResults.data)
        except:
            time.sleep(0.5)
    else:
        time.sleep(1)

    # make the results a dataframe
    dfResults_ocv = pd.DataFrame(ocvResults)
    dfResults_ocv.to_csv("ocv" + strTime_start + ".csv")

    # run the CA technique
    caRunner = channel.run_techniques([caTech])
    for result_temp in caRunner:
        try:
            caResults.append(result_temp.data)
            # log 
            logging.info(caResults.data)
        except:
            time.sleep(0.5)
    else:
        time.sleep(1)

    # make the results a dataframe
    dfResults_ca = pd.DataFrame(caResults)
    dfResults_ca.to_csv("ca" + strTime_start + ".csv")

    # run the CPP technique
    cppRunner = channel.run_techniques([cppTech])
    for result_temp in cppRunner:
        try:
            cppResults.append(result_temp.data)
            # log 
            logging.info(cppResults.data)
        except:
            time.sleep(0.5)
    else:
        time.sleep(1)

    # make the results a dataframe
    dfResults_cpp = pd.DataFrame(cppResults)
    dfResults_cpp.to_csv("cpp" + strTime_start + ".csv")


# log the end of the experiment
logging.info("End of electrochemical experiment")



#%%
# USE OPENTRONS INSTRUMENTS AND ARDUINO TO CLEAN ELECTRODE-----------------------------------------

# wash electrode
washElectrode(opentronsClient = oc,
              strLabwareName = strID_washStation,
              arduinoClient = ac)

# move to electrode tip rack
oc.moveToWell(strLabwareName = strID_electrodeTipRack,
              strWellName = 'A2',
              strPipetteName = 'p1000_single_gen2',
              strOffsetStart = 'top',
              fltOffsetX = 0.6,
              fltOffsetY = 0.5,
              intSpeed = 50)

# drop electrode tip
oc.dropTip(strLabwareName = strID_electrodeTipRack,
               strPipetteName = 'p1000_single_gen2',
               strWellName = 'A2',
               fltOffsetX = 0.6,
               fltOffsetY = 0.5,
               fltOffsetZ = 7,
               strOffsetStart = "bottom")

# home robot
oc.homeRobot()
# turn the lights off
oc.lights(False)
