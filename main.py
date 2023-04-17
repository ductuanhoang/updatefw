
from usr import bluestone_config
from usr import bluestone_timer
from usr import bluestone_common
from usr import bluestone_mqtt

from machine import Pin
import _thread
import utime
import log
import ujson
import dataCall
import net
import modem
import checkNet
import ntptime
import _thread
from machine import WDT

from machine import UART
from machine import Timer
import ujson

PROJECT_NAME = "ICom-Charger"
PROJECT_VERSION = "1.0.1"
CHARGER_MAX_PORT = 12
TIME_OUT_DETECT_FULL_LOAD = 1
checknet = checkNet.CheckNetwork(PROJECT_NAME, PROJECT_VERSION)

# init gpio control relay
relay_1 = Pin(Pin.GPIO7, Pin.OUT, Pin.PULL_DISABLE, 0)
relay_2 = Pin(Pin.GPIO5, Pin.OUT, Pin.PULL_DISABLE, 0)
relay_3 = Pin(Pin.GPIO10 , Pin.OUT, Pin.PULL_DISABLE, 0)
relay_4 = Pin(Pin.GPIO21 , Pin.OUT, Pin.PULL_DISABLE, 0)
relay_5 = Pin(Pin.GPIO22 , Pin.OUT, Pin.PULL_DISABLE, 0)
relay_6 = Pin(Pin.GPIO23 , Pin.OUT, Pin.PULL_DISABLE, 0)
relay_7 = Pin(Pin.GPIO24 , Pin.OUT, Pin.PULL_DISABLE, 0)
relay_8 = Pin(Pin.GPIO16 , Pin.OUT, Pin.PULL_DISABLE, 0)
relay_9 = Pin(Pin.GPIO14 , Pin.OUT, Pin.PULL_DISABLE, 0)
relay_10 = Pin(Pin.GPIO13 , Pin.OUT, Pin.PULL_DISABLE, 0)
relay_11 = Pin(Pin.GPIO12 , Pin.OUT, Pin.PULL_DISABLE, 0)
relay_12 = Pin(Pin.GPIO11 , Pin.OUT, Pin.PULL_DISABLE, 0)

led_red =  Pin(Pin.GPIO17, Pin.OUT, Pin.PULL_DISABLE, 0)
led_green = Pin(Pin.GPIO18, Pin.OUT, Pin.PULL_DISABLE, 0)

bl0939_control_enable = Pin(Pin.GPIO9, Pin.OUT, Pin.PULL_DISABLE, 0)

##################################### UART #################################

I_Conversion     =     266013
V_Conversion     =     6960
W_Conversion     =     280.1 #713
CF_Conversion    =     0.000163

#ID of the BL
BL0939_ID_01 = b'\x50' # 0x5[A4,A3,A2,A1]
BL0939_ID_02 = b'\x51' # 0x5[A4,A3,A2,A1]
BL0939_ID_03 = b'\x52' # 0x5[A4,A3,A2,A1]
BL0939_ID_04 = b'\x53' # 0x5[A4,A3,A2,A1]
BL0939_ID_05 = b'\x54' # 0x5[A4,A3,A2,A1]
BL0939_ID_06 = b'\x55' # 0x5[A4,A3,A2,A1]

BL0939_READ_COMMAND_ID_01 = b'\x50\xAA' # 0x5[A4,A3,A2,A1]
BL0939_READ_COMMAND_ID_02 = b'\x51\xAA' # 0x5[A4,A3,A2,A1]
BL0939_READ_COMMAND_ID_03 = b'\x52\xAA' # 0x5[A4,A3,A2,A1]
BL0939_READ_COMMAND_ID_04 = b'\x53\xAA' # 0x5[A4,A3,A2,A1]
BL0939_READ_COMMAND_ID_05 = b'\x54\xAA' # 0x5[A4,A3,A2,A1]
BL0939_READ_COMMAND_ID_06 = b'\x55\xAA' # 0x5[A4,A3,A2,A1]

BL0939_FULL_PACKET = b'\xAA'
BL0939_PACKET_HEADER = b'\x55'
BL0939_WRITE_COMMAND = b'\xA5'  # 0xA[A4,A3,A2,A1]
BL0939_REG_IA_FAST_RMS_CTRL = b'\x10'
BL0939_REG_IB_FAST_RMS_CTRL = b'\x1E'
BL0939_REG_MODE = b'\x18'
BL0939_REG_SOFT_RESET = b'\x19'
BL0939_REG_USR_WRPROT = b'\x1A'
BL0939_REG_TPS_CTRL = b'\x1B'

BL0939_INIT = [
#     #  Reset to default
    [BL0939_WRITE_COMMAND, BL0939_REG_SOFT_RESET, b'\x5A\x5A\x5A\x33'],
#     #  Enable User Operation Write
    [BL0939_WRITE_COMMAND, BL0939_REG_USR_WRPROT, b'\x55\x00\x00\xEB'],
#     #  0x0100 = CF_UNABLE energy pulse, AC_FREQ_SEL 50Hz, RMS_UPDATE_SEL 800mS
    [BL0939_WRITE_COMMAND, BL0939_REG_MODE, b'\x00\x10\x00\x32'],
#     #  0x47FF = Over-current and leakage alarm on, Automatic temperature measurement, Interval 100mS
    [BL0939_WRITE_COMMAND, BL0939_REG_TPS_CTRL, b'\xFF\x47\x00\xF9'],
#     #  0x181C = Half cycle, Fast RMS threshold 6172
    [BL0939_WRITE_COMMAND, BL0939_REG_IA_FAST_RMS_CTRL, b'\x1C\x18\x00\x16'],
#     #  0x181C = Half cycle, Fast RMS threshold 6172
    [BL0939_WRITE_COMMAND, BL0939_REG_IB_FAST_RMS_CTRL, b'\x1C\x18\x00\x08']]

# icom logger
log.basicConfig(level=log.INFO)
uart_log = log.getLogger("Uart: ")

