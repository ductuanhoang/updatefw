'''

File: bluestone_mqtt.py

Project: bluestone

Author: daniel dong

Email: dongzhenguo@lantsang.cn

Copyright 2021 - 2021 bluestone tech

'''

import net
import utime
import ujson
import log
import _thread

from misc import Power
from umqtt import MQTTClient

from usr import bluestone_config
from usr import bluestone_common
from usr import bluestone_fota
import dataCall

log.basicConfig(level = log.INFO)
_mqtt_log = log.getLogger("MQTT")

class BluestoneMqtt(object):
    inst = None

    def __init__(self, _MAC, client_id, server, port, user, password, sub_topic_01, _pub_topic_response, _pub_topic_report, _pub_topic_heartbeat, _pub_topic_closed):
        BluestoneMqtt.inst = self
        self.MAC = _MAC
        self.bs_config = None
        self.bs_gpio = None
        self.bs_pwm = None
        self.bs_fota = None
        self.bs_uart = None

        self.sn = bluestone_common.BluestoneCommon.get_sn()
        self.client_id = client_id
        self.server = server
        self.port = port
        self.user = user
        self.password = password

        self.subscribe_topic_01 = sub_topic_01 # subscribe topic

        self.pub_topic_response = _pub_topic_response # publish topic
        self.pub_topic_report = _pub_topic_report
        self.pub_topic_heartbeat = _pub_topic_heartbeat
        self.pub_topic_port_close = _pub_topic_closed

        self.client = None
        self._is_sub_callback_running = False
        self._is_message_published = False
        self.isMessageComming = False

        self.connectorID = 0
        self.transactionId = 0
        self.status = 0
        self.expected_watt = 0
        self.TaskEnable = True
        # 网络状态标志
        self.__nw_flag = True
        # 创建互斥锁
        self.connected = True
        self.mp_lock = _thread.allocate_lock()
    def _init_mqtt(self):
        self.bs_config = bluestone_config.BluestoneConfig('bluestone_config.json')
        self.bs_fota = bluestone_fota.BluestoneFOTA()
        self.connected = True
        # 创建一个MQTT实例
        self.client = MQTTClient(
            client_id = self.client_id,
            server = self.server,
            port = self.port,
            user = self.user,
            password = self.password,
            keepalive = 30)
        
        _mqtt_log.info("Start a new mqtt client, id:{}, server:{}, port:{}".format(self.client_id, self.server, self.port))

        # self.client.error_register_cb(self.err_cb_function)
        self.client.set_callback(self._sub_callback) # 设置消息回调
        try:
            self.client.connect() # 建立连接
        except Exception as err:
            self.connected = False
            print("connected is: error {}".format(err))
        #sub_topic = self.subscribe_topic.format(self.sn)
        if self.connected == False:
            utime.sleep_ms(5000)
            Power.powerRestart()
        else:
            _mqtt_log.info("Subscribe topic is {}".format(self.subscribe_topic_01))
            self.client.subscribe(self.subscribe_topic_01) # 订阅主题

    def err_cb_function(err):
        print("thread err:")
        print(err)

    def _handle_callback(self, key, config):
        result = False
        _mqtt_log.info("Got callback key : " + str(key))
        _mqtt_log.info("Got callback config: " + str(config))
        try:
            if key == 'fota':
                mode = self.bs_config.get_int_value(config, "mode")
                if mode == 0:
                    url_list = self.bs_config.get_value(config, "url")
                    url_list = url_list.split(',')
                    print("*** url_list" , (url_list))
                    self.bs_fota.start_fota_app(url_list)
                elif mode == 1:
                    url = self.bs_config.get_value(config, "url")
                    self.bs_fota.start_fota_firmware(url)
                result = True
        except Exception as err:
            _mqtt_log.error("Cannot handle callback for mqtt, the error is {}".format(err))
        
        return result

    def messageParseCtr(self, message):
        pythonObj = ujson.loads(message)
        print(type(pythonObj))

        if "fota" in pythonObj:
             _mqtt_log.info("OTA start")
             for key in pythonObj:
                config = pythonObj[key]
                result = self._handle_callback("fota", config)

        elif "port" in pythonObj and "ticket_id" in pythonObj and "status" in pythonObj and "reply_channel" in pythonObj and "expected_watt" in pythonObj:
            self.connectorID = pythonObj['port']
            self.transactionId = pythonObj['ticket_id']
            self.status = pythonObj['status']
            self.reply_channel = pythonObj['reply_channel']
            self.expected_watt = pythonObj['expected_watt']
            self.setTriggerMessageComming(True)


    
    def messageParserSettings(self, message):
        pythonObj = ujson.loads(message)
        print(type(pythonObj))

    def _sub_callback_internal(self, topic, msg):
        try:
            message = msg.decode()
            _mqtt_log.info("Subscribe received, topic={}, message={}".format(topic.decode(), message))
            restart = False
            if topic.decode() == self.subscribe_topic_01:
                print("message control")
                self.messageParseCtr(message)

        except Exception as err:
            _mqtt_log.error("Cannot handle subscribe callback for mqtt, the error is {}".format(err))
        finally:
            self._is_sub_callback_running = False

    # 云端消息响应回调函数
    def _sub_callback(self, topic, msg):
        if self._is_sub_callback_running:
            _mqtt_log.error("Subscribe callback function is running, skipping the new request")
            return

        self._is_sub_callback_running = True
        _thread.start_new_thread(self._sub_callback_internal, (topic, msg))

    def _mqtt_publish(self, message, _type, _reply_channel):
        #pub_topic = self.pub_topic_response.format(self.sn)
        #message = {"Config":{},"message":"MQTT hello from Bluestone"}
        _mqtt_log.info("MQTT publish message : %s -- %s", message, _type)
        if self.client is not None:
            if _type == 'response':
                _pub_topic_response = self.pub_topic_response
                _pub_topic_response = _pub_topic_response + str(_reply_channel)
                self.client.publish(_pub_topic_response, message)
                self._is_message_published = True
                _mqtt_log.info("Publish topic response is {}, message is {}".format(_pub_topic_response, message))
            elif _type == 'report':
                self.client.publish(self.pub_topic_report, message)
                self._is_message_published = True
                _mqtt_log.info("Publish topic report is {}, message is {}".format(self.pub_topic_report, message))
            elif _type == 'heartbeat':
                self.client.publish(self.pub_topic_heartbeat, message)
                self._is_message_published = True
                _mqtt_log.info("Publish topic heartbeat is {}, message is {}".format(self.pub_topic_heartbeat, message))
            elif _type == "portclosed":
                self.client.publish(self.pub_topic_port_close, message)
                self._is_message_published = True
                _mqtt_log.info("Publish topic heartbeat is {}, message is {}".format(self.pub_topic_port_close, message))
        else:
            _mqtt_log.info("self.client is None")

    def reconnect(self):
        _mqtt_log.info("mqtt client reconnect 1")
        # '''
        # mqtt 重连机制(该示例仅提供mqtt重连参考，根据实际情况调整)
        # PS：1.如有其他业务需要在mqtt重连后重新开启，请先考虑是否需要释放之前业务上的资源再进行业务重启
        #     2.该部分需要自己根据实际业务逻辑添加，此示例只包含mqtt重连后重新订阅Topic
        # '''
        # 判断锁是否已经被获取
        if self.mp_lock.locked():
            _mqtt_log.info("self.mp_lock.locked")
            return
        _mqtt_log.info("self.mp_lock.acquire")
        self.mp_lock.acquire()
        # 重新连接前关闭之前的连接，释放资源(注意区别disconnect方法，close只释放socket资源，disconnect包含mqtt线程等资源)
        self.client.close()
        _mqtt_log.info("mqtt client reconnect")
        self.client = MQTTClient(
            client_id = self.client_id,
            server = self.server,
            port = self.port,
            user = self.user,
            password = self.password,
            keepalive = 30)
        _mqtt_log.info("Start a re connect mqtt client, id:{}, server:{}, port:{}".format(self.client_id, self.server, self.port))

        # self.client.error_register_cb(self.err_cb_function)
        self.client.set_callback(self._sub_callback) # 设置消息回调
        try:
            self.client.connect() # 建立连接
        except Exception as err:
            self.connected = False
            print("connected is: error {}".format(err))
        
        if self.connected == False:
            utime.sleep_ms(5000)
            Power.powerRestart()
        else:
            _mqtt_log.info("Subscribe topic is {}".format(self.subscribe_topic_01))
            self.client.subscribe(self.subscribe_topic_01) # 订阅主题
        _mqtt_log.info("mqtt client reconnect call self.connect()")

        self.mp_lock.release()
        return True
    
    def nw_cb(self, args):
        '''
        dataCall 网络回调
        '''
        nw_sta = args[1]
        if nw_sta == 1:
            # 网络连接
            _mqtt_log.info("*** network connected! ***")
            self.__nw_flag = True
        else:
            # 网络断线
            _mqtt_log.info("*** network not connected! ***")
            self.__nw_flag = False

    def _wait_msg(self):
        while True:
            try:
                if not self.TaskEnable:
                    break
                self.client.wait_msg()
            except OSError as e:
                _mqtt_log.info("*** network connected! ***")
                # 判断网络是否断线
                if not self.__nw_flag:
                    # 网络断线等待恢复进行重连
                    self.reconnect()
                # 在socket状态异常情况下进行重连
                elif self.client.get_mqttsta() != 0 and self.TaskEnable:
                    self.reconnect()
                else:
                    # 这里可选择使用raise主动抛出异常或者返回-1
                    return -1

    def CheckMqttConnection(self):
        count = 0
        while True:
            count+=1
            if(count > 100):
                status = self.client.get_mqttsta()
                if status == 0:
                    _mqtt_log.error("the connection is successful")
                elif status == 1:
                    _mqtt_log.error("Connecting")
                elif status == 2:
                    _mqtt_log.error("The server connection is closed")
                    utime.sleep_ms(5000)
                    Power.powerRestart()
                elif status == -1:
                    _mqtt_log.error("connection exception")
                    self.reconnect()
                else :
                    _mqtt_log.error("unexpected status")
                count = 0
            utime.sleep_ms(50)  # 加个延时避免EC200U/EC600U运行重启

    def is_message_published(self):
        return self._is_message_published
        
    def start(self):
        self._init_mqtt()

        _thread.start_new_thread(self._wait_msg, ())
        _thread.start_new_thread(self.CheckMqttConnection, ())

    def publish(self, message, type, reply_channel):
        network_state = bluestone_common.BluestoneCommon.get_network_state()
        if network_state != 1:
            _mqtt_log.error("Cannot publish mqtt message, the network state is {}".format(network_state))
            return

        #_mqtt_log.info("Publish message is {}".format(message))
        #self._mqtt_publish(ujson.dumps(message))
        self._is_message_published = False
        _mqtt_log.info("Create a new thread publish message: ")
        _thread.start_new_thread(self._mqtt_publish, (ujson.dumps(message), type, reply_channel))      


    def connect(self):
        if self.client is not None:
            _mqtt_log.info("MQTT connect")
            self.client.connect()
            _mqtt_log.info("MQTT connected")
            flag = dataCall.setCallback(self.nw_cb)
            if flag != 0: # 回调注册失败
                raise Exception("Network callback registration failed")
        else:
            _mqtt_log.info("Client connection failed")

    def disconnect(self):
        if self.client is not None:
            self.TaskEnable = False
            self.client.disconnect()
            _mqtt_log.info("MQTT disconnected")

    def close(self):
        self.disconnect()
        self.client = None
        _mqtt_log.info("MQTT closed")
    
    def messagePackageValue(self, _deviceId, _port, __ticket_id, Voltage, Current, DeviceWatt, EnergyConsumption):
        header = {"device_id": _deviceId,"ticket_id": __ticket_id, "port": _port, "vol":Voltage, "current":Current, "device_watt": DeviceWatt, "total_watt": EnergyConsumption}
        # message_values = {"1":"{}","2":"{}", "3":"{}", "4":"{}"}
        # message_values["1"] = Voltage
        # message_values["2"] = Current
        # message_values["3"] = DeviceWatt
        # message_values["4"] = EnergyConsumption
        # header["metterValue"] = message_values
        return header
    
    def messagePackageHeartBeat(self, _deviceID, _time, _firmware_version):
        header = {"device_id": _deviceID,"request_at": _time, "firmware_version": _firmware_version}
        return header
    
    def messagePackageResponse(self, _port, _message_type):
        header = {"error": _message_type, "port": _port}
        return header

    def messagePackagePortClose(self, _deviceID, _port, _ticket_id, _total_watt, _replychannel):
        header = {"device_id": _deviceID,"port": _port, "ticket_id": _ticket_id, "total_watt": _total_watt, "reply_channel": _replychannel}
        return header

    def messagePackagePortCloseWithReason(self, _deviceID, _port, _ticket_id, _total_watt, _message, _replychannel):
        header = {"device_id": _deviceID,"port": _port, "ticket_id": _ticket_id, "total_watt": _total_watt, "reason":_message, "reply_channel": _replychannel}
        return header

    def getTriggerMessageComming(self):
        return self.isMessageComming
    
    def getDataMessageComming(self):
        return self.connectorID, self.transactionId, self.status, self.reply_channel, self.expected_watt
    
    def setTriggerMessageComming(self, value):
        self.isMessageComming = value