class IcomUart(object):
    def __init__(self, no=UART.UART2, bate=115200, data_bits=8, parity=0, stop_bits=1, flow_control=0):
        self.uart = UART(no, bate, data_bits, parity, stop_bits, flow_control)
        # self.uart.set_callback(self.callback)

    def uartWrite(self, msg):
        uart_log.info("write msg:{}".format(msg))
        self.uart.write(msg)
        self.uart.write("\r\n")

    def uartRead(self):
        # uart = UART(UART.UART1, self.baudrate, 8, 0, 1, 0)
        while 1:
            utime.sleep_us(1)  # 加个延时避免EC200U/EC600U运行重启
            msgLen = self.uart.any()
            if msgLen:
                msg = self.uart.read(msgLen)
                uart_log.info("UartRead with msg len: {}".format(msgLen))
            else:
                continue

    def uart_message(self, msg):
        return msg
    

################################# END OF UART #################################

##################################### BL09 #################################
class data_value(object):
    def __init__(self, Active, Voltage, Current, Power, PowerConsumption):
        self.active = Active
        self.Voltage = Voltage
        self.Current = Current
        self.Power = Power
        self.PowerConsumption = PowerConsumption
        self.ID = 0
        self.timeOut = 0
        self.expected_watt = 0

    def setDataValue(self, Voltage, Current, Power, PowerConsumption):
        self.Voltage = Voltage
        self.Current = Current
        self.Power = Power
        # self.PowerConsumption = PowerConsumption

    def calPowerConsumption(self, value):
        self.PowerConsumption = self.PowerConsumption + value
    
    def resetPowerConsumption(self):
        self.PowerConsumption = 0

    def setID(self, ID):
        self.ID = ID

    def setExpectedWatt(self, expected_watt):
        self.expected_watt = expected_watt

    def getExpectedWatt(self):
        return self.expected_watt

    def getDataValue(self):
        return self.ID, self.Voltage, self.Current, self.Power, self.PowerConsumption

    def getActive(self):
        return self.active
    
    def setActive(self,value):
        self.active = value

    def getTimeOutCount(self):
        return self.timeOut

    def increaseTimeOutCount(self):
        self.timeOut = self.timeOut + 1

    def resetTimeOutCount(self):
        self.timeOut = 0

port_01 = data_value(False, 0, 0, 0, 0)
port_02 = data_value(False, 0, 0, 0, 0)
port_03 = data_value(False, 0, 0, 0, 0)
port_04 = data_value(False, 0, 0, 0, 0)
port_05 = data_value(False, 0, 0, 0, 0)
port_06 = data_value(False, 0, 0, 0, 0)
port_07 = data_value(False, 0, 0, 0, 0)
port_08 = data_value(False, 0, 0, 0, 0)
port_09 = data_value(False, 0, 0, 0, 0)
port_10 = data_value(False, 0, 0, 0, 0)
port_11 = data_value(False, 0, 0, 0, 0)
port_12 = data_value(False, 0, 0, 0, 0)

power_test = 0

class IcomBL09(object):
    def __init__(self, power_state):
        self.power_state = power_state
        self.bl09Uart = IcomUart(UART.UART2, 4800, 8, 0, 2, 0)
        self.bl09Uart.uart.set_callback(self.Bl0939ParserMessage)
        self.command = 0
    def get_power_state(self):
        return self.power_state
    
    def set_power_state(self, power_state):
        self.power_state = power_state
    
    def Bl0939TurnOnOff(self, state):
        bl0939_control_enable.write(int(state))

    def Bl0939Thread(self):
        self.bl09Uart.uartRead()

    def Bl0939Send(self, data):
        self.bl09Uart.uartWrite(data)

    def Bl0939Initiate(self):
        self.Bl0939TurnOnOff(1)
    
    def Bl0939SetCommand(self, command):
        self.command = command
    def Bl0939GetCommand(self): 
        return self.command
    #     command1 = b'\xA5\x19\x5A\x5A\x5A\x33'
    #     #     #  Enable User Operation Write
    #     command2 = b'\xA5\x1A\x55\x00\x00\xEB'
    # #     #  0x0100 = CF_UNABLE energy pulse, AC_FREQ_SEL 50Hz, RMS_UPDATE_SEL 800mS
    #     command3 = b'\xA5\x18\x00\x10\x00\x32'
    # #     #  0x47FF = Over-current and leakage alarm on, Automatic temperature measurement, Interval 100mS
    #     command4 = b'\xA5\x1B\xFF\x47\x00\xF9'
    # #     #  0x181C = Half cycle, Fast RMS threshold 6172
    #     command5 = b'\xA5\x10\x1C\x18\x00\x16'
    # #     #  0x181C = Half cycle, Fast RMS threshold 6172
    #     command6 = b'\xA5\x1E\x1C\x18\x00\x08'
    #     self.bl09Uart.uartWrite(command1)
    #     utime.sleep(1)
    #     self.bl09Uart.uartWrite(command2)
    #     utime.sleep(1)
    #     self.bl09Uart.uartWrite(command3)
    #     utime.sleep(1)
    #     self.bl09Uart.uartWrite(command4)
    #     utime.sleep(1)
    #     self.bl09Uart.uartWrite(command5)
    #     utime.sleep(1)
    #     self.bl09Uart.uartWrite(command6)

    def Bl0939ParserMessage(self, para):
        if(0 == para[0]):
            message = self.bl09Uart.uart.read(para[2])
            if message[0] != BL0939_PACKET_HEADER:
                print("Reading port :" + str(self.Bl0939GetCommand()))
                tps1       = message[29] << 8 | message[28];   #TPS1        unsigned
                voltage    = message[12] << 16 | message[11] << 8 | message[10];    #V_RMS       unsigned
                energy_A   = message[24] << 16 | message[23] << 8 | message[22];    #CF_CNT[A]   unsigned
                energy_B   = message[27] << 16 | message[26] << 8 | message[25];    #CF_CNT[B]   unsigned
                current_A  = message[6]  << 16 | message[5]  << 8 | message[4];     #I_RMS[A]    unsigned
                current_B  = message[9]  << 16 | message[8]  << 8 | message[7];     #I_RMS[B]    unsigned
                power_A    = message[18] << 16 | message[17] << 8 | message[16];    #WATT[A]     signed
                power_B    = message[21] << 16 | message[20] << 8 | message[19];     # WATT[B]   signed

                voltage = voltage/V_Conversion
                current_A = current_A/I_Conversion
                current_B = current_B/I_Conversion
                power_A = power_A/W_Conversion
                power_B = power_B/W_Conversion
                energy_A = (energy_A * CF_Conversion)
                energy_B = (energy_B * CF_Conversion)

                userCommand.uartWrite("--------------------------------")
                userCommand.uartWrite("tps1 : {}".format(tps1))
                userCommand.uartWrite("voltage : {}".format(voltage))
                userCommand.uartWrite("energy_A : {}".format(energy_A))
                userCommand.uartWrite("energy_B : {}".format(energy_B))
                userCommand.uartWrite("current_A : {}".format(current_A))
                userCommand.uartWrite("current_B : {}".format(current_B))
                userCommand.uartWrite("power_A : {}".format(power_A))
                userCommand.uartWrite("power_B : {}".format(power_B))
                
                if self.Bl0939GetCommand() == 1:
                    if port_01.getActive() == True:
                        port_01.setDataValue(voltage, current_A, power_A, energy_A)
                        port_01.calPowerConsumption((current_A * voltage * 18) / 3600 / 1000)
                    if port_02.getActive() == True:
                        port_02.setDataValue(voltage, current_B, power_B, energy_B)
                        port_02.calPowerConsumption((current_A * voltage * 18) / 3600 / 1000)
                if self.Bl0939GetCommand() == 2:
                    if port_03.getActive() == True:
                        port_03.setDataValue(voltage, current_A, power_A, energy_A)
                        port_03.calPowerConsumption((current_A * voltage * 18) / 3600 / 1000)
                    if port_04.getActive() == True:
                        port_04.setDataValue(voltage, current_B, power_B, energy_B)
                        port_04.calPowerConsumption((current_A * voltage * 18) / 3600 / 1000)
                if self.Bl0939GetCommand() == 3:
                    if port_05.getActive() == True:
                        port_05.setDataValue(voltage, current_A, power_A, energy_A)
                        port_05.calPowerConsumption((current_A * voltage * 18) / 3600 / 1000)
                    if port_06.getActive() == True:
                        port_06.setDataValue(voltage, current_B, power_B, energy_B)
                        port_06.calPowerConsumption((current_A * voltage * 18) / 3600 / 1000)
                if self.Bl0939GetCommand() == 4:
                    if port_07.getActive() == True:
                        port_07.setDataValue(voltage, current_A, power_A, energy_A)
                        port_07.calPowerConsumption((current_A * voltage * 18) / 3600 / 1000)
                    if port_08.getActive() == True:
                        port_08.setDataValue(voltage, current_B, power_B, energy_B)
                        port_08.calPowerConsumption((current_A * voltage * 18) / 3600 / 1000)
                if self.Bl0939GetCommand() == 5:
                    if port_09.getActive() == True:
                        port_09.setDataValue(voltage, current_A, power_A, energy_A)
                        port_09.calPowerConsumption((current_A * voltage * 18) / 3600 / 1000)
                    if port_10.getActive() == True:
                        port_10.setDataValue(voltage, current_B, power_B, energy_B)
                        port_10.calPowerConsumption((current_A * voltage * 18) / 3600 / 1000)
                if self.Bl0939GetCommand() == 6:
                    if port_11.getActive() == True:
                        port_11.setDataValue(voltage, current_A, power_A, energy_A)
                        port_11.calPowerConsumption((current_A * voltage * 18) / 3600 / 1000)
                    if port_12.getActive() == True:
                        port_12.setDataValue(voltage, current_B, power_B, energy_B)
                        port_12.calPowerConsumption((current_A * voltage * 18) / 3600 / 1000)

    def B0939DebugPrint(self, tps1, voltage, energy_A, energy_B, current_A, current_B, power_A, power_B):
        uart_log.info("tps1 : {}".format(tps1))
        uart_log.info("voltage : {}".format(voltage/V_Conversion))
        uart_log.info("energy_A : {}".format(energy_A))
        uart_log.info("energy_B : {}".format(energy_B))
        uart_log.info("current_A : {}".format(current_A))
        uart_log.info("current_B : {}".format(current_B))
        uart_log.info("power_A : {}".format(power_A/W_Conversion))
        uart_log.info("power_B : {}".format(power_B/W_Conversion))
################################# END OF BL09 #################################

def parser_message_command(para):
        if(0 == para[0]):
            message = userCommand.uart.read(para[2])
            utf8_msg = message.decode(message)
            uart_log.info("call message:{}".format(utf8_msg))
            new_string= utf8_msg.split("/", 2)

            if new_string[0] == "1":
                uart_log.info("call message: 1")
                relay_1.write(int(new_string[1]))
            if new_string[0] == "2":
                uart_log.info("call message: 2")
                relay_2.write(int(new_string[1]))
            if new_string[0] == "3":
                uart_log.info("call message: 3")
                relay_3.write(int(new_string[1]))   
            if new_string[0] == "4":
                uart_log.info("call message: 4")
                relay_4.write(int(new_string[1]))
            if new_string[0] == "5":
                uart_log.info("call message: 5")
                relay_5.write(int(new_string[1]))
            if new_string[0] == "6":
                uart_log.info("call message: 6")
                relay_6.write(int(new_string[1]))
            if new_string[0] == "7":
                uart_log.info("call message: 7")
                relay_7.write(int(new_string[1]))
            if new_string[0] == "8":
                uart_log.info("call message: 8")
                relay_8.write(int(new_string[1]))
            if new_string[0] == "9":
                uart_log.info("call message: 9")
                relay_9.write(int(new_string[1]))
            if new_string[0] == "10":
                uart_log.info("call message: 10")
                relay_10.write(int(new_string[1]))
            if new_string[0] == "11":
                uart_log.info("call message: 11")
                relay_11.write(int(new_string[1]))
            if new_string[0] == "12":
                uart_log.info("call message: 12")
                relay_12.write(int(new_string[1]))
            if new_string[0] == "bl":
                uart_log.info("call turn on/off BL power")
                bl0939_control_enable.write(int(new_string[1]))


bs_config = None
device_MAC = None
state = 1
timer_name_list = ["timer0", "timer1", "timer2", "timer3"]
timer_list = [Timer.Timer0, Timer.Timer1, Timer.Timer2, Timer.Timer3]
timerID_0_job_name_list = []
timerID_0_job_name_list = []
is_timer_job_running = False
is_timer_job_report_running = False
count_state_machine = 1
heartbeat_time = 0

def send_device_info():
    global bs_data_config, bs_mqtt

    # 同步ntp时间
    ntptime.settime()

    data_config = "data_config 123"
    message = ujson.loads(data_config)
    main_log.info("Device configuration is {}".format(message))
    bs_mqtt.publish(message, "123")

################################# USER MQTT INIT #################################
def init_mqtt(config):
    global bs_config, bs_mqtt

    # mqtt_config = bs_config.read_config_by_name(config, 'mqtt')
    mqtt_config = bs_config.read_config_by_name(config, 'mqtt_icom')
    if mqtt_config is None:
        mqtt_config = {"client_id":"E3N2EXDG5Xbluestone001", "server":"m13.cloudmqtt.com","port":11734,"user":"wcewiofp","pwd":"TMnDUOEAKR8a","sub_topic":"/control","pub_topic":"/event"}
        main_log.info("No mqtt configuration file found")
        bs_config.update_config("mqtt", mqtt_config)    
    else:
        main_log.info("has mqtt configuration file")
        
    bs_mqtt = bluestone_mqtt.BluestoneMqtt( device_MAC,
                                            mqtt_config["client_id"], 
                                            mqtt_config["server"], 
                                            int(mqtt_config["port"]),
                                            mqtt_config["user"],
                                            mqtt_config["pwd"],
                                            mqtt_config["sub_topic_01"],
                                            mqtt_config["pub_topic_response"],
                                            mqtt_config["pub_topic_report"],
                                            mqtt_config["pub_topic_heartbeat"],
                                            mqtt_config["pub_topic_close"])
    bs_mqtt.start()

        # send_device_info()
    
    # except Exception as err:
    #     main_log.error("Cannot start mqtt proxy, the client_id is {}, please check the configuration".format(mqtt_config["client_id"]))
################################# END OF BL09 #################################

# icom logger
log.basicConfig(level=log.INFO)
main_log = log.getLogger("Main: ")

# function control relay numbers

# config UART configuration
# log.basicConfig(level=log.INFO)
# uart_log = log.getLogger("UART")
userCommand = IcomUart(UART.UART1, 9600)
userCommand.uart.set_callback(parser_message_command)
IcomBL09 = IcomBL09(1)

##################################### Thread #################################
def ThreadCommand():
    # 创建一个线程来监听接收uart消息
    main_log.info("Starting thread read UART command...")
    _thread.start_new_thread(userCommand.uartRead, ())

def ThreadBL0939():
    main_log.info("Starting thread read BL0939 ...")
    _thread.start_new_thread(IcomBL09.Bl0939Thread, ())
##################################### END Thread #################################

def start_one_job(args):
    global count_state_machine, timerID_1_job_name_list, bs_mqtt, bs_data_config, is_timer_job_running

    if is_timer_job_running:
        main_log.error("The timer job is running, skipping the new one")
        return
    
    is_timer_job_running = True

    
    if "bl09_com" in timerID_1_job_name_list:
        print("***** Running timer bl09_com")
        IcomBL09.Bl0939SetCommand(count_state_machine)
        if count_state_machine == 1:
            if port_01.getActive():
                IcomBL09.Bl0939Send(BL0939_READ_COMMAND_ID_01)
            elif port_02.getActive():
                IcomBL09.Bl0939Send(BL0939_READ_COMMAND_ID_01)
        elif count_state_machine ==  2:
            if port_03.getActive():
                IcomBL09.Bl0939Send(BL0939_READ_COMMAND_ID_02)
            elif port_04.getActive():
                IcomBL09.Bl0939Send(BL0939_READ_COMMAND_ID_02)
        elif count_state_machine ==  3:
            if port_05.getActive():
                IcomBL09.Bl0939Send(BL0939_READ_COMMAND_ID_03)
            elif port_06.getActive():
                IcomBL09.Bl0939Send(BL0939_READ_COMMAND_ID_03)
        elif count_state_machine ==  4:     
            if port_07.getActive():
                IcomBL09.Bl0939Send(BL0939_READ_COMMAND_ID_04)
            elif port_08.getActive():
                IcomBL09.Bl0939Send(BL0939_READ_COMMAND_ID_04)
        elif count_state_machine ==  5: 
            if port_09.getActive():
                IcomBL09.Bl0939Send(BL0939_READ_COMMAND_ID_05)
            elif port_10.getActive():
                IcomBL09.Bl0939Send(BL0939_READ_COMMAND_ID_05)
        elif count_state_machine == 6:
            if port_11.getActive():
                IcomBL09.Bl0939Send(BL0939_READ_COMMAND_ID_06)
            elif port_12.getActive():
                IcomBL09.Bl0939Send(BL0939_READ_COMMAND_ID_06)
        
        count_state_machine += 1
        if count_state_machine == 7:
            count_state_machine = 0
    
    # data_config = bs_data_config.read_config()
    # message = ujson.loads(data_config)
    # main_log.info("Data configuration is {}".format(message))
    # bs_mqtt.publish(message)

    # while True:
    #     is_message_published = bs_mqtt.is_message_published()
    #     if is_message_published:
    #         break
    #     utime.sleep_ms(300)
        
    is_timer_job_running = False

def start_job_report(args):
    global timerID_0_job_name_list, is_timer_job_report_running, heartbeat_time

    if is_timer_job_report_running:
        main_log.error("The timer job is running, skipping the new one")
        return
    
    is_timer_job_report_running = True
    if "report_message" in timerID_0_job_name_list:
        heartbeat_time = heartbeat_time + 1
        _reply_channel = "None"
        b_report_message = False
        print("***** Running timer report_message")
        if port_01.getActive():
            ID, Voltage,Current, Power, PowerConsumption = port_01.getDataValue()
            device_MAC
            message = bs_mqtt.messagePackageValue(device_MAC,1, ID, Voltage, Current, Power, PowerConsumption)
            if ((PowerConsumption * 1000) > port_01.getExpectedWatt()):
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "over_expected_watt")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_01.resetTimeOutCount()
                    port_01.resetPowerConsumption()
                    port_01.setActive(0)
                    relay_1.write(0) # off
            elif(Power < 5): # defalut less than 5W
                if( port_01.getTimeOutCount() < TIME_OUT_DETECT_FULL_LOAD):
                    bs_mqtt.publish(message, "report", _reply_channel)
                    port_01.increaseTimeOutCount()
                else:
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "full_load")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_01.resetTimeOutCount()
                    port_01.resetPowerConsumption()
                    port_01.setActive(0)
                    relay_1.write(0) # off
            else:
                bs_mqtt.publish(message, "report", _reply_channel)
            
            b_report_message = True
        if port_02.getActive():
            ID, Voltage,Current, Power, PowerConsumption = port_02.getDataValue()
            message = bs_mqtt.messagePackageValue(device_MAC,2, ID, Voltage, Current, Power, PowerConsumption)

            main_log.info("getTimeOutCount " + port_02.getTimeOutCount() + "Power " + Power)
            if ((PowerConsumption * 1000) > port_02.getExpectedWatt()):
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "over_expected_watt")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_02.resetTimeOutCount()
                    port_02.resetPowerConsumption()
                    port_02.setActive(0)
                    relay_2.write(0) # off
            elif(Power < 5): # defalut less than 5W
                if( port_02.getTimeOutCount() < TIME_OUT_DETECT_FULL_LOAD):
                    bs_mqtt.publish(message, "report", _reply_channel)
                    port_02.increaseTimeOutCount()
                else:
                    main_log.info("----- auto off port")
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "full_load")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_02.resetTimeOutCount()
                    port_02.setActive(0)
                    port_02.resetPowerConsumption() # reset power
                    relay_2.write(0) # off
            else:
                bs_mqtt.publish(message, "report", _reply_channel)

            b_report_message = True
        if port_03.getActive():
            ID, Voltage,Current, Power, PowerConsumption = port_03.getDataValue()
            message = bs_mqtt.messagePackageValue(device_MAC,3, ID, Voltage, Current, Power, PowerConsumption)
            if ((PowerConsumption * 1000) > port_03.getExpectedWatt()):
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "over_expected_watt")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_03.resetTimeOutCount()
                    port_03.resetPowerConsumption()
                    port_03.setActive(0)
                    relay_3.write(0) # off
            elif(Power < 5): # defalut less than 5W
                if( port_03.getTimeOutCount() < TIME_OUT_DETECT_FULL_LOAD):
                    bs_mqtt.publish(message, "report", _reply_channel)
                    port_03.increaseTimeOutCount()
                else:
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "full_load")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_03.resetTimeOutCount()
                    port_03.setActive(0)
                    port_03.resetPowerConsumption()
                    relay_3.write(0) # off
            else:
                bs_mqtt.publish(message, "report", _reply_channel)
            b_report_message = True
        if port_04.getActive():
            ID, Voltage,Current, Power, PowerConsumption = port_04.getDataValue()
            message = bs_mqtt.messagePackageValue(device_MAC,4, ID, Voltage, Current, Power, PowerConsumption)
            if ((PowerConsumption * 1000) > port_04.getExpectedWatt()):
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "over_expected_watt")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_04.resetTimeOutCount()
                    port_04.resetPowerConsumption()
                    port_04.setActive(0)
                    relay_4.write(0) # off
            elif(Power < 5): # defalut less than 5W
                if( port_04.getTimeOutCount() < TIME_OUT_DETECT_FULL_LOAD):
                    bs_mqtt.publish(message, "report", _reply_channel)
                    port_04.increaseTimeOutCount()
                else:
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "full_load")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_04.resetTimeOutCount()
                    port_04.setActive(0)
                    port_04.resetPowerConsumption()
                    relay_4.write(0) # off
            else:
                bs_mqtt.publish(message, "report", _reply_channel)
            b_report_message = True
        if port_05.getActive():
            ID, Voltage,Current, Power, PowerConsumption = port_05.getDataValue()
            message = bs_mqtt.messagePackageValue(device_MAC,5, ID, Voltage, Current, Power, PowerConsumption)
            if ((PowerConsumption * 1000) > port_05.getExpectedWatt()):
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "over_expected_watt")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_05.resetTimeOutCount()
                    port_05.resetPowerConsumption()
                    port_05.setActive(0)
                    relay_5.write(0) # off
            elif(Power < 5): # defalut less than 5W
                if( port_05.getTimeOutCount() < TIME_OUT_DETECT_FULL_LOAD):
                    bs_mqtt.publish(message, "report", _reply_channel)
                    port_05.increaseTimeOutCount()
                else:
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "full_load")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_05.resetTimeOutCount()
                    port_05.setActive(0)
                    port_05.resetPowerConsumption()
                    relay_5.write(0) # off
            else:
                bs_mqtt.publish(message, "report", _reply_channel)
            b_report_message = True
        if port_06.getActive():
            ID, Voltage,Current, Power, PowerConsumption = port_06.getDataValue()
            message = bs_mqtt.messagePackageValue(device_MAC,6, ID, Voltage, Current, Power, PowerConsumption)
            if ((PowerConsumption * 1000) > port_06.getExpectedWatt()):
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "over_expected_watt")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_06.resetTimeOutCount()
                    port_06.resetPowerConsumption()
                    port_06.setActive(0)
                    relay_6.write(0) # off
            elif(Power < 5): # defalut less than 5W
                if( port_06.getTimeOutCount() < TIME_OUT_DETECT_FULL_LOAD):
                    bs_mqtt.publish(message, "report", _reply_channel)
                    port_06.increaseTimeOutCount()
                else:
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "full_load")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_06.resetTimeOutCount()
                    port_06.setActive(0)
                    port_06.resetPowerConsumption()
                    relay_6.write(0) # off
            else:
                bs_mqtt.publish(message, "report", _reply_channel)
            b_report_message = True
        if port_07.getActive():
            ID, Voltage,Current, Power, PowerConsumption = port_07.getDataValue()
            message = bs_mqtt.messagePackageValue(device_MAC,7, ID, Voltage, Current, Power, PowerConsumption)
            if ((PowerConsumption * 1000) > port_07.getExpectedWatt()):
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "over_expected_watt")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_07.resetTimeOutCount()
                    port_07.resetPowerConsumption()
                    port_07.setActive(0)
                    relay_7.write(0) # off
            elif(Power < 5): # defalut less than 5W
                if( port_07.getTimeOutCount() < TIME_OUT_DETECT_FULL_LOAD):
                    bs_mqtt.publish(message, "report", _reply_channel)
                    port_07.increaseTimeOutCount()
                else:
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "full_load")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_07.resetTimeOutCount()
                    port_07.setActive(0)
                    port_07.resetPowerConsumption()
                    relay_7.write(0) # off
            else:
                bs_mqtt.publish(message, "report", _reply_channel)
            b_report_message = True
        if port_08.getActive():
            ID, Voltage,Current, Power, PowerConsumption = port_08.getDataValue()
            message = bs_mqtt.messagePackageValue(device_MAC,8, ID, Voltage, Current, Power, PowerConsumption)
            if ((PowerConsumption * 1000) > port_08.getExpectedWatt()):
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "over_expected_watt")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_08.resetTimeOutCount()
                    port_08.resetPowerConsumption()
                    port_08.setActive(0)
                    relay_8.write(0) # off
            elif(Power < 5): # defalut less than 5W
                if( port_08.getTimeOutCount() < TIME_OUT_DETECT_FULL_LOAD):
                    bs_mqtt.publish(message, "report", _reply_channel)
                    port_08.increaseTimeOutCount()
                else:
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "full_load")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_08.resetTimeOutCount()
                    port_08.setActive(0)
                    port_08.resetPowerConsumption()
                    relay_8.write(0) # off
            else:
                bs_mqtt.publish(message, "report", _reply_channel)
            b_report_message = True
        if port_09.getActive():
            ID, Voltage,Current, Power, PowerConsumption = port_09.getDataValue()
            message = bs_mqtt.messagePackageValue(device_MAC,9, ID, Voltage, Current, Power, PowerConsumption)
            if ((PowerConsumption * 1000) > port_09.getExpectedWatt()):
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "over_expected_watt")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_09.resetTimeOutCount()
                    port_09.resetPowerConsumption()
                    port_09.setActive(0)
                    relay_9.write(0) # off
            elif(Power < 5): # defalut less than 5W
                if( port_09.getTimeOutCount() < TIME_OUT_DETECT_FULL_LOAD):
                    bs_mqtt.publish(message, "report", _reply_channel)
                    port_09.increaseTimeOutCount()
                else:
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "full_load")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_09.resetTimeOutCount()
                    port_09.setActive(0)
                    port_09.resetPowerConsumption()
                    relay_9.write(0) # off
            else:
                bs_mqtt.publish(message, "report", _reply_channel)
            b_report_message = True
        if port_10.getActive():
            ID, Voltage,Current, Power, PowerConsumption = port_10.getDataValue()
            message = bs_mqtt.messagePackageValue(device_MAC,10, ID, Voltage, Current, Power, PowerConsumption)
            if ((PowerConsumption * 1000) > port_10.getExpectedWatt()):
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "over_expected_watt")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_10.resetTimeOutCount()
                    port_10.resetPowerConsumption()
                    port_10.setActive(0)
                    relay_10.write(0) # off
            elif(Power < 5): # defalut less than 5W
                if( port_10.getTimeOutCount() < TIME_OUT_DETECT_FULL_LOAD):
                    bs_mqtt.publish(message, "report", _reply_channel)
                    port_10.increaseTimeOutCount()
                else:
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "full_load")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_10.resetTimeOutCount()
                    port_10.setActive(0)
                    port_10.resetPowerConsumption()
                    relay_10.write(0) # off
            else:
                bs_mqtt.publish(message, "report", _reply_channel)
            b_report_message = True
        if port_11.getActive():
            ID, Voltage,Current, Power, PowerConsumption = port_11.getDataValue()
            message = bs_mqtt.messagePackageValue(device_MAC,11, ID, Voltage, Current, Power, PowerConsumption)
            if ((PowerConsumption * 1000) > port_11.getExpectedWatt()):
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "over_expected_watt")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_11.resetTimeOutCount()
                    port_11.resetPowerConsumption()
                    port_11.setActive(0)
                    relay_11.write(0) # off
            elif(Power < 5): # defalut less than 5W
                if( port_11.getTimeOutCount() < TIME_OUT_DETECT_FULL_LOAD):
                    bs_mqtt.publish(message, "report", _reply_channel)
                    port_11.increaseTimeOutCount()
                else:
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "full_load")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_11.resetTimeOutCount()
                    port_11.setActive(0)
                    port_11.resetPowerConsumption()
                    relay_11.write(0) # off
            else:
                bs_mqtt.publish(message, "report", _reply_channel)
            b_report_message = True
        if port_12.getActive():
            ID, Voltage,Current, Power, PowerConsumption = port_12.getDataValue()
            message = bs_mqtt.messagePackageValue(device_MAC,12, ID, Voltage, Current, Power, PowerConsumption)
            if ((PowerConsumption * 1000) > port_12.getExpectedWatt()):
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "over_expected_watt")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_12.resetTimeOutCount()
                    port_12.resetPowerConsumption()
                    port_12.setActive(0)
                    relay_12.write(0) # off
            elif(Power < 5): # defalut less than 5W
                if( port_12.getTimeOutCount() < TIME_OUT_DETECT_FULL_LOAD):
                    bs_mqtt.publish(message, "report", _reply_channel)
                    port_12.increaseTimeOutCount()
                else:
                    message = bs_mqtt.messagePackagePortCloseWithReason(device_MAC, port, ID, PowerConsumption, "full_load")
                    bs_mqtt.publish(message, "portclosed", _reply_channel)
                    port_12.resetTimeOutCount()
                    port_12.setActive(0)
                    port_12.resetPowerConsumption()
                    relay_12.write(0) # off
            else:
                bs_mqtt.publish(message, "report", _reply_channel)
            b_report_message = True
        
        if heartbeat_time >= 2:
            heartbeat_time = 0
            year, month, mday, hour, minute , second , weekday , yearday  = utime.localtime()

            # buffer = str(year) + ":" + str(month) + ":" + str(mday ) + " " + str(hour) + ":" + str(minute) + ":" + str(second)
            buffer = "%d-%02d-%02d %02d:%02d:%02d" % (year, month, mday, hour, minute, second)
            main_log.info("heartbeat time is " + buffer)
            message = bs_mqtt.messagePackageHeartBeat(device_MAC, buffer)
            bs_mqtt.publish(message, "heartbeat", _reply_channel)

    is_timer_job_report_running = False

def start_timer_job(timer_id, period, mode, func_name):
    global bs_timer
    print("start_timer_job " + str(timer_id))
    if timer_id == 2:
        bs_timer.start(timer_id, period, mode, start_job_report)
    elif timer_id == 1:
        bs_timer.start(timer_id, period, mode, start_one_job)

def stop_timer_job(timer_id):
    global bs_timer

    bs_timer.stop(timer_id)

def get_timer_by_name(name):
    index = timer_name_list.index(name)
    return timer_list[index]

def check_timer(config, timer_name):
    global bs_config, timerID_0_job_name_list, timerID_1_job_name_list

    timer_config = bs_config.read_config_by_name(config, timer_name)
    main_log.info("Timer {}'s config is {}".format(timer_name, ujson.dumps(timer_config)))
    if timer_config is not None:
        bs_config.update_config(timer_name, timer_config)
        job_status = bs_config.get_int_value(timer_config, "status")
        if job_status:
            timer_id = get_timer_by_name(timer_name)
            stop_timer_job(timer_id)

            period = bs_config.get_int_value(timer_config, "period")
            mode = bs_config.get_int_value(timer_config, "mode")
            callback = bs_config.get_value(timer_config, "callback")
            if callback:
                if timer_id == 2:
                    timerID_0_job_name_list = callback.split(',')
                    print("*** timer_job_name_list" , str(timerID_0_job_name_list))
                    start_timer_job(timer_id, period, mode, timerID_0_job_name_list)
                elif timer_id == 1:
                    timerID_1_job_name_list = callback.split(',')
                    print("*** timer_job_name_list" , str(timerID_1_job_name_list))
                    start_timer_job(timer_id, period, mode, timerID_1_job_name_list)

def init_timer(config):
    global bs_timer
    bs_timer = bluestone_timer.BluestoneTimer()

    # timer0 is reserved for WDT
    check_timer(config, 'timer2')
    check_timer(config, 'timer1')

def network_state_changed(args):
    global bs_mqtt

    pdp = args[0]
    state = args[1]
    if state == 1:
        main_log.info("Network %d connected!" % pdp)

        bs_mqtt.disconnect()
        utime.sleep_ms(1000)
        bs_mqtt.connect()

        # set network state to 1, 1 means normal
        bluestone_common.BluestoneCommon.set_network_state(1)
    else:
        main_log.error("Network %d not connected!" % pdp)

def check_network():
    while True:
        try:
            utime.sleep_ms(2000)
            #main_log.info("Check network connection")
            checknet.wait_network_connected()
            retry_count = 0
        except Exception as err:
            retry_count += 1
            main_log.error("Cannot connect to network, will retry it after {} millseconds for {} time".format(2000, retry_count))

            if retry_count >= 10:
                net.setModemFun(4) #进入飞行模式
                main_log.info("Enter airplane mode")
                utime.sleep_ms(2000)

                net.setModemFun(1)  #退出飞行模式
                main_log.info("Exit airplane mode")
                utime.sleep_ms(2000)
    #main_log.info("The network cannot be automatically recovered, restarting system to try again")
    #Power.powerRestart()

def start_network():
    '''
    如果程序包含网络相关代码，必须执行wait_network_connected() 等待网络就绪（拨号成功）；
    '''
    stagecode, subcode = checknet.wait_network_connected(30)
    if stagecode == 3 and subcode == 1:
        main_log.info('Network connection successful!')

    try:
        main_log.info("Check network connection")
        checknet.wait_network_connected()
        dataCall.setCallback(network_state_changed)
        _thread.start_new_thread(check_network, ())
    except Exception as err:
        _thread.start_new_thread(check_network, ())


def action_process_command(port, id, status, _reply_channel, _expected_watt):
    b_action_active = True
    buffer_id = id
    main_log.info("port: %s status: %s" % (port, status))
    if port == 1:
        if port_01.getActive() != status:            # turn on/off the port 
            relay_1.write(status)
            port_01.setActive(status)
            port_01.setID((id))
            port_01.setExpectedWatt(_expected_watt)
            if status == 0:
                ID, Voltage,Current, Power, PowerConsumption = port_01.getDataValue()
                message = bs_mqtt.messagePackagePortClose(device_MAC, port, id, PowerConsumption)
                bs_mqtt.publish(message, "portclosed", _reply_channel)
                port_01.resetPowerConsumption()
        else:
            b_action_active = False

    if port == 2:
        if port_02.getActive() != status:            # turn on/off the port 
            relay_2.write((status))
            port_02.setActive((status))
            port_02.setID((id))
            port_02.setExpectedWatt(_expected_watt)
            if status == 0:
                ID, Voltage,Current, Power, PowerConsumption = port_02.getDataValue()
                message = bs_mqtt.messagePackagePortClose(device_MAC, port, id, PowerConsumption)
                bs_mqtt.publish(message, "portclosed", _reply_channel)
                port_02.resetPowerConsumption()
        else:
            b_action_active = False
    if port == 3:
        if port_03.getActive() != status:            # turn on/off the port 
            relay_3.write((status))
            port_03.setActive((status))
            port_03.setID((id))
            port_03.setExpectedWatt(_expected_watt)
            if status == 0:
                ID, Voltage,Current, Power, PowerConsumption = port_03.getDataValue()
                message = bs_mqtt.messagePackagePortClose(device_MAC, port, id, PowerConsumption)
                bs_mqtt.publish(message, "portclosed", _reply_channel)
                port_03.resetPowerConsumption()
        else:
            b_action_active = False
    if port == 4:
        if port_04.getActive() != status:            # turn on/off the port 
            relay_4.write((status))
            port_04.setActive((status))
            port_04.setID((id))
            port_04.setExpectedWatt(_expected_watt)
            if status == 0:
                ID, Voltage,Current, Power, PowerConsumption = port_04.getDataValue()
                message = bs_mqtt.messagePackagePortClose(device_MAC, port, id, PowerConsumption)
                bs_mqtt.publish(message, "portclosed", _reply_channel)
                port_04.resetPowerConsumption()
        else:
            b_action_active = False
    if port == 5:
        if port_05.getActive() != status:            # turn on/off the port 
            relay_5.write((status))
            port_05.setActive((status))
            port_05.setID((id))
            port_05.setExpectedWatt(_expected_watt)
            if status == 0:
                ID, Voltage,Current, Power, PowerConsumption = port_05.getDataValue()
                message = bs_mqtt.messagePackagePortClose(device_MAC, port, id, PowerConsumption)
                bs_mqtt.publish(message, "portclosed", _reply_channel)
                port_05.resetPowerConsumption()
        else:
            b_action_active = False
    if port == 6:
        if port_06.getActive() != status:            # turn on/off the port 
            relay_6.write((status))
            port_06.setActive((status))
            port_06.setID((id))
            port_06.setExpectedWatt(_expected_watt)
            if status == 0:
                ID, Voltage,Current, Power, PowerConsumption = port_06.getDataValue()
                message = bs_mqtt.messagePackagePortClose(device_MAC, port, id, PowerConsumption)
                bs_mqtt.publish(message, "portclosed", _reply_channel)
                port_06.resetPowerConsumption()
        else:
            b_action_active = False
    if port == 7:
        if port_07.getActive() != status:            # turn on/off the port 
            relay_7.write((status))
            port_07.setActive((status))
            port_07.setID((id))
            port_07.setExpectedWatt(_expected_watt)
            if status == 0:

                ID, Voltage,Current, Power, PowerConsumption = port_07.getDataValue()
                message = bs_mqtt.messagePackagePortClose(device_MAC, port, id, PowerConsumption)
                bs_mqtt.publish(message, "portclosed", _reply_channel)
                port_07.resetPowerConsumption()
        else:
            b_action_active = False
    if port == 8:
        if port_08.getActive() != status:            # turn on/off the port 
            relay_8.write((status))
            port_08.setActive((status))
            port_08.setID((id))
            port_08.setExpectedWatt(_expected_watt)
            if status == 0:
                ID, Voltage,Current, Power, PowerConsumption = port_08.getDataValue()
                message = bs_mqtt.messagePackagePortClose(device_MAC, port, id, PowerConsumption)
                bs_mqtt.publish(message, "portclosed", _reply_channel)
                port_08.resetPowerConsumption()
        else:
            b_action_active = False
    if port == 9:
        if port_09.getActive() != status:            # turn on/off the port 
            relay_9.write((status))
            port_09.setActive((status))
            port_09.setID((id))
            port_09.setExpectedWatt(_expected_watt)
            if status == 0:
                ID, Voltage,Current, Power, PowerConsumption = port_09.getDataValue()
                message = bs_mqtt.messagePackagePortClose(device_MAC, port, id, PowerConsumption)
                bs_mqtt.publish(message, "portclosed", _reply_channel)
                port_09.resetPowerConsumption()
        else:
            b_action_active = False
    if port == 10:
        if port_10.getActive() != status:            # turn on/off the port 
            relay_10.write((status))
            port_10.setActive((status))
            port_10.setID((id))
            port_10.setExpectedWatt(_expected_watt)
            if status == 0:
                ID, Voltage,Current, Power, PowerConsumption = port_10.getDataValue()
                message = bs_mqtt.messagePackagePortClose(device_MAC, port, id, PowerConsumption)
                bs_mqtt.publish(message, "portclosed", _reply_channel)
                port_10.resetPowerConsumption()
        else:
            b_action_active = False
    if port == 11:
        if port_11.getActive() != status:            # turn on/off the port 
            relay_11.write((status))
            port_11.setActive((status))
            port_11.setID((id))
            port_11.setExpectedWatt(_expected_watt)
            if status == 0:
                ID, Voltage,Current, Power, PowerConsumption = port_11.getDataValue()
                message = bs_mqtt.messagePackagePortClose(device_MAC, port, id, PowerConsumption)
                bs_mqtt.publish(message, "portclosed", _reply_channel)
                port_11.resetPowerConsumption()
        else:
            b_action_active = False
    if port == 12:
        if port_12.getActive() != status:            # turn on/off the port 
            relay_12.write((status))
            port_12.setActive((status))
            port_12.setID((id))
            port_12.setExpectedWatt(_expected_watt)
            if status == 0:
                ID, Voltage,Current, Power, PowerConsumption = port_12.getDataValue()
                message = bs_mqtt.messagePackagePortClose(device_MAC, port, id, PowerConsumption)
                bs_mqtt.publish(message, "portclosed", _reply_channel)
                port_12.resetPowerConsumption()
        else:
            b_action_active = False

    if b_action_active == False: # send a message rejecting
        message = bs_mqtt.messagePackageResponse(port, 1)
        bs_mqtt.publish(message, "response", _reply_channel)
    else: # send a message accepting
        message = bs_mqtt.messagePackageResponse(port, 0)
        bs_mqtt.publish(message, "response", _reply_channel)

def feed_dog(args):
    global wdt

    main_log.info("Feeding dog...")
    wdt.feed()

def init_wdt():
    global timer0, wdt
    wdt = WDT(30)

    period = 5000
    main_log.info("Feeding dog service is running per {} millseconds".format(period))

    timer0 = Timer(Timer.Timer0)
    timer0.start(period = period, mode = timer0.PERIODIC, callback = feed_dog)

if __name__ == "__main__":
    main_log.info("Starting main thread")
    utime.sleep(5)
    checknet.poweron_print_once()

    main_log.info("Init system configuration file")
    bs_config = bluestone_config.BluestoneConfig('bluestone_config.json')
    config = bs_config.init_config()

    start_network()

    ThreadCommand()
    ThreadBL0939()
    count = 0
    command = b'\x55\xAA'
    IcomBL09.Bl0939Initiate()
    device_name = bluestone_common.BluestoneCommon.get_sn()
    uart_log.info("call device_name:{}".format(device_name))

    device_config = bs_config.read_config_by_name(config, 'device_info')
    uart_log.info("MAC = " + str(device_config["MAC"]))
    device_MAC = str(device_config["MAC"])

    main_log.info("Init timer service")
    init_timer(config)

    main_log.info("Init tencent mqtt service")
    init_mqtt(config)
    
    main_log.info("Init wdt service")
    init_wdt()

    while 1:
        count+=1
        if(count > 500):
            if bs_mqtt.getTriggerMessageComming() == True:
                bs_mqtt.setTriggerMessageComming(False)
                port, ctID, status, reply_channel, expected_watt= bs_mqtt.getDataMessageComming()
                action_process_command(port, ctID, status, reply_channel, expected_watt)
            # main_log.info("Local, the time is {}".format(utime.localtime()))
            # IcomBL09.Bl0939Send(command)
            # data1 = bs_mqtt.messagePackageValue("report",1, "123124155", 220, 0.8, 60, 20)
            # bs_mqtt.publish(data1)
            count = 0
        utime.sleep_us(10)  # 加个延时避免EC200U/EC600U运行重启