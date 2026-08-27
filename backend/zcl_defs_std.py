# -*- coding: utf-8 -*-
"""标准 ZCL 数据 — 由 scripts/zap_xml_extract.py 从 gecko_sdk ZAP XML
(Silicon Labs 官方, 与 Zigbee Cluster Library spec 一致) 自动生成.
勿手改 — 重新生成: python scripts/zap_xml_extract.py
"""

CLUSTER_COMMANDS_STD: dict[int, dict[int, str]] = {
    # Basic (0x0000) [general.xml]
    0x0000: {
        0: 'Reset To Factory Defaults',
    },
    # Power Configuration (0x0001) [general.xml]
    0x0001: {
    },
    # Device Temperature Configuration (0x0002) [general.xml]
    0x0002: {
    },
    # Identify (0x0003) [general.xml]
    0x0003: {
        0: 'Identify / Identify Query Response',
        1: 'Identify Query',
        2: 'EZ Mode Invoke',
        3: 'Update Commission State',
    },
    # Groups (0x0004) [general.xml]
    0x0004: {
        0: 'Add Group / Add Group Response',
        1: 'View Group / View Group Response',
        2: 'Get Group Membership / Get Group Membership Response',
        3: 'Remove Group / Remove Group Response',
        4: 'Remove All Groups',
        5: 'Add Group If Identifying',
    },
    # Scenes (0x0005) [general.xml]
    0x0005: {
        0: 'Add Scene / Add Scene Response',
        1: 'View Scene / View Scene Response',
        2: 'Remove Scene / Remove Scene Response',
        3: 'Remove All Scenes / Remove All Scenes Response',
        4: 'Store Scene / Store Scene Response',
        5: 'Recall Scene',
        6: 'Get Scene Membership / Get Scene Membership Response',
    },
    # On/off (0x0006) [general.xml]
    0x0006: {
        0: 'Off',
        1: 'On',
        2: 'Toggle',
    },
    # On/off Switch Configuration (0x0007) [general.xml]
    0x0007: {
    },
    # Level Control (0x0008) [general.xml]
    0x0008: {
        0: 'Move To Level',
        1: 'Move',
        2: 'Step',
        3: 'Stop',
        4: 'Move To Level With On Off',
        5: 'Move With On Off',
        6: 'Step With On Off',
        7: 'Stop With On Off',
        8: 'Move To Closest Frequency',
    },
    # Alarms (0x0009) [general.xml]
    0x0009: {
        0: 'Reset Alarm / Alarm',
        1: 'Reset All Alarms / Get Alarm Response',
        2: 'Get Alarm',
        3: 'Reset Alarm Log',
    },
    # Time (0x000A) [general.xml]
    0x000A: {
    },
    # RSSI Location (0x000B) [general.xml]
    0x000B: {
        0: 'Set Absolute Location / Device Configuration Response',
        1: 'Set Device Configuration / Location Data Response',
        2: 'Get Device Configuration / Location Data Notification',
        3: 'Get Location Data / Compact Location Data Notification',
        4: 'Rssi Response / Rssi Ping',
        5: 'Send Pings / Rssi Request',
        6: 'Anchor Node Announce / Report Rssi Measurements',
        7: 'Request Own Location',
    },
    # Binary Input (Basic) (0x000F) [general.xml]
    0x000F: {
    },
    # Commissioning (0x0015) [general.xml]
    0x0015: {
        0: 'Restart Device / Restart Device Response',
        1: 'Save Startup Parameters / Save Startup Parameters Response',
        2: 'Restore Startup Parameters / Restore Startup Parameters Response',
        3: 'Reset Startup Parameters / Reset Startup Parameters Response',
    },
    # Partition (0x0016) [ta.xml]
    0x0016: {
        0: 'Transfer Partitioned Frame / Multiple Ack',
        1: 'Read Handshake Param / Read Handshake Param Response',
        2: 'Write Handshake Param',
    },
    # Power Profile (0x001A) [ha.xml]
    0x001A: {
        0: 'Power Profile Request / Power Profile Notification',
        1: 'Power Profile State Request / Power Profile Response',
        2: 'Get Power Profile Price Response / Power Profile State Response',
        3: 'Get Overall Schedule Price Response / Get Power Profile Price',
        4: 'Energy Phases Schedule Notification / Power Profiles State Notification',
        5: 'Energy Phases Schedule Response / Get Overall Schedule Price',
        6: 'Power Profile Schedule Constraints Request / Energy Phases Schedule Request',
        7: 'Energy Phases Schedule State Request / Energy Phases Schedule State Response',
        8: 'Get Power Profile Price Extended Response / Energy Phases Schedule State Notification',
        9: 'Power Profile Schedule Constraints Notification',
        10: 'Power Profile Schedule Constraints Response',
        11: 'Get Power Profile Price Extended',
    },
    # Appliance Control (0x001B) [ha.xml]
    0x001B: {
        0: 'Execution Of A Command / Signal State Response',
        1: 'Signal State / Signal State Notification',
        2: 'Write Functions',
        3: 'Overload Pause Resume',
        4: 'Overload Pause',
        5: 'Overload Warning',
    },
    # Poll Control (0x0020) [ha.xml]
    0x0020: {
        0: 'Check In / Check In Response',
        1: 'Fast Poll Stop',
        2: 'Set Long Poll Interval',
        3: 'Set Short Poll Interval',
    },
    # Green Power (0x0021) [green-power.xml]
    0x0021: {
        0: 'Gp Notification / Gp Notification Response',
        1: 'Gp Pairing Search / Gp Pairing',
        2: 'Gp Proxy Commissioning Mode',
        3: 'Gp Tunneling Stop',
        4: 'Gp Commissioning Notification',
        5: 'Gp Sink Commissioning Mode',
        6: 'Gp Response',
        7: 'Gp Translation Table Update',
        8: 'Gp Translation Table Request / Gp Translation Table Response',
        9: 'Gp Pairing Configuration',
        10: 'Gp Sink Table Request / Gp Sink Table Response',
        11: 'Gp Proxy Table Response / Gp Proxy Table Request',
    },
    # Keep-Alive (0x0025) [ami.xml]
    0x0025: {
    },
    # Zigbee Direct Configuration (0x003D) [zigbee-direct.xml]
    0x003D: {
        0: 'Configure Interface',
        1: 'Configure Anonymous Join Timeout',
    },
    # Shade Configuration (0x0100) [ha.xml]
    0x0100: {
    },
    # Door Lock (0x0101) [ha.xml]
    0x0101: {
        0: 'Lock Door / Lock Door Response',
        1: 'Unlock Door / Unlock Door Response',
        2: 'Toggle / Toggle Response',
        3: 'Unlock With Timeout / Unlock With Timeout Response',
        4: 'Get Log Record / Get Log Record Response',
        5: 'Set Pin / Set Pin Response',
        6: 'Get Pin / Get Pin Response',
        7: 'Clear Pin / Clear Pin Response',
        8: 'Clear All Pins / Clear All Pins Response',
        9: 'Set User Status / Set User Status Response',
        10: 'Get User Status / Get User Status Response',
        11: 'Set Weekday Schedule / Set Weekday Schedule Response',
        12: 'Get Weekday Schedule / Get Weekday Schedule Response',
        13: 'Clear Weekday Schedule / Clear Weekday Schedule Response',
        14: 'Set Yearday Schedule / Set Yearday Schedule Response',
        15: 'Get Yearday Schedule / Get Yearday Schedule Response',
        16: 'Clear Yearday Schedule / Clear Yearday Schedule Response',
        17: 'Set Holiday Schedule / Set Holiday Schedule Response',
        18: 'Get Holiday Schedule / Get Holiday Schedule Response',
        19: 'Clear Holiday Schedule / Clear Holiday Schedule Response',
        20: 'Set User Type / Set User Type Response',
        21: 'Get User Type / Get User Type Response',
        22: 'Set Rfid / Set Rfid Response',
        23: 'Get Rfid / Get Rfid Response',
        24: 'Clear Rfid / Clear Rfid Response',
        25: 'Clear All Rfids / Clear All Rfids Response',
        26: 'Set Disposable Schedule / Set Disposable Schedule Response',
        27: 'Get Disposable Schedule / Get Disposable Schedule Response',
        28: 'Clear Disposable Schedule / Clear Disposable Schedule Response',
        29: 'Clear Biometric Credential / Clear Biometric Credential Response',
        30: 'Clear All Biometric Credentials / Clear All Biometric Credentials Response',
        32: 'Operation Event Notification',
        33: 'Programming Event Notification',
    },
    # Window Covering (0x0102) [ha.xml]
    0x0102: {
        0: 'Window Covering Up Open',
        1: 'Window Covering Down Close',
        2: 'Window Covering Stop',
        4: 'Window Covering Go To Lift Value',
        5: 'Window Covering Go To Lift Percentage',
        7: 'Window Covering Go To Tilt Value',
        8: 'Window Covering Go To Tilt Percentage',
    },
    # Barrier Control (0x0103) [ha.xml]
    0x0103: {
        0: 'Barrier Control Go To Percent',
        1: 'Barrier Control Stop',
    },
    # Pump Configuration and Control (0x0200) [ha.xml]
    0x0200: {
    },
    # Thermostat (0x0201) [ha.xml]
    0x0201: {
        0: 'Setpoint Raise Lower / Current Weekly Schedule',
        1: 'Set Weekly Schedule / Relay Status Log',
        2: 'Get Weekly Schedule',
        3: 'Clear Weekly Schedule',
        4: 'Get Relay Status Log',
    },
    # Fan Control (0x0202) [ha.xml]
    0x0202: {
    },
    # Dehumidification Control (0x0203) [ha.xml]
    0x0203: {
    },
    # Thermostat User Interface Configuration (0x0204) [ha.xml]
    0x0204: {
    },
    # Color Control (0x0300) [ha.xml]
    0x0300: {
        0: 'Move To Hue',
        1: 'Move Hue',
        2: 'Step Hue',
        3: 'Move To Saturation',
        4: 'Move Saturation',
        5: 'Step Saturation',
        6: 'Move To Hue And Saturation',
        7: 'Move To Color',
        8: 'Move Color',
        9: 'Step Color',
        10: 'Move To Color Temperature',
    },
    # Ballast Configuration (0x0301) [ha.xml]
    0x0301: {
    },
    # Illuminance Measurement (0x0400) [ha.xml]
    0x0400: {
    },
    # Illuminance Level Sensing (0x0401) [ha.xml]
    0x0401: {
    },
    # Temperature Measurement (0x0402) [ha.xml]
    0x0402: {
    },
    # Pressure Measurement (0x0403) [ha.xml]
    0x0403: {
    },
    # Flow Measurement (0x0404) [ha.xml]
    0x0404: {
    },
    # Relative Humidity Measurement (0x0405) [ha.xml]
    0x0405: {
    },
    # Occupancy Sensing (0x0406) [ha.xml]
    0x0406: {
    },
    # Carbon Monoxide Concentration Measurement (0x040C) [ha.xml]
    0x040C: {
    },
    # Carbon Dioxide Concentration Measurement (0x040D) [ha.xml]
    0x040D: {
    },
    # Ethylene Concentration Measurement (0x040E) [ha.xml]
    0x040E: {
    },
    # Ethylene Oxide Concentration Measurement (0x040F) [ha.xml]
    0x040F: {
    },
    # Hydrogen Concentration Measurement (0x0410) [ha.xml]
    0x0410: {
    },
    # Hydrogen Sulphide Concentration Measurement (0x0411) [ha.xml]
    0x0411: {
    },
    # Nitric Oxide Concentration Measurement (0x0412) [ha.xml]
    0x0412: {
    },
    # Nitrogen Dioxide Concentration Measurement (0x0413) [ha.xml]
    0x0413: {
    },
    # Oxygen Concentration Measurement (0x0414) [ha.xml]
    0x0414: {
    },
    # Ozone Concentration Measurement (0x0415) [ha.xml]
    0x0415: {
    },
    # Sulfur Dioxide Concentration Measurement (0x0416) [ha.xml]
    0x0416: {
    },
    # Dissolved Oxygen Concentration Measurement (0x0417) [ha.xml]
    0x0417: {
    },
    # Bromate Concentration Measurement (0x0418) [ha.xml]
    0x0418: {
    },
    # Chloramines Concentration Measurement (0x0419) [ha.xml]
    0x0419: {
    },
    # Chlorine Concentration Measurement (0x041A) [ha.xml]
    0x041A: {
    },
    # Fecal coliform and E. Coli Concentration Measurement (0x041B) [ha.xml]
    0x041B: {
    },
    # Fluoride Concentration Measurement (0x041C) [ha.xml]
    0x041C: {
    },
    # Haloacetic Acids Concentration Measurement (0x041D) [ha.xml]
    0x041D: {
    },
    # Total Trihalomethanes Concentration Measurement (0x041E) [ha.xml]
    0x041E: {
    },
    # Total Coliform Bacteria Concentration Measurement (0x041F) [ha.xml]
    0x041F: {
    },
    # Turbidity Concentration Measurement (0x0420) [ha.xml]
    0x0420: {
    },
    # Copper Concentration Measurement (0x0421) [ha.xml]
    0x0421: {
    },
    # Lead Concentration Measurement (0x0422) [ha.xml]
    0x0422: {
    },
    # Manganese Concentration Measurement (0x0423) [ha.xml]
    0x0423: {
    },
    # Sulfate Concentration Measurement (0x0424) [ha.xml]
    0x0424: {
    },
    # Bromodichloromethane Concentration Measurement (0x0425) [ha.xml]
    0x0425: {
    },
    # Bromoform Concentration Measurement (0x0426) [ha.xml]
    0x0426: {
    },
    # Chlorodibromomethane Concentration Measurement (0x0427) [ha.xml]
    0x0427: {
    },
    # Chloroform Concentration Measurement (0x0428) [ha.xml]
    0x0428: {
    },
    # Sodium Concentration Measurement (0x0429) [ha.xml]
    0x0429: {
    },
    # IAS Zone (0x0500) [ha.xml]
    0x0500: {
        0: 'Zone Enroll Response / Zone Status Change Notification',
        1: 'Initiate Normal Operation Mode / Zone Enroll Request',
        2: 'Initiate Test Mode / Initiate Normal Operation Mode Response',
        3: 'Initiate Test Mode Response',
    },
    # IAS ACE (0x0501) [ha.xml]
    0x0501: {
        0: 'Arm / Arm Response',
        1: 'Bypass / Get Zone Id Map Response',
        2: 'Emergency / Get Zone Information Response',
        3: 'Fire / Zone Status Changed',
        4: 'Panic / Panel Status Changed',
        5: 'Get Zone Id Map / Get Panel Status Response',
        6: 'Get Zone Information / Set Bypassed Zone List',
        7: 'Get Panel Status / Bypass Response',
        8: 'Get Bypassed Zone List / Get Zone Status Response',
        9: 'Get Zone Status',
    },
    # IAS WD (0x0502) [ha.xml]
    0x0502: {
        0: 'Start Warning',
        1: 'Squawk',
    },
    # Generic Tunnel (0x0600) [cba.xml]
    0x0600: {
        0: 'Match Protocol Address / Match Protocol Address Response',
        1: 'Advertise Protocol Address',
    },
    # BACnet Protocol Tunnel (0x0601) [cba.xml]
    0x0601: {
        0: 'Transfer Npdu',
    },
    # 11073 Protocol Tunnel (0x0614) [hc.xml]
    0x0614: {
        0: 'Transfer APDU',
        1: 'Connect Request',
        2: 'Disconnect Request',
        3: 'Connect Status Notification',
    },
    # ISO 7816 Protocol Tunnel (0x0615) [ta.xml]
    0x0615: {
        0: 'Transfer Apdu From Client / Transfer Apdu From Server',
        1: 'Insert Smart Card',
        2: 'Extract Smart Card',
    },
    # Price (0x0700) [ami.xml]
    0x0700: {
        0: 'Publish Price / Get Current Price',
        1: 'Publish Block Period / Get Scheduled Prices',
        2: 'Publish Conversion Factor / Price Acknowledgement',
        3: 'Publish Calorific Value / Get Block Periods',
        4: 'Publish Tariff Information / Get Conversion Factor',
        5: 'Publish Price Matrix / Get Calorific Value',
        6: 'Publish Block Thresholds / Get Tariff Information',
        7: 'Publish CO2 Value / Get Price Matrix',
        8: 'Publish Tier Labels / Get Block Thresholds',
        9: 'Publish Billing Period / Get CO2 Value',
        10: 'Publish Consolidated Bill / Get Tier Labels',
        11: 'Publish Cpp Event / Get Billing Period',
        12: 'Publish Credit Payment / Get Consolidated Bill',
        13: 'Publish Currency Conversion / Cpp Event Response',
        14: 'Cancel Tariff / Get Credit Payment',
        15: 'Get Currency Conversion Command',
        16: 'Get Tariff Cancellation',
    },
    # Demand Response and Load Control (0x0701) [ami.xml]
    0x0701: {
        0: 'Load Control Event / Report Event Status',
        1: 'Cancel Load Control Event / Get Scheduled Events',
        2: 'Cancel All Load Control Events',
    },
    # Simple Metering (0x0702) [ami.xml]
    0x0702: {
        0: 'Get Profile Response / Get Profile',
        1: 'Request Mirror / Request Mirror Response',
        2: 'Remove Mirror / Mirror Removed',
        3: 'Request Fast Poll Mode Response / Request Fast Poll Mode',
        4: 'Schedule Snapshot Response / Schedule Snapshot',
        5: 'Take Snapshot Response / Take Snapshot',
        6: 'Publish Snapshot / Get Snapshot',
        7: 'Get Sampled Data Response / Start Sampling',
        8: 'Configure Mirror / Get Sampled Data',
        9: 'Configure Notification Scheme / Mirror Report Attribute Response',
        10: 'Configure Notification Flags / Reset Load Limit Counter',
        11: 'Get Notified Message / Change Supply',
        12: 'Supply Status Response / Local Change Supply',
        13: 'Start Sampling Response / Set Supply Status',
        14: 'Set Uncontrolled Flow Threshold',
    },
    # Messaging (0x0703) [ami.xml]
    0x0703: {
        0: 'Display Message / Get Last Message',
        1: 'Cancel Message / Message Confirmation',
        2: 'Display Protected Message / Get Message Cancellation',
        3: 'Cancel All Messages',
    },
    # Tunneling (0x0704) [ami.xml]
    0x0704: {
        0: 'Request Tunnel / Request Tunnel Response',
        1: 'Close Tunnel / Transfer Data Server To Client',
        2: 'Transfer Data Client To Server / Transfer Data Error Server To Client',
        3: 'Transfer Data Error Client To Server / Ack Transfer Data Server To Client',
        4: 'Ack Transfer Data Client To Server / Ready Data Server To Client',
        5: 'Ready Data Client To Server / Supported Tunnel Protocols Response',
        6: 'Get Supported Tunnel Protocols / Tunnel Closure Notification',
    },
    # Prepayment (0x0705) [ami.xml]
    0x0705: {
        0: 'Select Available Emergency Credit',
        1: 'Publish Prepay Snapshot',
        2: 'Change Debt / Change Payment Mode Response',
        3: 'Emergency Credit Setup / Consumer Top Up Response',
        4: 'Consumer Top Up',
        5: 'Credit Adjustment / Publish Top Up Log',
        6: 'Change Payment Mode / Publish Debt Log',
        7: 'Get Prepay Snapshot',
        8: 'Get Top Up Log',
        9: 'Set Low Credit Warning Level',
        10: 'Get Debt Repayment Log',
        11: 'Set Maximum Credit Limit',
        12: 'Set Overall Debt Cap',
    },
    # Energy Management (0x0706) [ami.xml]
    0x0706: {
        0: 'Report Event Status / Manage Event',
    },
    # Calendar (0x0707) [ami.xml]
    0x0707: {
        0: 'Publish Calendar / Get Calendar',
        1: 'Publish Day Profile / Get Day Profiles',
        2: 'Publish Week Profile / Get Week Profiles',
        3: 'Publish Seasons / Get Seasons',
        4: 'Publish Special Days / Get Special Days',
        5: 'Cancel Calendar / Get Calendar Cancellation',
    },
    # Device Management (0x0708) [ami.xml]
    0x0708: {
        0: 'Get Change Of Tenancy / Publish Change Of Tenancy',
        1: 'Get Change Of Supplier / Publish Change Of Supplier',
        2: 'Request New Password / Request New Password Response',
        3: 'Get Site Id / Update Site Id',
        4: 'Report Event Configuration / Set Event Configuration',
        5: 'Get CIN / Get Event Configuration',
        6: 'Update CIN',
    },
    # Events (0x0709) [ami.xml]
    0x0709: {
        0: 'Get Event Log / Publish Event',
        1: 'Clear Event Log Request / Publish Event Log',
        2: 'Clear Event Log Response',
    },
    # MDU Pairing (0x070A) [ami.xml]
    0x070A: {
        0: 'Pairing Response / Pairing Request',
    },
    # Sub-GHz (0x070B) [ami.xml]
    0x070B: {
        0: 'Suspend Zcl Messages / Get Suspend Zcl Messages Status',
    },
    # Key Establishment (0x0800) [ami.xml]
    0x0800: {
        0: 'Initiate Key Establishment Request / Initiate Key Establishment Response',
        1: 'Ephemeral Data Request / Ephemeral Data Response',
        2: 'Confirm Key Data Request / Confirm Key Data Response',
        3: 'Terminate Key Establishment From Client / Terminate Key Establishment From Server',
    },
    # Information (0x0900) [ta.xml]
    0x0900: {
        0: 'Request Information / Request Information Response',
        1: 'Push Information Response / Push Information',
        2: 'Send Preference / Send Preference Response',
        3: 'Request Preference Response / Server Request Preference',
        4: 'Update / Request Preference Confirmation',
        5: 'Delete / Update Response',
        6: 'Configure Node Description / Delete Response',
        7: 'Configure Delivery Enable',
        8: 'Configure Push Information Timer',
        9: 'Configure Set Root Id',
    },
    # Data Sharing (0x0901) [ta.xml]
    0x0901: {
        0: 'Read File Request / Write File Request',
        1: 'Read Record Request / Modify File Request',
        2: 'Write File Response / Modify Record Request',
        3: 'File Transmission',
        4: 'Record Transmission',
    },
    # Gaming (0x0902) [ta.xml]
    0x0902: {
        0: 'Search Game / Game Announcement',
        1: 'Join Game / General Response',
        2: 'Start Game',
        3: 'Pause Game',
        4: 'Resume Game',
        5: 'Quit Game',
        6: 'End Game',
        7: 'Start Over',
        8: 'Action Control',
        9: 'Download Game',
    },
    # Data Rate Control (0x0903) [ta.xml]
    0x0903: {
        0: 'Path Creation / Data Rate Control',
        1: 'Data Rate Notification',
        2: 'Path Deletion',
    },
    # Voice over ZigBee (0x0904) [ta.xml]
    0x0904: {
        0: 'Establishment Request / Establishment Response',
        1: 'Voice Transmission / Voice Transmission Response',
        2: 'Voice Transmission Completion / Control',
        3: 'Control Response',
    },
    # Chatting (0x0905) [ta.xml]
    0x0905: {
        0: 'Join Chat Request / Start Chat Response',
        1: 'Leave Chat Request / Join Chat Response',
        2: 'Search Chat Request / User Left',
        3: 'Switch Chairman Response / User Joined',
        4: 'Start Chat Request / Search Chat Response',
        5: 'Chat Message / Switch Chairman Request',
        6: 'Get Node Information Request / Switch Chairman Confirm',
        7: 'Switch Chairman Notification',
        8: 'Get Node Information Response',
    },
    # Payment (0x0A01) [ta.xml]
    0x0A01: {
        0: 'Buy Request / Buy Confirm',
        1: 'Accept Payment / Receipt Delivery',
        2: 'Payment Confirm / Transaction End',
    },
    # Billing (0x0A02) [ta.xml]
    0x0A02: {
        0: 'Subscribe / Check Bill Status',
        1: 'Unsubscribe / Send Bill Record',
        2: 'Start Billing Session',
        3: 'Stop Billing Session',
        4: 'Bill Status Notification',
        5: 'Session Keep Alive',
    },
    # Appliance Identification (0x0B00) [ha.xml]
    0x0B00: {
    },
    # Meter Identification (0x0B01) [ha.xml]
    0x0B01: {
    },
    # Appliance Events and Alert (0x0B02) [ha.xml]
    0x0B02: {
        0: 'Get Alerts / Get Alerts Response',
        1: 'Alerts Notification',
        2: 'Events Notification',
    },
    # Appliance Statistics (0x0B03) [ha.xml]
    0x0B03: {
        0: 'Log Notification / Log Request',
        1: 'Log Response / Log Queue Request',
        2: 'Log Queue Response',
        3: 'Statistics Available',
    },
    # Electrical Measurement (0x0B04) [ha.xml]
    0x0B04: {
        0: 'Get Profile Info Response Command / Get Profile Info Command',
        1: 'Get Measurement Profile Response Command / Get Measurement Profile Command',
    },
    # Diagnostics (0x0B05) [ha.xml]
    0x0B05: {
    },
    # ZLL Commissioning (0x1000) [zll.xml]
    0x1000: {
        0: 'Scan Request',
        1: 'Scan Response',
        2: 'Device Information Request',
        3: 'Device Information Response',
        6: 'Identify Request',
        7: 'Reset To Factory New Request',
        16: 'Network Start Request',
        17: 'Network Start Response',
        18: 'Network Join Router Request',
        19: 'Network Join Router Response',
        20: 'Network Join End Device Request',
        21: 'Network Join End Device Response',
        22: 'Network Update Request',
        64: 'Endpoint Information',
        65: 'Get Group Identifiers Request / Get Group Identifiers Response',
        66: 'Get Endpoint List Request / Get Endpoint List Response',
    },
    # Relay Control (0xC00D) [relay-control.xml]
    0xC00D: {
        0: 'Set Relay State / Get Relay State Response',
        1: 'Get Relay State',
    },
    # Sample Mfg Specific Cluster 2 (0xFC00) [sample-extensions.xml]
    0xFC00: {
        0: 'Command Two',
    },
    # Configuration Cluster (0xFC01) [silabs.xml]
    0xFC01: {
        0: 'Set Token / Return Token',
        1: 'Lock Tokens',
        2: 'Read Tokens',
        3: 'Unlock Tokens',
    },
    # MFGLIB Cluster (0xFC02) [silabs.xml]
    0xFC02: {
        0: 'stream',
        1: 'tone',
        2: 'rx Mode',
    },
    # SL Works With All Hubs (0xFC57) [wwah-silabs.xml]
    0xFC57: {
        0: 'Enable Aps Link Key Authorization / Aps Link Key Authorization Query Response',
        1: 'Disable Aps Link Key Authorization / Powering Off Notification',
        2: 'Aps Link Key Authorization Query / Powering On Notification',
        3: 'Request New Aps Link Key / Short Address Change',
        4: 'Enable Wwah App Event Retry Algorithm / Aps Ack Enablement Query Response',
        5: 'Disable Wwah App Event Retry Algorithm / Power Descriptor Change',
        6: 'Request Time / New Debug Report Notification',
        7: 'Enable Wwah Rejoin Algorithm / Debug Report Query Response',
        8: 'Disable Wwah Rejoin Algorithm / Trust Center For Cluster Server Query Response',
        9: 'Set Ias Zone Enrollment Method / Survey Beacons Response',
        10: 'Clear Binding Table',
        11: 'Enable Periodic Router Check Ins',
        12: 'Disable Periodic Router Check Ins',
        13: 'Set Mac Poll Failure Wait Time',
        14: 'Set Pending Network Update',
        15: 'Require Aps Acks On Unicasts',
        16: 'Remove Aps Acks On Unicasts Requirement',
        17: 'Aps Ack Requirement Query',
        18: 'Debug Report Query',
        19: 'Survey Beacons',
        20: 'Disable Ota Downgrades',
        21: 'Disable Mgmt Leave Without Rejoin',
        22: 'Disable Touchlink Interpan Message Support',
        23: 'Enable Wwah Parent Classification',
        24: 'Disable Wwah Parent Classification',
        25: 'Enable Tc Security On Ntwk Key Rotation',
        26: 'Enable Wwah Bad Parent Recovery',
        27: 'Disable Wwah Bad Parent Recovery',
        28: 'Enable Configuration Mode',
        29: 'Disable Configuration Mode',
        30: 'Use Trust Center For Cluster Server',
        31: 'Trust Center For Cluster Server Query',
        158: 'Use Trust Center For Cluster Server Response',
    },
}

CMD_PAYLOAD_SCHEMAS_STD: dict[int, dict[int, dict[str, list]]] = {
    # Basic (0x0000) [general.xml]
    0x0000: {
        0: {
            "C→S": [
            ],
        },
    },
    # Identify (0x0003) [general.xml]
    0x0003: {
        0: {
            "C→S": [
                {"name": 'identify Time', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'timeout', "type": 'u16'},
            ],
        },
        1: {
            "C→S": [
            ],
        },
        2: {
            "C→S": [
                {"name": 'action', "type": 'bytes:4'},
            ],
        },
        3: {
            "C→S": [
                {"name": 'action', "type": 'u8'},
                {"name": 'commission State Mask', "type": 'bytes:4'},
            ],
        },
    },
    # Groups (0x0004) [general.xml]
    0x0004: {
        0: {
            "C→S": [
                {"name": 'group Id', "type": 'u16'},
                {"name": 'group Name', "type": 'zstr'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8', "enum": {0: 'SUCCESS', 1: 'FAILURE', 126: 'NOT_AUTHORIZED', 128: 'MALFORMED_COMMAND', 129: 'UNSUP_COMMAND', 130: 'UNSUP_GENERAL_COMMAND', 131: 'UNSUP_MANUF_CLUSTER_COMMAND', 132: 'UNSUP_MANUF_GENERAL_COMMAND', 133: 'INVALID_FIELD', 134: 'UNSUPPORTED_ATTRIBUTE', 135: 'INVALID_VALUE', 136: 'READ_ONLY', 137: 'INSUFFICIENT_SPACE', 138: 'DUPLICATE_EXISTS', 139: 'NOT_FOUND', 140: 'UNREPORTABLE_ATTRIBUTE', 141: 'INVALID_DATA_TYPE', 142: 'INVALID_SELECTOR', 143: 'WRITE_ONLY', 144: 'INCONSISTENT_STARTUP_STATE', 145: 'DEFINED_OUT_OF_BAND', 147: 'ACTION_DENIED', 148: 'TIMEOUT', 149: 'ABORT', 150: 'INVALID_IMAGE', 151: 'WAIT_FOR_DATA', 152: 'NO_IMAGE_AVAILABLE', 153: 'REQUIRE_MORE_IMAGE', 154: 'NOTIFICATION_PENDING', 192: 'HARDWARE_FAILURE', 193: 'SOFTWARE_FAILURE', 195: 'UNSUPPORTED_CLUSTER', 196: 'LIMIT_REACHED'}},
                {"name": 'group Id', "type": 'u16'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'group Id', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8', "enum": {0: 'SUCCESS', 1: 'FAILURE', 126: 'NOT_AUTHORIZED', 128: 'MALFORMED_COMMAND', 129: 'UNSUP_COMMAND', 130: 'UNSUP_GENERAL_COMMAND', 131: 'UNSUP_MANUF_CLUSTER_COMMAND', 132: 'UNSUP_MANUF_GENERAL_COMMAND', 133: 'INVALID_FIELD', 134: 'UNSUPPORTED_ATTRIBUTE', 135: 'INVALID_VALUE', 136: 'READ_ONLY', 137: 'INSUFFICIENT_SPACE', 138: 'DUPLICATE_EXISTS', 139: 'NOT_FOUND', 140: 'UNREPORTABLE_ATTRIBUTE', 141: 'INVALID_DATA_TYPE', 142: 'INVALID_SELECTOR', 143: 'WRITE_ONLY', 144: 'INCONSISTENT_STARTUP_STATE', 145: 'DEFINED_OUT_OF_BAND', 147: 'ACTION_DENIED', 148: 'TIMEOUT', 149: 'ABORT', 150: 'INVALID_IMAGE', 151: 'WAIT_FOR_DATA', 152: 'NO_IMAGE_AVAILABLE', 153: 'REQUIRE_MORE_IMAGE', 154: 'NOTIFICATION_PENDING', 192: 'HARDWARE_FAILURE', 193: 'SOFTWARE_FAILURE', 195: 'UNSUPPORTED_CLUSTER', 196: 'LIMIT_REACHED'}},
                {"name": 'group Id', "type": 'u16'},
                {"name": 'group Name', "type": 'zstr'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'group Count', "type": 'u8'},
                {"name": 'group List', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'capacity', "type": 'u8'},
                {"name": 'group Count', "type": 'u8'},
                {"name": 'group List', "type": 'u16'},
            ],
        },
        3: {
            "C→S": [
                {"name": 'group Id', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8', "enum": {0: 'SUCCESS', 1: 'FAILURE', 126: 'NOT_AUTHORIZED', 128: 'MALFORMED_COMMAND', 129: 'UNSUP_COMMAND', 130: 'UNSUP_GENERAL_COMMAND', 131: 'UNSUP_MANUF_CLUSTER_COMMAND', 132: 'UNSUP_MANUF_GENERAL_COMMAND', 133: 'INVALID_FIELD', 134: 'UNSUPPORTED_ATTRIBUTE', 135: 'INVALID_VALUE', 136: 'READ_ONLY', 137: 'INSUFFICIENT_SPACE', 138: 'DUPLICATE_EXISTS', 139: 'NOT_FOUND', 140: 'UNREPORTABLE_ATTRIBUTE', 141: 'INVALID_DATA_TYPE', 142: 'INVALID_SELECTOR', 143: 'WRITE_ONLY', 144: 'INCONSISTENT_STARTUP_STATE', 145: 'DEFINED_OUT_OF_BAND', 147: 'ACTION_DENIED', 148: 'TIMEOUT', 149: 'ABORT', 150: 'INVALID_IMAGE', 151: 'WAIT_FOR_DATA', 152: 'NO_IMAGE_AVAILABLE', 153: 'REQUIRE_MORE_IMAGE', 154: 'NOTIFICATION_PENDING', 192: 'HARDWARE_FAILURE', 193: 'SOFTWARE_FAILURE', 195: 'UNSUPPORTED_CLUSTER', 196: 'LIMIT_REACHED'}},
                {"name": 'group Id', "type": 'u16'},
            ],
        },
        4: {
            "C→S": [
            ],
        },
        5: {
            "C→S": [
                {"name": 'group Id', "type": 'u16'},
                {"name": 'group Name', "type": 'zstr'},
            ],
        },
    },
    # Scenes (0x0005) [general.xml]
    0x0005: {
        0: {
            "C→S": [
                {"name": 'group Id', "type": 'u16'},
                {"name": 'scene Id', "type": 'u8'},
                {"name": 'transition Time', "type": 'u16'},
                {"name": 'scene Name', "type": 'zstr'},
                {"name": 'extension Field Sets', "type": 'bytes:4'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8', "enum": {0: 'SUCCESS', 1: 'FAILURE', 126: 'NOT_AUTHORIZED', 128: 'MALFORMED_COMMAND', 129: 'UNSUP_COMMAND', 130: 'UNSUP_GENERAL_COMMAND', 131: 'UNSUP_MANUF_CLUSTER_COMMAND', 132: 'UNSUP_MANUF_GENERAL_COMMAND', 133: 'INVALID_FIELD', 134: 'UNSUPPORTED_ATTRIBUTE', 135: 'INVALID_VALUE', 136: 'READ_ONLY', 137: 'INSUFFICIENT_SPACE', 138: 'DUPLICATE_EXISTS', 139: 'NOT_FOUND', 140: 'UNREPORTABLE_ATTRIBUTE', 141: 'INVALID_DATA_TYPE', 142: 'INVALID_SELECTOR', 143: 'WRITE_ONLY', 144: 'INCONSISTENT_STARTUP_STATE', 145: 'DEFINED_OUT_OF_BAND', 147: 'ACTION_DENIED', 148: 'TIMEOUT', 149: 'ABORT', 150: 'INVALID_IMAGE', 151: 'WAIT_FOR_DATA', 152: 'NO_IMAGE_AVAILABLE', 153: 'REQUIRE_MORE_IMAGE', 154: 'NOTIFICATION_PENDING', 192: 'HARDWARE_FAILURE', 193: 'SOFTWARE_FAILURE', 195: 'UNSUPPORTED_CLUSTER', 196: 'LIMIT_REACHED'}},
                {"name": 'group Id', "type": 'u16'},
                {"name": 'scene Id', "type": 'u8'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'group Id', "type": 'u16'},
                {"name": 'scene Id', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8', "enum": {0: 'SUCCESS', 1: 'FAILURE', 126: 'NOT_AUTHORIZED', 128: 'MALFORMED_COMMAND', 129: 'UNSUP_COMMAND', 130: 'UNSUP_GENERAL_COMMAND', 131: 'UNSUP_MANUF_CLUSTER_COMMAND', 132: 'UNSUP_MANUF_GENERAL_COMMAND', 133: 'INVALID_FIELD', 134: 'UNSUPPORTED_ATTRIBUTE', 135: 'INVALID_VALUE', 136: 'READ_ONLY', 137: 'INSUFFICIENT_SPACE', 138: 'DUPLICATE_EXISTS', 139: 'NOT_FOUND', 140: 'UNREPORTABLE_ATTRIBUTE', 141: 'INVALID_DATA_TYPE', 142: 'INVALID_SELECTOR', 143: 'WRITE_ONLY', 144: 'INCONSISTENT_STARTUP_STATE', 145: 'DEFINED_OUT_OF_BAND', 147: 'ACTION_DENIED', 148: 'TIMEOUT', 149: 'ABORT', 150: 'INVALID_IMAGE', 151: 'WAIT_FOR_DATA', 152: 'NO_IMAGE_AVAILABLE', 153: 'REQUIRE_MORE_IMAGE', 154: 'NOTIFICATION_PENDING', 192: 'HARDWARE_FAILURE', 193: 'SOFTWARE_FAILURE', 195: 'UNSUPPORTED_CLUSTER', 196: 'LIMIT_REACHED'}},
                {"name": 'group Id', "type": 'u16'},
                {"name": 'scene Id', "type": 'u8'},
                {"name": 'transition Time', "type": 'u16'},
                {"name": 'scene Name', "type": 'zstr'},
                {"name": 'extension Field Sets', "type": 'bytes:4'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'group Id', "type": 'u16'},
                {"name": 'scene Id', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8', "enum": {0: 'SUCCESS', 1: 'FAILURE', 126: 'NOT_AUTHORIZED', 128: 'MALFORMED_COMMAND', 129: 'UNSUP_COMMAND', 130: 'UNSUP_GENERAL_COMMAND', 131: 'UNSUP_MANUF_CLUSTER_COMMAND', 132: 'UNSUP_MANUF_GENERAL_COMMAND', 133: 'INVALID_FIELD', 134: 'UNSUPPORTED_ATTRIBUTE', 135: 'INVALID_VALUE', 136: 'READ_ONLY', 137: 'INSUFFICIENT_SPACE', 138: 'DUPLICATE_EXISTS', 139: 'NOT_FOUND', 140: 'UNREPORTABLE_ATTRIBUTE', 141: 'INVALID_DATA_TYPE', 142: 'INVALID_SELECTOR', 143: 'WRITE_ONLY', 144: 'INCONSISTENT_STARTUP_STATE', 145: 'DEFINED_OUT_OF_BAND', 147: 'ACTION_DENIED', 148: 'TIMEOUT', 149: 'ABORT', 150: 'INVALID_IMAGE', 151: 'WAIT_FOR_DATA', 152: 'NO_IMAGE_AVAILABLE', 153: 'REQUIRE_MORE_IMAGE', 154: 'NOTIFICATION_PENDING', 192: 'HARDWARE_FAILURE', 193: 'SOFTWARE_FAILURE', 195: 'UNSUPPORTED_CLUSTER', 196: 'LIMIT_REACHED'}},
                {"name": 'group Id', "type": 'u16'},
                {"name": 'scene Id', "type": 'u8'},
            ],
        },
        3: {
            "C→S": [
                {"name": 'group Id', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8', "enum": {0: 'SUCCESS', 1: 'FAILURE', 126: 'NOT_AUTHORIZED', 128: 'MALFORMED_COMMAND', 129: 'UNSUP_COMMAND', 130: 'UNSUP_GENERAL_COMMAND', 131: 'UNSUP_MANUF_CLUSTER_COMMAND', 132: 'UNSUP_MANUF_GENERAL_COMMAND', 133: 'INVALID_FIELD', 134: 'UNSUPPORTED_ATTRIBUTE', 135: 'INVALID_VALUE', 136: 'READ_ONLY', 137: 'INSUFFICIENT_SPACE', 138: 'DUPLICATE_EXISTS', 139: 'NOT_FOUND', 140: 'UNREPORTABLE_ATTRIBUTE', 141: 'INVALID_DATA_TYPE', 142: 'INVALID_SELECTOR', 143: 'WRITE_ONLY', 144: 'INCONSISTENT_STARTUP_STATE', 145: 'DEFINED_OUT_OF_BAND', 147: 'ACTION_DENIED', 148: 'TIMEOUT', 149: 'ABORT', 150: 'INVALID_IMAGE', 151: 'WAIT_FOR_DATA', 152: 'NO_IMAGE_AVAILABLE', 153: 'REQUIRE_MORE_IMAGE', 154: 'NOTIFICATION_PENDING', 192: 'HARDWARE_FAILURE', 193: 'SOFTWARE_FAILURE', 195: 'UNSUPPORTED_CLUSTER', 196: 'LIMIT_REACHED'}},
                {"name": 'group Id', "type": 'u16'},
            ],
        },
        4: {
            "C→S": [
                {"name": 'group Id', "type": 'u16'},
                {"name": 'scene Id', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8', "enum": {0: 'SUCCESS', 1: 'FAILURE', 126: 'NOT_AUTHORIZED', 128: 'MALFORMED_COMMAND', 129: 'UNSUP_COMMAND', 130: 'UNSUP_GENERAL_COMMAND', 131: 'UNSUP_MANUF_CLUSTER_COMMAND', 132: 'UNSUP_MANUF_GENERAL_COMMAND', 133: 'INVALID_FIELD', 134: 'UNSUPPORTED_ATTRIBUTE', 135: 'INVALID_VALUE', 136: 'READ_ONLY', 137: 'INSUFFICIENT_SPACE', 138: 'DUPLICATE_EXISTS', 139: 'NOT_FOUND', 140: 'UNREPORTABLE_ATTRIBUTE', 141: 'INVALID_DATA_TYPE', 142: 'INVALID_SELECTOR', 143: 'WRITE_ONLY', 144: 'INCONSISTENT_STARTUP_STATE', 145: 'DEFINED_OUT_OF_BAND', 147: 'ACTION_DENIED', 148: 'TIMEOUT', 149: 'ABORT', 150: 'INVALID_IMAGE', 151: 'WAIT_FOR_DATA', 152: 'NO_IMAGE_AVAILABLE', 153: 'REQUIRE_MORE_IMAGE', 154: 'NOTIFICATION_PENDING', 192: 'HARDWARE_FAILURE', 193: 'SOFTWARE_FAILURE', 195: 'UNSUPPORTED_CLUSTER', 196: 'LIMIT_REACHED'}},
                {"name": 'group Id', "type": 'u16'},
                {"name": 'scene Id', "type": 'u8'},
            ],
        },
        5: {
            "C→S": [
                {"name": 'group Id', "type": 'u16'},
                {"name": 'scene Id', "type": 'u8'},
                {"name": 'transition Time', "type": 'u16', "note": '(zcl-7.0-07-5123-07)'},
            ],
        },
        6: {
            "C→S": [
                {"name": 'group Id', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8', "enum": {0: 'SUCCESS', 1: 'FAILURE', 126: 'NOT_AUTHORIZED', 128: 'MALFORMED_COMMAND', 129: 'UNSUP_COMMAND', 130: 'UNSUP_GENERAL_COMMAND', 131: 'UNSUP_MANUF_CLUSTER_COMMAND', 132: 'UNSUP_MANUF_GENERAL_COMMAND', 133: 'INVALID_FIELD', 134: 'UNSUPPORTED_ATTRIBUTE', 135: 'INVALID_VALUE', 136: 'READ_ONLY', 137: 'INSUFFICIENT_SPACE', 138: 'DUPLICATE_EXISTS', 139: 'NOT_FOUND', 140: 'UNREPORTABLE_ATTRIBUTE', 141: 'INVALID_DATA_TYPE', 142: 'INVALID_SELECTOR', 143: 'WRITE_ONLY', 144: 'INCONSISTENT_STARTUP_STATE', 145: 'DEFINED_OUT_OF_BAND', 147: 'ACTION_DENIED', 148: 'TIMEOUT', 149: 'ABORT', 150: 'INVALID_IMAGE', 151: 'WAIT_FOR_DATA', 152: 'NO_IMAGE_AVAILABLE', 153: 'REQUIRE_MORE_IMAGE', 154: 'NOTIFICATION_PENDING', 192: 'HARDWARE_FAILURE', 193: 'SOFTWARE_FAILURE', 195: 'UNSUPPORTED_CLUSTER', 196: 'LIMIT_REACHED'}},
                {"name": 'capacity', "type": 'u8'},
                {"name": 'group Id', "type": 'u16'},
                {"name": 'scene Count', "type": 'u8'},
                {"name": 'scene List', "type": 'u8'},
            ],
        },
    },
    # On/off (0x0006) [general.xml]
    0x0006: {
        0: {
            "C→S": [
            ],
        },
        1: {
            "C→S": [
            ],
        },
        2: {
            "C→S": [
            ],
        },
    },
    # Level Control (0x0008) [general.xml]
    0x0008: {
        0: {
            "C→S": [
                {"name": 'level', "type": 'u8'},
                {"name": 'transition Time', "type": 'u16'},
                {"name": 'option Mask', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
                {"name": 'option Override', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'move Mode', "type": 'u8', "enum": {0: 'Up', 1: 'Down'}},
                {"name": 'rate', "type": 'u8'},
                {"name": 'option Mask', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
                {"name": 'option Override', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'step Mode', "type": 'u8', "enum": {0: 'Up', 1: 'Down'}},
                {"name": 'step Size', "type": 'u8'},
                {"name": 'transition Time', "type": 'u16'},
                {"name": 'option Mask', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
                {"name": 'option Override', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
            ],
        },
        3: {
            "C→S": [
                {"name": 'option Mask', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
                {"name": 'option Override', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
            ],
        },
        4: {
            "C→S": [
                {"name": 'level', "type": 'u8'},
                {"name": 'transition Time', "type": 'u16'},
            ],
        },
        5: {
            "C→S": [
                {"name": 'move Mode', "type": 'u8', "enum": {0: 'Up', 1: 'Down'}},
                {"name": 'rate', "type": 'u8'},
            ],
        },
        6: {
            "C→S": [
                {"name": 'step Mode', "type": 'u8', "enum": {0: 'Up', 1: 'Down'}},
                {"name": 'step Size', "type": 'u8'},
                {"name": 'transition Time', "type": 'u16'},
            ],
        },
        7: {
            "C→S": [
            ],
        },
        8: {
            "C→S": [
                {"name": 'frequency', "type": 'u16'},
            ],
        },
    },
    # Alarms (0x0009) [general.xml]
    0x0009: {
        0: {
            "C→S": [
                {"name": 'alarm Code', "type": 'u8'},
                {"name": 'cluster Id', "type": 'bytes:4'},
            ],
            "S→C": [
                {"name": 'alarm Code', "type": 'u8'},
                {"name": 'cluster Id', "type": 'bytes:4'},
            ],
        },
        1: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'status', "type": 'u8', "enum": {0: 'SUCCESS', 1: 'FAILURE', 126: 'NOT_AUTHORIZED', 128: 'MALFORMED_COMMAND', 129: 'UNSUP_COMMAND', 130: 'UNSUP_GENERAL_COMMAND', 131: 'UNSUP_MANUF_CLUSTER_COMMAND', 132: 'UNSUP_MANUF_GENERAL_COMMAND', 133: 'INVALID_FIELD', 134: 'UNSUPPORTED_ATTRIBUTE', 135: 'INVALID_VALUE', 136: 'READ_ONLY', 137: 'INSUFFICIENT_SPACE', 138: 'DUPLICATE_EXISTS', 139: 'NOT_FOUND', 140: 'UNREPORTABLE_ATTRIBUTE', 141: 'INVALID_DATA_TYPE', 142: 'INVALID_SELECTOR', 143: 'WRITE_ONLY', 144: 'INCONSISTENT_STARTUP_STATE', 145: 'DEFINED_OUT_OF_BAND', 147: 'ACTION_DENIED', 148: 'TIMEOUT', 149: 'ABORT', 150: 'INVALID_IMAGE', 151: 'WAIT_FOR_DATA', 152: 'NO_IMAGE_AVAILABLE', 153: 'REQUIRE_MORE_IMAGE', 154: 'NOTIFICATION_PENDING', 192: 'HARDWARE_FAILURE', 193: 'SOFTWARE_FAILURE', 195: 'UNSUPPORTED_CLUSTER', 196: 'LIMIT_REACHED'}},
                {"name": 'alarm Code', "type": 'u8'},
                {"name": 'cluster Id', "type": 'bytes:4'},
                {"name": 'time Stamp', "type": 'u32'},
            ],
        },
        2: {
            "C→S": [
            ],
        },
        3: {
            "C→S": [
            ],
        },
    },
    # RSSI Location (0x000B) [general.xml]
    0x000B: {
        0: {
            "C→S": [
                {"name": 'coordinate1', "type": 'bytes:4'},
                {"name": 'coordinate2', "type": 'bytes:4'},
                {"name": 'coordinate3', "type": 'bytes:4'},
                {"name": 'power', "type": 'bytes:4'},
                {"name": 'path Loss Exponent', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8', "enum": {0: 'SUCCESS', 1: 'FAILURE', 126: 'NOT_AUTHORIZED', 128: 'MALFORMED_COMMAND', 129: 'UNSUP_COMMAND', 130: 'UNSUP_GENERAL_COMMAND', 131: 'UNSUP_MANUF_CLUSTER_COMMAND', 132: 'UNSUP_MANUF_GENERAL_COMMAND', 133: 'INVALID_FIELD', 134: 'UNSUPPORTED_ATTRIBUTE', 135: 'INVALID_VALUE', 136: 'READ_ONLY', 137: 'INSUFFICIENT_SPACE', 138: 'DUPLICATE_EXISTS', 139: 'NOT_FOUND', 140: 'UNREPORTABLE_ATTRIBUTE', 141: 'INVALID_DATA_TYPE', 142: 'INVALID_SELECTOR', 143: 'WRITE_ONLY', 144: 'INCONSISTENT_STARTUP_STATE', 145: 'DEFINED_OUT_OF_BAND', 147: 'ACTION_DENIED', 148: 'TIMEOUT', 149: 'ABORT', 150: 'INVALID_IMAGE', 151: 'WAIT_FOR_DATA', 152: 'NO_IMAGE_AVAILABLE', 153: 'REQUIRE_MORE_IMAGE', 154: 'NOTIFICATION_PENDING', 192: 'HARDWARE_FAILURE', 193: 'SOFTWARE_FAILURE', 195: 'UNSUPPORTED_CLUSTER', 196: 'LIMIT_REACHED'}},
                {"name": 'power', "type": 'bytes:4'},
                {"name": 'path Loss Exponent', "type": 'u16'},
                {"name": 'calculation Period', "type": 'u16'},
                {"name": 'number Rssi Measurements', "type": 'u8'},
                {"name": 'reporting Period', "type": 'u16'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'power', "type": 'bytes:4'},
                {"name": 'path Loss Exponent', "type": 'u16'},
                {"name": 'calculation Period', "type": 'u16'},
                {"name": 'number Rssi Measurements', "type": 'u8'},
                {"name": 'reporting Period', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8', "enum": {0: 'SUCCESS', 1: 'FAILURE', 126: 'NOT_AUTHORIZED', 128: 'MALFORMED_COMMAND', 129: 'UNSUP_COMMAND', 130: 'UNSUP_GENERAL_COMMAND', 131: 'UNSUP_MANUF_CLUSTER_COMMAND', 132: 'UNSUP_MANUF_GENERAL_COMMAND', 133: 'INVALID_FIELD', 134: 'UNSUPPORTED_ATTRIBUTE', 135: 'INVALID_VALUE', 136: 'READ_ONLY', 137: 'INSUFFICIENT_SPACE', 138: 'DUPLICATE_EXISTS', 139: 'NOT_FOUND', 140: 'UNREPORTABLE_ATTRIBUTE', 141: 'INVALID_DATA_TYPE', 142: 'INVALID_SELECTOR', 143: 'WRITE_ONLY', 144: 'INCONSISTENT_STARTUP_STATE', 145: 'DEFINED_OUT_OF_BAND', 147: 'ACTION_DENIED', 148: 'TIMEOUT', 149: 'ABORT', 150: 'INVALID_IMAGE', 151: 'WAIT_FOR_DATA', 152: 'NO_IMAGE_AVAILABLE', 153: 'REQUIRE_MORE_IMAGE', 154: 'NOTIFICATION_PENDING', 192: 'HARDWARE_FAILURE', 193: 'SOFTWARE_FAILURE', 195: 'UNSUPPORTED_CLUSTER', 196: 'LIMIT_REACHED'}},
                {"name": 'location Type', "type": 'bytes:4'},
                {"name": 'coordinate1', "type": 'bytes:4'},
                {"name": 'coordinate2', "type": 'bytes:4'},
                {"name": 'coordinate3', "type": 'bytes:4'},
                {"name": 'power', "type": 'bytes:4'},
                {"name": 'path Loss Exponent', "type": 'u16'},
                {"name": 'location Method', "type": 'u8', "enum": {0: 'Lateration', 1: 'Signposting', 2: 'Rf Fingerprinting', 3: 'Out Of Band'}},
                {"name": 'quality Measure', "type": 'u8'},
                {"name": 'location Age', "type": 'u16'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'target Address', "type": 'bytes:4'},
            ],
            "S→C": [
                {"name": 'location Type', "type": 'bytes:4'},
                {"name": 'coordinate1', "type": 'bytes:4'},
                {"name": 'coordinate2', "type": 'bytes:4'},
                {"name": 'coordinate3', "type": 'bytes:4'},
                {"name": 'power', "type": 'bytes:4'},
                {"name": 'path Loss Exponent', "type": 'u16'},
                {"name": 'location Method', "type": 'u8', "enum": {0: 'Lateration', 1: 'Signposting', 2: 'Rf Fingerprinting', 3: 'Out Of Band'}},
                {"name": 'quality Measure', "type": 'u8'},
                {"name": 'location Age', "type": 'u16'},
            ],
        },
        3: {
            "C→S": [
                {"name": 'flags', "type": 'bytes:4'},
                {"name": 'number Responses', "type": 'u8'},
                {"name": 'target Address', "type": 'bytes:4'},
            ],
            "S→C": [
                {"name": 'location Type', "type": 'bytes:4'},
                {"name": 'coordinate1', "type": 'bytes:4'},
                {"name": 'coordinate2', "type": 'bytes:4'},
                {"name": 'coordinate3', "type": 'bytes:4'},
                {"name": 'quality Measure', "type": 'u8'},
                {"name": 'location Age', "type": 'u16'},
            ],
        },
        4: {
            "C→S": [
                {"name": 'replying Device', "type": 'bytes:4'},
                {"name": 'coordinate1', "type": 'bytes:4'},
                {"name": 'coordinate2', "type": 'bytes:4'},
                {"name": 'coordinate3', "type": 'bytes:4'},
                {"name": 'rssi', "type": 'bytes:4'},
                {"name": 'number Rssi Measurements', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'location Type', "type": 'bytes:4'},
            ],
        },
        5: {
            "C→S": [
                {"name": 'target Address', "type": 'bytes:4'},
                {"name": 'number Rssi Measurements', "type": 'u8'},
                {"name": 'calculation Period', "type": 'u16'},
            ],
            "S→C": [
            ],
        },
        6: {
            "C→S": [
                {"name": 'anchor Node Ieee Address', "type": 'bytes:4'},
                {"name": 'coordinate1', "type": 'bytes:4'},
                {"name": 'coordinate2', "type": 'bytes:4'},
                {"name": 'coordinate3', "type": 'bytes:4'},
            ],
            "S→C": [
                {"name": 'measuring Device', "type": 'bytes:4'},
                {"name": 'neighbors', "type": 'u8'},
                {"name": 'neighbors Info', "type": 'bytes:4'},
            ],
        },
        7: {
            "S→C": [
                {"name": 'blind Node', "type": 'bytes:4'},
            ],
        },
    },
    # Commissioning (0x0015) [general.xml]
    0x0015: {
        0: {
            "C→S": [
                {"name": 'options', "type": 'bytes:4'},
                {"name": 'delay', "type": 'u8'},
                {"name": 'jitter', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'options', "type": 'bytes:4'},
                {"name": 'index', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'options', "type": 'bytes:4'},
                {"name": 'index', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        3: {
            "C→S": [
                {"name": 'options', "type": 'bytes:4'},
                {"name": 'index', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
    },
    # Partition (0x0016) [ta.xml]
    0x0016: {
        0: {
            "C→S": [
                {"name": 'fragmentation Options', "type": 'bytes:4'},
                {"name": 'partition Indicator', "type": 'bytes:4'},
                {"name": 'partitioned Frame', "type": 'zstr'},
                {"name": 'partitioned Indicator And Frame', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'ack Options', "type": 'bytes:4'},
                {"name": 'first Frame Id', "type": 'bytes:4'},
                {"name": 'nack List', "type": 'bytes:4'},
                {"name": 'first Frame Id And Nack List', "type": 'u8'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'partitioned Cluster Id', "type": 'bytes:4'},
                {"name": 'attribute List', "type": 'bytes:4'},
            ],
            "S→C": [
                {"name": 'partitioned Cluster Id', "type": 'bytes:4'},
                {"name": 'read Attribute Status Records', "type": 'bytes:4'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'partitioned Cluster Id', "type": 'bytes:4'},
                {"name": 'write Attribute Records', "type": 'bytes:4'},
            ],
        },
    },
    # Power Profile (0x001A) [ha.xml]
    0x001A: {
        0: {
            "C→S": [
                {"name": 'power Profile Id', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'total Profile Num', "type": 'u8'},
                {"name": 'power Profile Id', "type": 'u8'},
                {"name": 'num Of Transferred Phases', "type": 'u8'},
                {"name": 'transferred Phases', "type": 'bytes:4'},
            ],
        },
        1: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'total Profile Num', "type": 'u8'},
                {"name": 'power Profile Id', "type": 'u8'},
                {"name": 'num Of Transferred Phases', "type": 'u8'},
                {"name": 'transferred Phases', "type": 'bytes:4'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'power Profile Id', "type": 'u8'},
                {"name": 'currency', "type": 'u16'},
                {"name": 'price', "type": 'u32'},
                {"name": 'price Trailing Digit', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'power Profile Count', "type": 'u8'},
                {"name": 'power Profile Records', "type": 'bytes:4'},
            ],
        },
        3: {
            "C→S": [
                {"name": 'currency', "type": 'u16'},
                {"name": 'price', "type": 'u32'},
                {"name": 'price Trailing Digit', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'power Profile Id', "type": 'u8'},
            ],
        },
        4: {
            "C→S": [
                {"name": 'power Profile Id', "type": 'u8'},
                {"name": 'num Of Scheduled Phases', "type": 'u8'},
                {"name": 'scheduled Phases', "type": 'bytes:4'},
            ],
            "S→C": [
                {"name": 'power Profile Count', "type": 'u8'},
                {"name": 'power Profile Records', "type": 'bytes:4'},
            ],
        },
        5: {
            "C→S": [
                {"name": 'power Profile Id', "type": 'u8'},
                {"name": 'num Of Scheduled Phases', "type": 'u8'},
                {"name": 'scheduled Phases', "type": 'bytes:4'},
            ],
            "S→C": [
            ],
        },
        6: {
            "C→S": [
                {"name": 'power Profile Id', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'power Profile Id', "type": 'u8'},
            ],
        },
        7: {
            "C→S": [
                {"name": 'power Profile Id', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'power Profile Id', "type": 'u8'},
                {"name": 'num Of Scheduled Phases', "type": 'u8'},
                {"name": 'scheduled Phases', "type": 'bytes:4'},
            ],
        },
        8: {
            "C→S": [
                {"name": 'power Profile Id', "type": 'u8'},
                {"name": 'currency', "type": 'u16'},
                {"name": 'price', "type": 'u32'},
                {"name": 'price Trailing Digit', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'power Profile Id', "type": 'u8'},
                {"name": 'num Of Scheduled Phases', "type": 'u8'},
                {"name": 'scheduled Phases', "type": 'bytes:4'},
            ],
        },
        9: {
            "S→C": [
                {"name": 'power Profile Id', "type": 'u8'},
                {"name": 'start After', "type": 'u16'},
                {"name": 'stop Before', "type": 'u16'},
            ],
        },
        10: {
            "S→C": [
                {"name": 'power Profile Id', "type": 'u8'},
                {"name": 'start After', "type": 'u16'},
                {"name": 'stop Before', "type": 'u16'},
            ],
        },
        11: {
            "S→C": [
                {"name": 'options', "type": 'bytes:4'},
                {"name": 'power Profile Id', "type": 'u8'},
                {"name": 'power Profile Start Time', "type": 'u16'},
            ],
        },
    },
    # Appliance Control (0x001B) [ha.xml]
    0x001B: {
        0: {
            "C→S": [
                {"name": 'command Id', "type": 'u8', "enum": {1: 'Start', 2: 'Stop', 3: 'Pause', 4: 'Start Superfreezing', 5: 'Stop Superfreezing', 6: 'Start Supercooling', 7: 'Stop Supercooling', 8: 'Disable Gas', 9: 'Enable Gas', 10: 'Enable Energy Control', 11: 'Disable Energy Control'}},
            ],
            "S→C": [
                {"name": 'appliance Status', "type": 'u8', "enum": {1: 'Off', 2: 'Stand By', 3: 'Programmed', 4: 'Programmed Waiting To Start', 5: 'Running', 6: 'Pause', 7: 'End Programmed', 8: 'Failure', 9: 'Programme Interrupted', 10: 'Idle', 11: 'Rinse Hold', 12: 'Service', 13: 'Superfreezing', 14: 'Supercooling', 15: 'Superheating'}},
                {"name": 'remote Enable Flags And Device Status2', "type": 'bytes:4'},
                {"name": 'appliance Status2', "type": 'u24'},
            ],
        },
        1: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'appliance Status', "type": 'u8', "enum": {1: 'Off', 2: 'Stand By', 3: 'Programmed', 4: 'Programmed Waiting To Start', 5: 'Running', 6: 'Pause', 7: 'End Programmed', 8: 'Failure', 9: 'Programme Interrupted', 10: 'Idle', 11: 'Rinse Hold', 12: 'Service', 13: 'Superfreezing', 14: 'Supercooling', 15: 'Superheating'}},
                {"name": 'remote Enable Flags And Device Status2', "type": 'bytes:4'},
                {"name": 'appliance Status2', "type": 'u24'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'function Id', "type": 'u16'},
                {"name": 'function Data Type', "type": 'u8'},
                {"name": 'function Data', "type": 'u8'},
            ],
        },
        3: {
            "C→S": [
            ],
        },
        4: {
            "C→S": [
            ],
        },
        5: {
            "C→S": [
                {"name": 'warning Event', "type": 'u8', "enum": {0: 'Warning1 Overall Power Above Available Power Level', 1: 'Warning2 Overall Power Above Power Threshold Level', 2: 'Warning3 Overall Power Back Below The Available Power Level', 3: 'Warning4 Overall Power Back Below The Power Threshold Level', 4: 'Warning5 Overall Power Will Be Potentially Above Available Power Level If The Appliance Starts'}},
            ],
        },
    },
    # Poll Control (0x0020) [ha.xml]
    0x0020: {
        0: {
            "S→C": [
            ],
            "C→S": [
                {"name": 'start Fast Polling', "type": 'u8'},
                {"name": 'fast Poll Timeout', "type": 'u16'},
            ],
        },
        1: {
            "C→S": [
            ],
        },
        2: {
            "C→S": [
                {"name": 'new Long Poll Interval', "type": 'u32'},
            ],
        },
        3: {
            "C→S": [
                {"name": 'new Short Poll Interval', "type": 'u16'},
            ],
        },
    },
    # Green Power (0x0021) [green-power.xml]
    0x0021: {
        0: {
            "C→S": [
                {"name": 'options', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Src Id', "type": 'u32', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Ieee', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Endpoint', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Security Frame Counter', "type": 'u32', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Command Id', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Command Payload', "type": 'zstr', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpp Short Address', "type": 'u16', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpp Distance', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
            ],
            "S→C": [
                {"name": 'options', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Src Id', "type": 'u32', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Ieee', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'endpoint', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Security Frame Counter', "type": 'u32', "note": '(gp-1.0-09-5499-24)'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'options', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Src Id', "type": 'u32', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Ieee', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'endpoint', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'options', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Src Id', "type": 'u32', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Ieee', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'endpoint', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'sink Ieee Address', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'sink Nwk Address', "type": 'u16', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'sink Group Id', "type": 'u16', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'device Id', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Security Frame Counter', "type": 'u32', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Key', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'assigned Alias', "type": 'u16', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'groupcast Radius', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
            ],
        },
        2: {
            "S→C": [
                {"name": 'options', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'commissioning Window', "type": 'u16', "note": '(gp-1.0-15-02014-011)'},
                {"name": 'channel', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
            ],
        },
        3: {
            "C→S": [
                {"name": 'options', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Src Id', "type": 'u32', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Ieee', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'endpoint', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Security Frame Counter', "type": 'u32', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpp Short Address', "type": 'u16', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpp Distance', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
            ],
        },
        4: {
            "C→S": [
                {"name": 'options', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Src Id', "type": 'u32', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Ieee', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'endpoint', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Security Frame Counter', "type": 'u32', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Command Id', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Command Payload', "type": 'zstr', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpp Short Address', "type": 'u16', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpp Link', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'mic', "type": 'u32', "note": '(gp-1.0-09-5499-24)'},
            ],
        },
        5: {
            "C→S": [
                {"name": 'options', "type": 'bytes:4'},
                {"name": 'gpm Addr For Security', "type": 'u16'},
                {"name": 'gpm Addr For Pairing', "type": 'u16'},
                {"name": 'sink Endpoint', "type": 'u8'},
            ],
        },
        6: {
            "S→C": [
                {"name": 'options', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'temp Master Short Address', "type": 'u16', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'temp Master Tx Channel', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Src Id', "type": 'u32', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Ieee', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'endpoint', "type": 'u8'},
                {"name": 'gpd Command Id', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Command Payload', "type": 'zstr'},
            ],
        },
        7: {
            "C→S": [
                {"name": 'options', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Src Id', "type": 'u32', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Ieee', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'endpoint', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'translations', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
            ],
        },
        8: {
            "C→S": [
                {"name": 'start Index', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
            ],
            "S→C": [
                {"name": 'status', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'options', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'total Number Of Entries', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'start Index', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'entries Count', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'translation Table List', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
            ],
        },
        9: {
            "C→S": [
                {"name": 'actions', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'options', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Src Id', "type": 'u32', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Ieee', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'endpoint', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'device Id', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'group List Count', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'group List', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Assigned Alias', "type": 'u16', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'groupcast Radius', "type": 'u8', "note": '(gp-1.0-15-2014-05-CCB2180)'},
                {"name": 'security Options', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Security Frame Counter', "type": 'u32', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'gpd Security Key', "type": 'bytes:4', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'number Of Paired Endpoints', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'paired Endpoints', "type": 'u8', "note": '(gp-1.0-09-5499-24)'},
                {"name": 'application Information', "type": 'bytes:4'},
                {"name": 'manufacturer Id', "type": 'u16'},
                {"name": 'mode Id', "type": 'u16'},
                {"name": 'number Of Gpd Commands', "type": 'u8'},
                {"name": 'gpd Command Id List', "type": 'u8'},
                {"name": 'cluster Id List Count', "type": 'u8'},
                {"name": 'cluster List Server', "type": 'u16'},
                {"name": 'cluster List Client', "type": 'u16'},
                {"name": 'switch Information Length', "type": 'u8'},
                {"name": 'switch Configuration', "type": 'u8'},
                {"name": 'current Contact Status', "type": 'u8'},
                {"name": 'total Number Of Reports', "type": 'u8'},
                {"name": 'number Of Reports', "type": 'u8'},
                {"name": 'report Descriptor', "type": 'u8'},
            ],
        },
        10: {
            "C→S": [
                {"name": 'options', "type": 'bytes:4'},
                {"name": 'gpd Src Id', "type": 'u32'},
                {"name": 'gpd Ieee', "type": 'u64'},
                {"name": 'endpoint', "type": 'u8'},
                {"name": 'index', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
                {"name": 'total Numberof Non Empty Sink Table Entries', "type": 'u8'},
                {"name": 'start Index', "type": 'u8'},
                {"name": 'sink Table Entries Count', "type": 'u8'},
                {"name": 'sink Table Entries', "type": 'u8'},
            ],
        },
        11: {
            "C→S": [
                {"name": 'status', "type": 'bytes:4'},
                {"name": 'total Number Of Non Empty Proxy Table Entries', "type": 'u8'},
                {"name": 'start Index', "type": 'u8'},
                {"name": 'entries Count', "type": 'u8'},
                {"name": 'proxy Table Entries', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'options', "type": 'bytes:4'},
                {"name": 'gpd Src Id', "type": 'u32'},
                {"name": 'gpd Ieee', "type": 'u64'},
                {"name": 'endpoint', "type": 'u8'},
                {"name": 'index', "type": 'u8'},
            ],
        },
    },
    # Zigbee Direct Configuration (0x003D) [zigbee-direct.xml]
    0x003D: {
        0: {
            "C→S": [
                {"name": 'Interface State', "type": 'bytes:4'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'Anonymous Join Timeout', "type": 'u24'},
            ],
        },
    },
    # Door Lock (0x0101) [ha.xml]
    0x0101: {
        0: {
            "C→S": [
                {"name": 'PIN', "type": 'zstr', "note": '(ha-1.2-05-3520-29)'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'PIN', "type": 'zstr', "note": '(ha-1.2-05-3520-29)'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'pin', "type": 'zstr', "note": '(ha-1.2-05-3520-29)'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        3: {
            "C→S": [
                {"name": 'timeout In Seconds', "type": 'u16'},
                {"name": 'pin', "type": 'zstr', "note": '(ha-1.2-05-3520-29)'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        4: {
            "C→S": [
                {"name": 'log Index', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'log Entry Id', "type": 'u16'},
                {"name": 'timestamp', "type": 'u32'},
                {"name": 'event Type', "type": 'u8'},
                {"name": 'source', "type": 'u8'},
                {"name": 'event Id Or Alarm Code', "type": 'u8'},
                {"name": 'user Id', "type": 'u16'},
                {"name": 'pin', "type": 'zstr'},
            ],
        },
        5: {
            "C→S": [
                {"name": 'user Id', "type": 'u16'},
                {"name": 'user Status', "type": 'u8', "enum": {0: 'Available', 1: 'Occupied Enabled', 3: 'Occupied Disabled', 255: 'Not Supported'}},
                {"name": 'user Type', "type": 'u8', "enum": {0: 'Unrestricted', 1: 'Year Day Schedule User', 2: 'Week Day Schedule User', 3: 'Master User', 4: 'Non Access User', 5: 'Coerced User', 6: 'Disposable User', 255: 'Not Supported'}},
                {"name": 'pin', "type": 'zstr'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8', "enum": {0: 'Success', 1: 'General Failure', 2: 'Memory Full', 3: 'Duplicate Code Error'}},
            ],
        },
        6: {
            "C→S": [
                {"name": 'user Id', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'user Id', "type": 'u16'},
                {"name": 'user Status', "type": 'u8', "enum": {0: 'Available', 1: 'Occupied Enabled', 3: 'Occupied Disabled', 255: 'Not Supported'}},
                {"name": 'user Type', "type": 'u8', "enum": {0: 'Unrestricted', 1: 'Year Day Schedule User', 2: 'Week Day Schedule User', 3: 'Master User', 4: 'Non Access User', 5: 'Coerced User', 6: 'Disposable User', 255: 'Not Supported'}},
                {"name": 'pin', "type": 'zstr'},
            ],
        },
        7: {
            "C→S": [
                {"name": 'user Id', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        8: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        9: {
            "C→S": [
                {"name": 'user Id', "type": 'u16'},
                {"name": 'user Status', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        10: {
            "C→S": [
                {"name": 'user Id', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'user Id', "type": 'u16'},
                {"name": 'status', "type": 'u8'},
            ],
        },
        11: {
            "C→S": [
                {"name": 'schedule Id', "type": 'u8'},
                {"name": 'user Id', "type": 'u16'},
                {"name": 'days Mask', "type": 'bytes:4'},
                {"name": 'start Hour', "type": 'u8'},
                {"name": 'start Minute', "type": 'u8'},
                {"name": 'end Hour', "type": 'u8'},
                {"name": 'end Minute', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        12: {
            "C→S": [
                {"name": 'schedule Id', "type": 'u8'},
                {"name": 'user Id', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'schedule Id', "type": 'u8'},
                {"name": 'user Id', "type": 'u16'},
                {"name": 'status', "type": 'u8'},
                {"name": 'days Mask', "type": 'u8', "note": '(ha-1.2-05-3520-29)'},
                {"name": 'start Hour', "type": 'u8', "note": '(ha-1.2-05-3520-29)'},
                {"name": 'start Minute', "type": 'u8', "note": '(ha-1.2-05-3520-29)'},
                {"name": 'end Hour', "type": 'u8', "note": '(ha-1.2-05-3520-29)'},
                {"name": 'end Minute', "type": 'u8', "note": '(ha-1.2-05-3520-29)'},
            ],
        },
        13: {
            "C→S": [
                {"name": 'schedule Id', "type": 'u8'},
                {"name": 'user Id', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        14: {
            "C→S": [
                {"name": 'schedule Id', "type": 'u8'},
                {"name": 'user Id', "type": 'u16'},
                {"name": 'local Start Time', "type": 'u32'},
                {"name": 'local End Time', "type": 'u32'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        15: {
            "C→S": [
                {"name": 'schedule Id', "type": 'u8'},
                {"name": 'user Id', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'schedule Id', "type": 'u8'},
                {"name": 'user Id', "type": 'u16'},
                {"name": 'status', "type": 'u8'},
                {"name": 'local Start Time', "type": 'u32', "note": '(ha-1.2-05-3520-29)'},
                {"name": 'local End Time', "type": 'u32', "note": '(ha-1.2-05-3520-29)'},
            ],
        },
        16: {
            "C→S": [
                {"name": 'schedule Id', "type": 'u8'},
                {"name": 'user Id', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        17: {
            "C→S": [
                {"name": 'schedule Id', "type": 'u8'},
                {"name": 'local Start Time', "type": 'u32'},
                {"name": 'local End Time', "type": 'u32'},
                {"name": 'operating Mode During Holiday', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        18: {
            "C→S": [
                {"name": 'schedule Id', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'schedule Id', "type": 'u8'},
                {"name": 'status', "type": 'u8'},
                {"name": 'local Start Time', "type": 'u32', "note": '(ha-1.2-05-3520-29)'},
                {"name": 'local End Time', "type": 'u32', "note": '(ha-1.2-05-3520-29)'},
                {"name": 'operating Mode During Holiday', "type": 'u8', "note": '(ha-1.2-05-3520-29)'},
            ],
        },
        19: {
            "C→S": [
                {"name": 'schedule Id', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        20: {
            "C→S": [
                {"name": 'user Id', "type": 'u16'},
                {"name": 'user Type', "type": 'u8', "enum": {0: 'Unrestricted', 1: 'Year Day Schedule User', 2: 'Week Day Schedule User', 3: 'Master User', 4: 'Non Access User', 5: 'Coerced User', 6: 'Disposable User', 255: 'Not Supported'}},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        21: {
            "C→S": [
                {"name": 'user Id', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'user Id', "type": 'u16'},
                {"name": 'user Type', "type": 'u8', "enum": {0: 'Unrestricted', 1: 'Year Day Schedule User', 2: 'Week Day Schedule User', 3: 'Master User', 4: 'Non Access User', 5: 'Coerced User', 6: 'Disposable User', 255: 'Not Supported'}},
            ],
        },
        22: {
            "C→S": [
                {"name": 'user Id', "type": 'u16'},
                {"name": 'user Status', "type": 'u8', "enum": {0: 'Available', 1: 'Occupied Enabled', 3: 'Occupied Disabled', 255: 'Not Supported'}},
                {"name": 'user Type', "type": 'u8', "enum": {0: 'Unrestricted', 1: 'Year Day Schedule User', 2: 'Week Day Schedule User', 3: 'Master User', 4: 'Non Access User', 5: 'Coerced User', 6: 'Disposable User', 255: 'Not Supported'}},
                {"name": 'id', "type": 'zstr'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8', "enum": {0: 'Success', 1: 'General Failure', 2: 'Memory Full', 3: 'Duplicate Code Error'}},
            ],
        },
        23: {
            "C→S": [
                {"name": 'user Id', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'user Id', "type": 'u16'},
                {"name": 'user Status', "type": 'u8', "enum": {0: 'Available', 1: 'Occupied Enabled', 3: 'Occupied Disabled', 255: 'Not Supported'}},
                {"name": 'user Type', "type": 'u8', "enum": {0: 'Unrestricted', 1: 'Year Day Schedule User', 2: 'Week Day Schedule User', 3: 'Master User', 4: 'Non Access User', 5: 'Coerced User', 6: 'Disposable User', 255: 'Not Supported'}},
                {"name": 'rfid', "type": 'zstr'},
            ],
        },
        24: {
            "C→S": [
                {"name": 'user Id', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        25: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        26: {
            "C→S": [
                {"name": 'user Id', "type": 'u16'},
                {"name": 'local Start Time', "type": 'u32'},
                {"name": 'local End Time', "type": 'u32'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        27: {
            "C→S": [
                {"name": 'user Id', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'user Id', "type": 'u16'},
                {"name": 'status', "type": 'u8'},
                {"name": 'local Start Time', "type": 'u32'},
                {"name": 'local End Time', "type": 'u32'},
            ],
        },
        28: {
            "C→S": [
                {"name": 'user Id', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        29: {
            "C→S": [
                {"name": 'user Id', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        30: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
            ],
        },
        32: {
            "S→C": [
                {"name": 'source', "type": 'u8'},
                {"name": 'event Code', "type": 'u8', "enum": {0: 'Unknown Or Mfg Specific', 1: 'Lock', 2: 'Unlock', 3: 'Lock Invalid Pin Or Id', 4: 'Lock Invalid Schedule', 5: 'Unlock Invalid Pin Or Id', 6: 'Unlock Invalid Schedule', 7: 'One Touch Lock', 8: 'Key Lock', 9: 'Key Unlock', 10: 'Auto Lock', 11: 'Schedule Lock', 12: 'Schedule Unlock', 13: 'Manual Lock', 14: 'Manual Unlock', 16: 'Unlock Coerced User', 17: 'Fingerpint Unlock', 18: 'Face ID Unlock', 19: 'Fingervein Unlock', 20: 'Auto Unlock', 21: 'Application Unlock', 22: 'Unlock Disposable User'}},
                {"name": 'user Id', "type": 'u16'},
                {"name": 'pin', "type": 'zstr'},
                {"name": 'time Stamp', "type": 'u32'},
                {"name": 'data', "type": 'zstr', "note": '(ha-1.2-05-3520-29)'},
            ],
        },
        33: {
            "S→C": [
                {"name": 'source', "type": 'u8'},
                {"name": 'event Code', "type": 'u8', "enum": {0: 'Unknown Or Mfg Specific', 1: 'Master Code Changed', 2: 'Pin Added', 3: 'Pin Deleted', 4: 'Pin Changed', 5: 'Id Added', 6: 'Id Deleted', 7: 'Fingerprint Added', 8: 'Fingerprint Deleted', 9: 'Face Id Added', 10: 'Face Id Deleted', 11: 'Fingervein Added', 12: 'Fingervein Deleted'}},
                {"name": 'user Id', "type": 'u16'},
                {"name": 'pin', "type": 'zstr'},
                {"name": 'user Type', "type": 'u8', "enum": {0: 'Unrestricted', 1: 'Year Day Schedule User', 2: 'Week Day Schedule User', 3: 'Master User', 4: 'Non Access User', 5: 'Coerced User', 6: 'Disposable User', 255: 'Not Supported'}},
                {"name": 'user Status', "type": 'u8', "enum": {0: 'Available', 1: 'Occupied Enabled', 3: 'Occupied Disabled', 255: 'Not Supported'}},
                {"name": 'time Stamp', "type": 'u32'},
                {"name": 'data', "type": 'zstr', "note": '(ha-1.2-05-3520-29)'},
            ],
        },
    },
    # Window Covering (0x0102) [ha.xml]
    0x0102: {
        0: {
            "C→S": [
            ],
        },
        1: {
            "C→S": [
            ],
        },
        2: {
            "C→S": [
            ],
        },
        4: {
            "C→S": [
                {"name": 'lift Value', "type": 'u16'},
            ],
        },
        5: {
            "C→S": [
                {"name": 'percentage Lift Value', "type": 'u8'},
            ],
        },
        7: {
            "C→S": [
                {"name": 'tilt Value', "type": 'u16'},
            ],
        },
        8: {
            "C→S": [
                {"name": 'percentage Tilt Value', "type": 'u8'},
            ],
        },
    },
    # Barrier Control (0x0103) [ha.xml]
    0x0103: {
        0: {
            "C→S": [
                {"name": 'percent Open', "type": 'u8'},
            ],
        },
        1: {
            "C→S": [
            ],
        },
    },
    # Thermostat (0x0201) [ha.xml]
    0x0201: {
        0: {
            "C→S": [
                {"name": 'mode', "type": 'u8', "enum": {0: 'heat Setpoint', 1: 'cool Setpoint', 2: 'heat And Cool Setpoints'}},
                {"name": 'amount', "type": 'bytes:4'},
            ],
            "S→C": [
                {"name": 'number Of Transitions For Sequence', "type": 'u8'},
                {"name": 'day Of Week For Sequence', "type": 'bytes:4'},
                {"name": 'mode For Sequence', "type": 'bytes:4'},
                {"name": 'payload', "type": 'u8'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'number Of Transitions For Sequence', "type": 'u8'},
                {"name": 'day Of Week For Sequence', "type": 'bytes:4'},
                {"name": 'mode For Sequence', "type": 'bytes:4'},
                {"name": 'payload', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'time Of Day', "type": 'u16'},
                {"name": 'relay Status', "type": 'bytes:4'},
                {"name": 'local Temperature', "type": 'bytes:4'},
                {"name": 'humidity In Percentage', "type": 'u8'},
                {"name": 'setpoint', "type": 'bytes:4'},
                {"name": 'unread Entries', "type": 'u16'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'days To Return', "type": 'bytes:4'},
                {"name": 'mode To Return', "type": 'bytes:4'},
            ],
        },
        3: {
            "C→S": [
            ],
        },
        4: {
            "C→S": [
            ],
        },
    },
    # Color Control (0x0300) [ha.xml]
    0x0300: {
        0: {
            "C→S": [
                {"name": 'hue', "type": 'u8'},
                {"name": 'direction', "type": 'u8', "enum": {0: 'Shortest Distance', 1: 'Longest Distance', 2: 'Up', 3: 'Down'}},
                {"name": 'transition Time', "type": 'u16'},
                {"name": 'options Mask', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
                {"name": 'options Override', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'move Mode', "type": 'u8', "enum": {0: 'stop', 1: 'Up', 3: 'Down'}},
                {"name": 'rate', "type": 'u8'},
                {"name": 'options Mask', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
                {"name": 'options Override', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'step Mode', "type": 'u8', "enum": {1: 'Up', 3: 'Down'}},
                {"name": 'step Size', "type": 'u8'},
                {"name": 'transition Time', "type": 'u8'},
                {"name": 'options Mask', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
                {"name": 'options Override', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
            ],
        },
        3: {
            "C→S": [
                {"name": 'saturation', "type": 'u8'},
                {"name": 'transition Time', "type": 'u16'},
                {"name": 'options Mask', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
                {"name": 'options Override', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
            ],
        },
        4: {
            "C→S": [
                {"name": 'move Mode', "type": 'u8', "enum": {0: 'stop', 1: 'Up', 3: 'Down'}},
                {"name": 'rate', "type": 'u8'},
                {"name": 'options Mask', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
                {"name": 'options Override', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
            ],
        },
        5: {
            "C→S": [
                {"name": 'step Mode', "type": 'u8', "enum": {1: 'Up', 3: 'Down'}},
                {"name": 'step Size', "type": 'u8'},
                {"name": 'transition Time', "type": 'u8'},
                {"name": 'options Mask', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
                {"name": 'options Override', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
            ],
        },
        6: {
            "C→S": [
                {"name": 'hue', "type": 'u8'},
                {"name": 'saturation', "type": 'u8'},
                {"name": 'transition Time', "type": 'u16'},
                {"name": 'options Mask', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
                {"name": 'options Override', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
            ],
        },
        7: {
            "C→S": [
                {"name": 'color X', "type": 'u16'},
                {"name": 'color Y', "type": 'u16'},
                {"name": 'transition Time', "type": 'u16'},
                {"name": 'options Mask', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
                {"name": 'options Override', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
            ],
        },
        8: {
            "C→S": [
                {"name": 'rate X', "type": 'bytes:4'},
                {"name": 'rate Y', "type": 'bytes:4'},
                {"name": 'options Mask', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
                {"name": 'options Override', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
            ],
        },
        9: {
            "C→S": [
                {"name": 'step X', "type": 'bytes:4'},
                {"name": 'step Y', "type": 'bytes:4'},
                {"name": 'transition Time', "type": 'u16'},
                {"name": 'options Mask', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
                {"name": 'options Override', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
            ],
        },
        10: {
            "C→S": [
                {"name": 'color Temperature', "type": 'u16'},
                {"name": 'transition Time', "type": 'u16'},
                {"name": 'options Mask', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
                {"name": 'options Override', "type": 'bytes:4', "note": '(zcl6-errata-14-0129-15)'},
            ],
        },
    },
    # IAS Zone (0x0500) [ha.xml]
    0x0500: {
        0: {
            "C→S": [
                {"name": 'enroll Response Code', "type": 'u8', "enum": {0: 'success', 1: 'not Supported', 2: 'no Enroll Permit', 3: 'too Many Zones'}},
                {"name": 'zone Id', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'zone Status', "type": 'bytes:4'},
                {"name": 'extended Status', "type": 'bytes:4'},
                {"name": 'zone Id', "type": 'u8', "note": '(ha-1.2-05-3520-29)'},
                {"name": 'delay', "type": 'u16', "note": '(ha-1.2-05-3520-29)'},
            ],
        },
        1: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'zone Type', "type": 'u16', "enum": {0: 'standard Cie', 13: 'motion Sensor', 21: 'contact Switch', 40: 'fire Sensor', 42: 'water Sensor', 43: 'gas Sensor', 44: 'personal Emergency Device', 45: 'vibration Movement Sensor', 271: 'remote Control', 277: 'key Fob', 541: 'keypad', 549: 'standard Warning Device', 550: 'glass Break Sensor', 551: 'carbon Monoxide Sensor', 553: 'security Repeater', 65535: 'invalid Zone Type'}},
                {"name": 'manufacturer Code', "type": 'u16'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'test Mode Duration', "type": 'u8'},
                {"name": 'current Zone Sensitivity Level', "type": 'u8'},
            ],
            "S→C": [
            ],
        },
        3: {
            "S→C": [
            ],
        },
    },
    # IAS ACE (0x0501) [ha.xml]
    0x0501: {
        0: {
            "C→S": [
                {"name": 'arm Mode', "type": 'u8', "enum": {0: 'disarm', 1: 'arm Day Home Zones Only', 2: 'arm Night Sleep Zones Only', 3: 'arm All Zones'}},
                {"name": 'arm Disarm Code', "type": 'zstr', "note": '(ha-1.2-05-3520-29)'},
                {"name": 'zone Id', "type": 'u8', "note": '(ha-1.2-05-3520-29)'},
            ],
            "S→C": [
                {"name": 'arm Notification', "type": 'u8', "enum": {0: 'all Zones Disarmed', 1: 'only Day Home Zones Armed', 2: 'only Night Sleep Zones Armed', 3: 'all Zones Armed', 4: 'invalid Arm Disarm Code', 5: 'not Ready To Arm', 6: 'already Disarmed'}},
            ],
        },
        1: {
            "C→S": [
                {"name": 'number Of Zones', "type": 'u8'},
                {"name": 'zone Ids', "type": 'u8'},
                {"name": 'arm Disarm Code', "type": 'zstr', "note": '(ha-1.2.1-05-3520-30)'},
            ],
            "S→C": [
                {"name": 'section0', "type": 'bytes:4'},
                {"name": 'section1', "type": 'bytes:4'},
                {"name": 'section2', "type": 'bytes:4'},
                {"name": 'section3', "type": 'bytes:4'},
                {"name": 'section4', "type": 'bytes:4'},
                {"name": 'section5', "type": 'bytes:4'},
                {"name": 'section6', "type": 'bytes:4'},
                {"name": 'section7', "type": 'bytes:4'},
                {"name": 'section8', "type": 'bytes:4'},
                {"name": 'section9', "type": 'bytes:4'},
                {"name": 'section10', "type": 'bytes:4'},
                {"name": 'section11', "type": 'bytes:4'},
                {"name": 'section12', "type": 'bytes:4'},
                {"name": 'section13', "type": 'bytes:4'},
                {"name": 'section14', "type": 'bytes:4'},
                {"name": 'section15', "type": 'bytes:4'},
            ],
        },
        2: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'zone Id', "type": 'u8'},
                {"name": 'zone Type', "type": 'u16', "enum": {0: 'standard Cie', 13: 'motion Sensor', 21: 'contact Switch', 40: 'fire Sensor', 42: 'water Sensor', 43: 'gas Sensor', 44: 'personal Emergency Device', 45: 'vibration Movement Sensor', 271: 'remote Control', 277: 'key Fob', 541: 'keypad', 549: 'standard Warning Device', 550: 'glass Break Sensor', 551: 'carbon Monoxide Sensor', 553: 'security Repeater', 65535: 'invalid Zone Type'}},
                {"name": 'ieee Address', "type": 'bytes:4'},
                {"name": 'zone Label', "type": 'zstr', "note": '(ha-1.2.1-05-3520-30)'},
            ],
        },
        3: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'zone Id', "type": 'u8'},
                {"name": 'zone Status', "type": 'u16'},
                {"name": 'audible Notification', "type": 'u8', "enum": {0: 'mute', 1: 'default Sound'}, "note": '(ha-1.2.1-05-3520-30)'},
                {"name": 'zone Label', "type": 'zstr', "note": '(ha-1.2.1-05-3520-30)'},
            ],
        },
        4: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'panel Status', "type": 'u8', "enum": {0: 'panel Disarmed', 1: 'armed Stay', 2: 'armed Night', 3: 'armed Away', 4: 'exit Delay', 5: 'entry Delay', 6: 'not Ready To Arm', 7: 'in Alarm', 8: 'arming Stay', 9: 'arming Night', 10: 'arming Away'}},
                {"name": 'seconds Remaining', "type": 'u8'},
                {"name": 'audible Notification', "type": 'u8', "enum": {0: 'mute', 1: 'default Sound'}, "note": '(ha-1.2.1-05-3520-30)'},
                {"name": 'alarm Status', "type": 'u8', "enum": {0: 'no Alarm', 1: 'burglar', 2: 'fire', 3: 'emergency', 4: 'police Panic', 5: 'fire Panic', 6: 'emergency Panic'}, "note": '(ha-1.2.1-05-3520-30)'},
            ],
        },
        5: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'panel Status', "type": 'u8', "enum": {0: 'panel Disarmed', 1: 'armed Stay', 2: 'armed Night', 3: 'armed Away', 4: 'exit Delay', 5: 'entry Delay', 6: 'not Ready To Arm', 7: 'in Alarm', 8: 'arming Stay', 9: 'arming Night', 10: 'arming Away'}},
                {"name": 'seconds Remaining', "type": 'u8'},
                {"name": 'audible Notification', "type": 'u8', "enum": {0: 'mute', 1: 'default Sound'}},
                {"name": 'alarm Status', "type": 'u8', "enum": {0: 'no Alarm', 1: 'burglar', 2: 'fire', 3: 'emergency', 4: 'police Panic', 5: 'fire Panic', 6: 'emergency Panic'}},
            ],
        },
        6: {
            "C→S": [
                {"name": 'zone Id', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'number Of Zones', "type": 'u8'},
                {"name": 'zone Ids', "type": 'u8'},
            ],
        },
        7: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'number Of Zones', "type": 'u8'},
                {"name": 'bypass Result', "type": 'u8', "enum": {0: 'zone Bypassed', 1: 'zone Not Bypassed', 2: 'not Allowed', 3: 'invalid Zone Id', 4: 'unknown Zone Id', 5: 'invalid Arm Disarm Code'}},
            ],
        },
        8: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'zone Status Complete', "type": 'u8'},
                {"name": 'number Of Zones', "type": 'u8'},
                {"name": 'zone Status Result', "type": 'bytes:4'},
            ],
        },
        9: {
            "C→S": [
                {"name": 'starting Zone Id', "type": 'u8'},
                {"name": 'max Number Of Zone Ids', "type": 'u8'},
                {"name": 'zone Status Mask Flag', "type": 'u8'},
                {"name": 'zone Status Mask', "type": 'bytes:4'},
            ],
        },
    },
    # IAS WD (0x0502) [ha.xml]
    0x0502: {
        0: {
            "C→S": [
                {"name": 'warning Info', "type": 'bytes:4'},
                {"name": 'warning Duration', "type": 'u16'},
                {"name": 'strobe Duty Cycle', "type": 'u8', "note": '(ha-1.2-05-3520-29)'},
                {"name": 'strobe Level', "type": 'u8', "note": '(ha-1.2-05-3520-29)'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'squawk Info', "type": 'bytes:4'},
            ],
        },
    },
    # Generic Tunnel (0x0600) [cba.xml]
    0x0600: {
        0: {
            "C→S": [
                {"name": 'protocol Address', "type": 'zstr'},
            ],
            "S→C": [
                {"name": 'device Ieee Address', "type": 'bytes:4'},
                {"name": 'protocol Address', "type": 'zstr'},
            ],
        },
        1: {
            "S→C": [
                {"name": 'protocol Address', "type": 'zstr'},
            ],
        },
    },
    # BACnet Protocol Tunnel (0x0601) [cba.xml]
    0x0601: {
        0: {
            "C→S": [
                {"name": 'npdu', "type": 'bytes:4'},
            ],
        },
    },
    # 11073 Protocol Tunnel (0x0614) [hc.xml]
    0x0614: {
        0: {
            "C→S": [
                {"name": 'apdu', "type": 'zstr'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'connect Control', "type": 'bytes:4'},
                {"name": 'idle Timeout', "type": 'u16'},
                {"name": 'manager Target', "type": 'bytes:4'},
                {"name": 'manager Endpoint', "type": 'u8'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'manager IEEE Address', "type": 'bytes:4'},
            ],
        },
        3: {
            "C→S": [
                {"name": 'connect Status', "type": 'bytes:4'},
            ],
        },
    },
    # ISO 7816 Protocol Tunnel (0x0615) [ta.xml]
    0x0615: {
        0: {
            "C→S": [
                {"name": 'apdu', "type": 'zstr'},
            ],
            "S→C": [
                {"name": 'apdu', "type": 'zstr'},
            ],
        },
        1: {
            "C→S": [
            ],
        },
        2: {
            "C→S": [
            ],
        },
    },
    # Price (0x0700) [ami.xml]
    0x0700: {
        0: {
            "S→C": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'rate Label', "type": 'zstr'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'current Time', "type": 'bytes:4'},
                {"name": 'unit Of Measure', "type": 'bytes:4'},
                {"name": 'currency', "type": 'u16'},
                {"name": 'price Trailing Digit And Price Tier', "type": 'bytes:4'},
                {"name": 'number Of Price Tiers And Register Tier', "type": 'bytes:4'},
                {"name": 'start Time', "type": 'bytes:4'},
                {"name": 'duration In Minutes', "type": 'u16'},
                {"name": 'price', "type": 'u32'},
                {"name": 'price Ratio', "type": 'u8'},
                {"name": 'generation Price', "type": 'u32'},
                {"name": 'generation Price Ratio', "type": 'u8'},
                {"name": 'alternate Cost Delivered', "type": 'u32', "note": '(se-1.0-07-5356-15)'},
                {"name": 'alternate Cost Unit', "type": 'bytes:4', "note": '(se-1.0-07-5356-15)'},
                {"name": 'alternate Cost Trailing Digit', "type": 'bytes:4', "note": '(se-1.0-07-5356-15)'},
                {"name": 'number Of Block Thresholds', "type": 'u8', "note": '(se-1.1-07-5356-16)'},
                {"name": 'price Control', "type": 'bytes:4', "note": '(se-1.1-07-5356-16)'},
                {"name": 'number Of Generation Tiers', "type": 'u8', "note": '(se-1.2a-07-5356-19)'},
                {"name": 'generation Tier', "type": 'bytes:4', "note": '(se-1.2a-07-5356-19)'},
                {"name": 'extended Number Of Price Tiers', "type": 'bytes:4', "note": '(se-1.2a-07-5356-19)'},
                {"name": 'extended Price Tier', "type": 'bytes:4', "note": '(se-1.2a-07-5356-19)'},
                {"name": 'extended Register Tier', "type": 'bytes:4', "note": '(se-1.2a-07-5356-19)'},
            ],
            "C→S": [
                {"name": 'command Options', "type": 'bytes:4'},
            ],
        },
        1: {
            "S→C": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'block Period Start Time', "type": 'bytes:4'},
                {"name": 'block Period Duration', "type": 'u24'},
                {"name": 'number Of Price Tiers And Number Of Block Thresholds', "type": 'bytes:4'},
                {"name": 'block Period Control', "type": 'bytes:4'},
                {"name": 'block Period Duration Type', "type": 'bytes:4', "note": '(se-1.2a-07-5356-19)'},
                {"name": 'tariff Type', "type": 'bytes:4', "note": '(se-1.2a-07-5356-19)'},
                {"name": 'tariff Resolution Period', "type": 'bytes:4', "note": '(se-1.2a-07-5356-19)'},
            ],
            "C→S": [
                {"name": 'start Time', "type": 'bytes:4'},
                {"name": 'number Of Events', "type": 'u8'},
            ],
        },
        2: {
            "S→C": [
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'start Time', "type": 'bytes:4'},
                {"name": 'conversion Factor', "type": 'u32'},
                {"name": 'conversion Factor Trailing Digit', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'price Ack Time', "type": 'bytes:4'},
                {"name": 'control', "type": 'bytes:4'},
            ],
        },
        3: {
            "S→C": [
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'start Time', "type": 'bytes:4'},
                {"name": 'calorific Value', "type": 'u32'},
                {"name": 'calorific Value Unit', "type": 'bytes:4'},
                {"name": 'calorific Value Trailing Digit', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'start Time', "type": 'bytes:4'},
                {"name": 'number Of Events', "type": 'u8'},
                {"name": 'tariff Type', "type": 'bytes:4'},
            ],
        },
        4: {
            "S→C": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'issuer Tariff Id', "type": 'u32'},
                {"name": 'start Time', "type": 'bytes:4'},
                {"name": 'tariff Type Charging Scheme', "type": 'bytes:4'},
                {"name": 'tariff Label', "type": 'zstr'},
                {"name": 'number Of Price Tiers In Use', "type": 'u8'},
                {"name": 'number Of Block Thresholds In Use', "type": 'u8'},
                {"name": 'unit Of Measure', "type": 'bytes:4'},
                {"name": 'currency', "type": 'u16'},
                {"name": 'price Trailing Digit', "type": 'bytes:4'},
                {"name": 'standing Charge', "type": 'u32'},
                {"name": 'tier Block Mode', "type": 'bytes:4'},
                {"name": 'block Threshold Multiplier', "type": 'u24'},
                {"name": 'block Threshold Divisor', "type": 'u24'},
            ],
            "C→S": [
                {"name": 'earliest Start Time', "type": 'bytes:4'},
                {"name": 'min Issuer Event Id', "type": 'u32'},
                {"name": 'number Of Commands', "type": 'u8'},
            ],
        },
        5: {
            "S→C": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'start Time', "type": 'bytes:4'},
                {"name": 'issuer Tariff Id', "type": 'u32'},
                {"name": 'command Index', "type": 'u8'},
                {"name": 'number Of Commands', "type": 'u8'},
                {"name": 'sub Payload Control', "type": 'bytes:4'},
                {"name": 'payload', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'earliest Start Time', "type": 'bytes:4'},
                {"name": 'min Issuer Event Id', "type": 'u32'},
                {"name": 'number Of Commands', "type": 'u8'},
            ],
        },
        6: {
            "S→C": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'start Time', "type": 'bytes:4'},
                {"name": 'issuer Tariff Id', "type": 'u32'},
                {"name": 'command Index', "type": 'u8'},
                {"name": 'number Of Commands', "type": 'u8'},
                {"name": 'sub Payload Control', "type": 'bytes:4'},
                {"name": 'payload', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'earliest Start Time', "type": 'bytes:4'},
                {"name": 'min Issuer Event Id', "type": 'u32'},
                {"name": 'number Of Commands', "type": 'u8'},
                {"name": 'tariff Type', "type": 'bytes:4'},
            ],
        },
        7: {
            "S→C": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'start Time', "type": 'bytes:4'},
                {"name": 'tariff Type', "type": 'bytes:4'},
                {"name": 'c O2 Value', "type": 'u32'},
                {"name": 'c O2 Value Unit', "type": 'bytes:4'},
                {"name": 'c O2 Value Trailing Digit', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'issuer Tariff Id', "type": 'u32'},
            ],
        },
        8: {
            "S→C": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'issuer Tariff Id', "type": 'u32'},
                {"name": 'command Index', "type": 'u8'},
                {"name": 'number Of Commands', "type": 'u8'},
                {"name": 'number Of Labels', "type": 'u8'},
                {"name": 'tier Labels Payload', "type": 'u8'},
            ],
            "C→S": [
                {"name": 'issuer Tariff Id', "type": 'u32'},
            ],
        },
        9: {
            "S→C": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'billing Period Start Time', "type": 'bytes:4'},
                {"name": 'billing Period Duration', "type": 'bytes:4'},
                {"name": 'billing Period Duration Type', "type": 'bytes:4'},
                {"name": 'tariff Type', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'earliest Start Time', "type": 'bytes:4'},
                {"name": 'min Issuer Event Id', "type": 'u32'},
                {"name": 'number Of Commands', "type": 'u8'},
                {"name": 'tariff Type', "type": 'bytes:4'},
            ],
        },
        10: {
            "S→C": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'billing Period Start Time', "type": 'bytes:4'},
                {"name": 'billing Period Duration', "type": 'bytes:4'},
                {"name": 'billing Period Duration Type', "type": 'bytes:4'},
                {"name": 'tariff Type', "type": 'bytes:4'},
                {"name": 'consolidated Bill', "type": 'u32'},
                {"name": 'currency', "type": 'u16'},
                {"name": 'bill Trailing Digit', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'issuer Tariff Id', "type": 'u32'},
            ],
        },
        11: {
            "S→C": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'start Time', "type": 'bytes:4'},
                {"name": 'duration In Minutes', "type": 'u16'},
                {"name": 'tariff Type', "type": 'bytes:4'},
                {"name": 'cpp Price Tier', "type": 'bytes:4'},
                {"name": 'cpp Auth', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'earliest Start Time', "type": 'bytes:4'},
                {"name": 'min Issuer Event Id', "type": 'u32'},
                {"name": 'number Of Commands', "type": 'u8'},
                {"name": 'tariff Type', "type": 'bytes:4'},
            ],
        },
        12: {
            "S→C": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'credit Payment Due Date', "type": 'bytes:4'},
                {"name": 'credit Payment Over Due Amount', "type": 'u32'},
                {"name": 'credit Payment Status', "type": 'bytes:4'},
                {"name": 'credit Payment', "type": 'u32'},
                {"name": 'credit Payment Date', "type": 'bytes:4'},
                {"name": 'credit Payment Ref', "type": 'zstr'},
            ],
            "C→S": [
                {"name": 'earliest Start Time', "type": 'bytes:4'},
                {"name": 'min Issuer Event Id', "type": 'u32'},
                {"name": 'number Of Commands', "type": 'u8'},
                {"name": 'tariff Type', "type": 'bytes:4'},
            ],
        },
        13: {
            "S→C": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'start Time', "type": 'bytes:4'},
                {"name": 'old Currency', "type": 'u16'},
                {"name": 'new Currency', "type": 'u16'},
                {"name": 'conversion Factor', "type": 'u32'},
                {"name": 'conversion Factor Trailing Digit', "type": 'bytes:4'},
                {"name": 'currency Change Control Flags', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'cpp Auth', "type": 'bytes:4'},
            ],
        },
        14: {
            "S→C": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Tariff Id', "type": 'u32'},
                {"name": 'tariff Type', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'latest End Time', "type": 'bytes:4'},
                {"name": 'number Of Records', "type": 'u8'},
            ],
        },
        15: {
            "C→S": [
            ],
        },
        16: {
            "C→S": [
            ],
        },
    },
    # Demand Response and Load Control (0x0701) [ami.xml]
    0x0701: {
        0: {
            "S→C": [
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'device Class', "type": 'bytes:4'},
                {"name": 'utility Enrollment Group', "type": 'u8'},
                {"name": 'start Time', "type": 'bytes:4'},
                {"name": 'duration In Minutes', "type": 'u16'},
                {"name": 'criticality Level', "type": 'bytes:4'},
                {"name": 'cooling Temperature Offset', "type": 'u8'},
                {"name": 'heating Temperature Offset', "type": 'u8'},
                {"name": 'cooling Temperature Set Point', "type": 'bytes:4'},
                {"name": 'heating Temperature Set Point', "type": 'bytes:4'},
                {"name": 'average Load Adjustment Percentage', "type": 'bytes:4'},
                {"name": 'duty Cycle', "type": 'u8'},
                {"name": 'event Control', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'event Status', "type": 'bytes:4'},
                {"name": 'event Status Time', "type": 'bytes:4'},
                {"name": 'criticality Level Applied', "type": 'bytes:4'},
                {"name": 'cooling Temperature Set Point Applied', "type": 'u16'},
                {"name": 'heating Temperature Set Point Applied', "type": 'u16'},
                {"name": 'average Load Adjustment Percentage Applied', "type": 'bytes:4'},
                {"name": 'duty Cycle Applied', "type": 'u8'},
                {"name": 'event Control', "type": 'bytes:4'},
                {"name": 'signature Type', "type": 'bytes:4'},
                {"name": 'signature', "type": 'bytes:4'},
            ],
        },
        1: {
            "S→C": [
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'device Class', "type": 'bytes:4'},
                {"name": 'utility Enrollment Group', "type": 'u8'},
                {"name": 'cancel Control', "type": 'bytes:4'},
                {"name": 'effective Time', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'start Time', "type": 'bytes:4'},
                {"name": 'number Of Events', "type": 'u8'},
                {"name": 'issuer Event Id', "type": 'u32', "note": '(se-1.2b-15-0131-02)'},
            ],
        },
        2: {
            "S→C": [
                {"name": 'cancel Control', "type": 'bytes:4'},
            ],
        },
    },
    # Simple Metering (0x0702) [ami.xml]
    0x0702: {
        0: {
            "S→C": [
                {"name": 'end Time', "type": 'bytes:4'},
                {"name": 'status', "type": 'bytes:4'},
                {"name": 'profile Interval Period', "type": 'bytes:4'},
                {"name": 'number Of Periods Delivered', "type": 'u8'},
                {"name": 'intervals', "type": 'u24'},
            ],
            "C→S": [
                {"name": 'interval Channel', "type": 'bytes:4'},
                {"name": 'end Time', "type": 'bytes:4'},
                {"name": 'number Of Periods', "type": 'u8'},
            ],
        },
        1: {
            "S→C": [
            ],
            "C→S": [
                {"name": 'endpoint Id', "type": 'u16'},
            ],
        },
        2: {
            "S→C": [
            ],
            "C→S": [
                {"name": 'endpoint Id', "type": 'u16'},
            ],
        },
        3: {
            "S→C": [
                {"name": 'applied Update Period', "type": 'u8'},
                {"name": 'fast Poll Mode Endtime', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'fast Poll Update Period', "type": 'u8'},
                {"name": 'duration', "type": 'u8'},
            ],
        },
        4: {
            "S→C": [
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'snapshot Response Payload', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'command Index', "type": 'u8'},
                {"name": 'command Count', "type": 'u8'},
                {"name": 'snapshot Schedule Payload', "type": 'bytes:4'},
            ],
        },
        5: {
            "S→C": [
                {"name": 'snapshot Id', "type": 'u32'},
                {"name": 'snapshot Confirmation', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'snapshot Cause', "type": 'bytes:4'},
            ],
        },
        6: {
            "S→C": [
                {"name": 'snapshot Id', "type": 'u32'},
                {"name": 'snapshot Time', "type": 'bytes:4'},
                {"name": 'total Snapshots Found', "type": 'u8'},
                {"name": 'command Index', "type": 'u8'},
                {"name": 'total Commands', "type": 'u8'},
                {"name": 'snapshot Cause', "type": 'bytes:4'},
                {"name": 'snapshot Payload Type', "type": 'bytes:4'},
                {"name": 'snapshot Payload', "type": 'u8'},
            ],
            "C→S": [
                {"name": 'earliest Start Time', "type": 'bytes:4'},
                {"name": 'latest End Time', "type": 'bytes:4'},
                {"name": 'snapshot Offset', "type": 'u8'},
                {"name": 'snapshot Cause', "type": 'bytes:4'},
            ],
        },
        7: {
            "S→C": [
                {"name": 'sample Id', "type": 'u16'},
                {"name": 'sample Start Time', "type": 'bytes:4'},
                {"name": 'sample Type', "type": 'bytes:4'},
                {"name": 'sample Request Interval', "type": 'u16'},
                {"name": 'number Of Samples', "type": 'u16'},
                {"name": 'samples', "type": 'u24'},
            ],
            "C→S": [
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'start Sampling Time', "type": 'bytes:4'},
                {"name": 'sample Type', "type": 'bytes:4'},
                {"name": 'sample Request Interval', "type": 'u16'},
                {"name": 'max Number Of Samples', "type": 'u16'},
            ],
        },
        8: {
            "S→C": [
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'reporting Interval', "type": 'u24'},
                {"name": 'mirror Notification Reporting', "type": 'u8'},
                {"name": 'notification Scheme', "type": 'u8'},
            ],
            "C→S": [
                {"name": 'sample Id', "type": 'u16'},
                {"name": 'earliest Sample Time', "type": 'bytes:4'},
                {"name": 'sample Type', "type": 'bytes:4'},
                {"name": 'number Of Samples', "type": 'u16'},
            ],
        },
        9: {
            "S→C": [
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'notification Scheme', "type": 'u8'},
                {"name": 'notification Flag Order', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'notification Scheme', "type": 'u8'},
                {"name": 'notification Flags', "type": 'bytes:4'},
            ],
        },
        10: {
            "S→C": [
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'notification Scheme', "type": 'u8'},
                {"name": 'notification Flag Attribute Id', "type": 'u16'},
                {"name": 'cluster Id', "type": 'u16'},
                {"name": 'manufacturer Code', "type": 'u16'},
                {"name": 'number Of Commands', "type": 'u8'},
                {"name": 'command Ids', "type": 'u8'},
            ],
            "C→S": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
            ],
        },
        11: {
            "S→C": [
                {"name": 'notification Scheme', "type": 'u8'},
                {"name": 'notification Flag Attribute Id', "type": 'u16'},
                {"name": 'notification Flags N', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'request Date Time', "type": 'bytes:4'},
                {"name": 'implementation Date Time', "type": 'bytes:4'},
                {"name": 'proposed Supply Status', "type": 'bytes:4'},
                {"name": 'supply Control Bits', "type": 'bytes:4'},
            ],
        },
        12: {
            "S→C": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'implementation Date Time', "type": 'bytes:4'},
                {"name": 'supply Status', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'proposed Supply Status', "type": 'bytes:4'},
            ],
        },
        13: {
            "S→C": [
                {"name": 'sample Id', "type": 'u16'},
            ],
            "C→S": [
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'supply Tamper State', "type": 'bytes:4'},
                {"name": 'supply Depletion State', "type": 'bytes:4'},
                {"name": 'supply Uncontrolled Flow State', "type": 'bytes:4'},
                {"name": 'load Limit Supply State', "type": 'bytes:4'},
            ],
        },
        14: {
            "C→S": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'uncontrolled Flow Threshold', "type": 'u16'},
                {"name": 'unit Of Measure', "type": 'bytes:4'},
                {"name": 'multiplier', "type": 'u16'},
                {"name": 'divisor', "type": 'u16'},
                {"name": 'stabilisation Period', "type": 'u8'},
                {"name": 'measurement Period', "type": 'u16'},
            ],
        },
    },
    # Messaging (0x0703) [ami.xml]
    0x0703: {
        0: {
            "S→C": [
                {"name": 'message Id', "type": 'u32'},
                {"name": 'message Control', "type": 'bytes:4'},
                {"name": 'start Time', "type": 'bytes:4'},
                {"name": 'duration In Minutes', "type": 'u16'},
                {"name": 'message', "type": 'zstr'},
                {"name": 'optional Extended Message Control', "type": 'bytes:4', "note": '(se-1.2a-07-5356-19)'},
            ],
            "C→S": [
            ],
        },
        1: {
            "S→C": [
                {"name": 'message Id', "type": 'u32'},
                {"name": 'message Control', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'message Id', "type": 'u32'},
                {"name": 'confirmation Time', "type": 'bytes:4'},
                {"name": 'message Confirmation Control', "type": 'bytes:4', "note": '(se-1.2a-07-5356-19)'},
                {"name": 'message Response', "type": 'zstr', "note": '(se-1.2a-07-5356-19)'},
            ],
        },
        2: {
            "S→C": [
                {"name": 'message Id', "type": 'u32'},
                {"name": 'message Control', "type": 'bytes:4'},
                {"name": 'start Time', "type": 'bytes:4'},
                {"name": 'duration In Minutes', "type": 'u16'},
                {"name": 'message', "type": 'zstr'},
                {"name": 'optional Extended Message Control', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'earliest Implementation Time', "type": 'bytes:4'},
            ],
        },
        3: {
            "S→C": [
                {"name": 'implementation Date Time', "type": 'bytes:4'},
            ],
        },
    },
    # Tunneling (0x0704) [ami.xml]
    0x0704: {
        0: {
            "C→S": [
                {"name": 'protocol Id', "type": 'u8'},
                {"name": 'manufacturer Code', "type": 'u16'},
                {"name": 'flow Control Support', "type": 'u8'},
                {"name": 'maximum Incoming Transfer Size', "type": 'u16', "note": '(se-1.1a-07-5356-17)'},
            ],
            "S→C": [
                {"name": 'tunnel Id', "type": 'u16'},
                {"name": 'tunnel Status', "type": 'bytes:4'},
                {"name": 'maximum Incoming Transfer Size', "type": 'u16', "note": '(se-1.1a-07-5356-17)'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'tunnel Id', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'tunnel Id', "type": 'u16'},
                {"name": 'data', "type": 'u8'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'tunnel Id', "type": 'u16'},
                {"name": 'data', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'tunnel Id', "type": 'u16'},
                {"name": 'transfer Data Status', "type": 'bytes:4'},
            ],
        },
        3: {
            "C→S": [
                {"name": 'tunnel Id', "type": 'u16'},
                {"name": 'transfer Data Status', "type": 'bytes:4'},
            ],
            "S→C": [
                {"name": 'tunnel Id', "type": 'u16'},
                {"name": 'number Of Bytes Left', "type": 'u16'},
            ],
        },
        4: {
            "C→S": [
                {"name": 'tunnel Id', "type": 'u16'},
                {"name": 'number Of Bytes Left', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'tunnel Id', "type": 'u16'},
                {"name": 'number Of Octets Left', "type": 'u16'},
            ],
        },
        5: {
            "C→S": [
                {"name": 'tunnel Id', "type": 'u16'},
                {"name": 'number Of Octets Left', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'protocol List Complete', "type": 'u8'},
                {"name": 'protocol Count', "type": 'u8'},
                {"name": 'protocol List', "type": 'bytes:4'},
            ],
        },
        6: {
            "C→S": [
                {"name": 'protocol Offset', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'tunnel Id', "type": 'u16'},
            ],
        },
    },
    # Prepayment (0x0705) [ami.xml]
    0x0705: {
        0: {
            "C→S": [
                {"name": 'command Issue Date Time', "type": 'bytes:4'},
                {"name": 'originating Device', "type": 'bytes:4'},
                {"name": 'site Id', "type": 'zstr'},
                {"name": 'meter Serial Number', "type": 'zstr'},
            ],
        },
        1: {
            "S→C": [
                {"name": 'snapshot Id', "type": 'u32'},
                {"name": 'snapshot Time', "type": 'bytes:4'},
                {"name": 'total Snapshots Found', "type": 'u8'},
                {"name": 'command Index', "type": 'u8'},
                {"name": 'total Number Of Commands', "type": 'u8'},
                {"name": 'snapshot Cause', "type": 'bytes:4'},
                {"name": 'snapshot Payload Type', "type": 'bytes:4'},
                {"name": 'snapshot Payload', "type": 'u8'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'debt Label', "type": 'zstr'},
                {"name": 'debt Amount', "type": 'u32'},
                {"name": 'debt Recovery Method', "type": 'bytes:4'},
                {"name": 'debt Amount Type', "type": 'bytes:4'},
                {"name": 'debt Recovery Start Time', "type": 'bytes:4'},
                {"name": 'debt Recovery Collection Time', "type": 'u16'},
                {"name": 'debt Recovery Frequency', "type": 'bytes:4'},
                {"name": 'debt Recovery Amount', "type": 'u32'},
                {"name": 'debt Recovery Balance Percentage', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'friendly Credit', "type": 'bytes:4'},
                {"name": 'friendly Credit Calendar Id', "type": 'u32'},
                {"name": 'emergency Credit Limit', "type": 'u32'},
                {"name": 'emergency Credit Threshold', "type": 'u32'},
            ],
        },
        3: {
            "C→S": [
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'start Time', "type": 'bytes:4'},
                {"name": 'emergency Credit Limit', "type": 'u32'},
                {"name": 'emergency Credit Threshold', "type": 'u32'},
            ],
            "S→C": [
                {"name": 'result Type', "type": 'bytes:4'},
                {"name": 'top Up Value', "type": 'u32'},
                {"name": 'source Of Top Up', "type": 'bytes:4'},
                {"name": 'credit Remaining', "type": 'u32'},
            ],
        },
        4: {
            "C→S": [
                {"name": 'originating Device', "type": 'bytes:4'},
                {"name": 'top Up Code', "type": 'zstr'},
            ],
        },
        5: {
            "C→S": [
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'start Time', "type": 'bytes:4'},
                {"name": 'credit Adjustment Type', "type": 'bytes:4'},
                {"name": 'credit Adjustment Value', "type": 'u32'},
            ],
            "S→C": [
                {"name": 'command Index', "type": 'u8'},
                {"name": 'total Number Of Commands', "type": 'u8'},
                {"name": 'top Up Payload', "type": 'bytes:4'},
            ],
        },
        6: {
            "C→S": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'implementation Date Time', "type": 'bytes:4'},
                {"name": 'proposed Payment Control Configuration', "type": 'bytes:4'},
                {"name": 'cut Off Value', "type": 'u32'},
            ],
            "S→C": [
                {"name": 'command Index', "type": 'u8'},
                {"name": 'total Number Of Commands', "type": 'u8'},
                {"name": 'debt Payload', "type": 'bytes:4'},
            ],
        },
        7: {
            "C→S": [
                {"name": 'earliest Start Time', "type": 'bytes:4'},
                {"name": 'latest End Time', "type": 'bytes:4'},
                {"name": 'snapshot Offset', "type": 'u8'},
                {"name": 'snapshot Cause', "type": 'bytes:4'},
            ],
        },
        8: {
            "C→S": [
                {"name": 'latest End Time', "type": 'bytes:4'},
                {"name": 'number Of Records', "type": 'u8'},
            ],
        },
        9: {
            "C→S": [
                {"name": 'low Credit Warning Level', "type": 'u32'},
            ],
        },
        10: {
            "C→S": [
                {"name": 'latest End Time', "type": 'bytes:4'},
                {"name": 'number Of Debts', "type": 'u8'},
                {"name": 'debt Type', "type": 'bytes:4'},
            ],
        },
        11: {
            "C→S": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'implementation Date Time', "type": 'bytes:4'},
                {"name": 'maximum Credit Level', "type": 'u32'},
                {"name": 'maximum Credit Per Top Up', "type": 'u32'},
            ],
        },
        12: {
            "C→S": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'implementation Date Time', "type": 'bytes:4'},
                {"name": 'overall Debt Cap', "type": 'u32'},
            ],
        },
    },
    # Energy Management (0x0706) [ami.xml]
    0x0706: {
        0: {
            "S→C": [
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'event Status', "type": 'bytes:4'},
                {"name": 'event Status Time', "type": 'bytes:4'},
                {"name": 'criticality Level Applied', "type": 'bytes:4'},
                {"name": 'cooling Temperature Set Point Applied', "type": 'u16'},
                {"name": 'heating Temperature Set Point Applied', "type": 'u16'},
                {"name": 'average Load Adjustment Percentage Applied', "type": 'bytes:4'},
                {"name": 'duty Cycle Applied', "type": 'u8'},
                {"name": 'event Control', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'device Class', "type": 'bytes:4'},
                {"name": 'utility Enrollment Group', "type": 'u8'},
                {"name": 'action Required', "type": 'u8'},
            ],
        },
    },
    # Calendar (0x0707) [ami.xml]
    0x0707: {
        0: {
            "S→C": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'issuer Calendar Id', "type": 'u32'},
                {"name": 'start Time', "type": 'bytes:4'},
                {"name": 'calendar Type', "type": 'bytes:4'},
                {"name": 'calendar Time Reference', "type": 'bytes:4'},
                {"name": 'calendar Name', "type": 'zstr'},
                {"name": 'number Of Seasons', "type": 'u8'},
                {"name": 'number Of Week Profiles', "type": 'u8'},
                {"name": 'number Of Day Profiles', "type": 'u8'},
            ],
            "C→S": [
                {"name": 'earliest Start Time', "type": 'bytes:4'},
                {"name": 'min Issuer Event Id', "type": 'u32'},
                {"name": 'number Of Calendars', "type": 'u8'},
                {"name": 'calendar Type', "type": 'bytes:4'},
                {"name": 'provider Id', "type": 'u32'},
            ],
        },
        1: {
            "S→C": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'issuer Calendar Id', "type": 'u32'},
                {"name": 'day Id', "type": 'u8'},
                {"name": 'total Number Of Schedule Entries', "type": 'u8'},
                {"name": 'command Index', "type": 'u8'},
                {"name": 'total Number Of Commands', "type": 'u8'},
                {"name": 'calendar Type', "type": 'bytes:4'},
                {"name": 'day Schedule Entries', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Calendar Id', "type": 'u32'},
                {"name": 'start Day Id', "type": 'u8'},
                {"name": 'number Of Days', "type": 'u8'},
            ],
        },
        2: {
            "S→C": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'issuer Calendar Id', "type": 'u32'},
                {"name": 'week Id', "type": 'u8'},
                {"name": 'day Id Ref Monday', "type": 'u8'},
                {"name": 'day Id Ref Tuesday', "type": 'u8'},
                {"name": 'day Id Ref Wednesday', "type": 'u8'},
                {"name": 'day Id Ref Thursday', "type": 'u8'},
                {"name": 'day Id Ref Friday', "type": 'u8'},
                {"name": 'day Id Ref Saturday', "type": 'u8'},
                {"name": 'day Id Ref Sunday', "type": 'u8'},
            ],
            "C→S": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Calendar Id', "type": 'u32'},
                {"name": 'start Week Id', "type": 'u8'},
                {"name": 'number Of Weeks', "type": 'u8'},
            ],
        },
        3: {
            "S→C": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'issuer Calendar Id', "type": 'u32'},
                {"name": 'command Index', "type": 'u8'},
                {"name": 'total Number Of Commands', "type": 'u8'},
                {"name": 'season Entries', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Calendar Id', "type": 'u32'},
            ],
        },
        4: {
            "S→C": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'issuer Calendar Id', "type": 'u32'},
                {"name": 'start Time', "type": 'bytes:4'},
                {"name": 'calendar Type', "type": 'bytes:4'},
                {"name": 'total Number Of Special Days', "type": 'u8'},
                {"name": 'command Index', "type": 'u8'},
                {"name": 'total Number Of Commands', "type": 'u8'},
                {"name": 'special Day Entries', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'start Time', "type": 'bytes:4'},
                {"name": 'number Of Events', "type": 'u8'},
                {"name": 'calendar Type', "type": 'bytes:4'},
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Calendar Id', "type": 'u32'},
            ],
        },
        5: {
            "S→C": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Calendar Id', "type": 'u32'},
                {"name": 'calendar Type', "type": 'bytes:4'},
            ],
            "C→S": [
            ],
        },
    },
    # Device Management (0x0708) [ami.xml]
    0x0708: {
        0: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'tariff Type', "type": 'bytes:4'},
                {"name": 'implementation Date Time', "type": 'bytes:4'},
                {"name": 'proposed Tenancy Change Control', "type": 'bytes:4'},
            ],
        },
        1: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'current Provider Id', "type": 'u32'},
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'tariff Type', "type": 'bytes:4'},
                {"name": 'proposed Provider Id', "type": 'u32'},
                {"name": 'provider Change Implementation Time', "type": 'bytes:4'},
                {"name": 'provider Change Control', "type": 'bytes:4'},
                {"name": 'proposed Provider Name', "type": 'zstr'},
                {"name": 'proposed Provider Contact Details', "type": 'zstr'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'password Type', "type": 'bytes:4'},
            ],
            "S→C": [
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'implementation Date Time', "type": 'bytes:4'},
                {"name": 'duration In Minutes', "type": 'u16'},
                {"name": 'password Type', "type": 'bytes:4'},
                {"name": 'password', "type": 'zstr'},
            ],
        },
        3: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'site Id Time', "type": 'bytes:4'},
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'site Id', "type": 'zstr'},
            ],
        },
        4: {
            "C→S": [
                {"name": 'command Index', "type": 'u8'},
                {"name": 'total Commands', "type": 'u8'},
                {"name": 'event Configuration Payload', "type": 'bytes:4'},
            ],
            "S→C": [
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'start Date Time', "type": 'bytes:4'},
                {"name": 'event Configuration', "type": 'bytes:4'},
                {"name": 'configuration Control', "type": 'bytes:4'},
                {"name": 'event Configuration Payload', "type": 'u8'},
            ],
        },
        5: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'event Id', "type": 'u16'},
            ],
        },
        6: {
            "S→C": [
                {"name": 'issuer Event Id', "type": 'u32'},
                {"name": 'implementation Time', "type": 'bytes:4'},
                {"name": 'provider Id', "type": 'u32'},
                {"name": 'customer Id Number', "type": 'zstr'},
            ],
        },
    },
    # Events (0x0709) [ami.xml]
    0x0709: {
        0: {
            "C→S": [
                {"name": 'event Control Log Id', "type": 'bytes:4'},
                {"name": 'event Id', "type": 'u16'},
                {"name": 'start Time', "type": 'bytes:4'},
                {"name": 'end Time', "type": 'bytes:4'},
                {"name": 'number Of Events', "type": 'u8'},
                {"name": 'event Offset', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'log Id', "type": 'bytes:4'},
                {"name": 'event Id', "type": 'u16'},
                {"name": 'event Time', "type": 'bytes:4'},
                {"name": 'event Control', "type": 'bytes:4'},
                {"name": 'event Data', "type": 'zstr'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'log Id', "type": 'bytes:4'},
            ],
            "S→C": [
                {"name": 'total Number Of Events', "type": 'u16'},
                {"name": 'command Index', "type": 'u8'},
                {"name": 'total Commands', "type": 'u8'},
                {"name": 'log Payload Control', "type": 'bytes:4'},
                {"name": 'log Payload', "type": 'bytes:4'},
            ],
        },
        2: {
            "S→C": [
                {"name": 'cleared Events Logs', "type": 'bytes:4'},
            ],
        },
    },
    # MDU Pairing (0x070A) [ami.xml]
    0x070A: {
        0: {
            "S→C": [
                {"name": 'pairing Information Version', "type": 'u32'},
                {"name": 'total Number Of Devices', "type": 'u8'},
                {"name": 'command Index', "type": 'u8'},
                {"name": 'total Number Of Commands', "type": 'u8'},
                {"name": 'eui64s', "type": 'bytes:4'},
            ],
            "C→S": [
                {"name": 'local Pairing Information Version', "type": 'u32'},
                {"name": 'eui64 Of Requesting Device', "type": 'bytes:4'},
            ],
        },
    },
    # Sub-GHz (0x070B) [ami.xml]
    0x070B: {
        0: {
            "S→C": [
                {"name": 'period', "type": 'u8'},
            ],
            "C→S": [
            ],
        },
    },
    # Key Establishment (0x0800) [ami.xml]
    0x0800: {
        0: {
            "C→S": [
                {"name": 'key Establishment Suite', "type": 'bytes:4'},
                {"name": 'ephemeral Data Generate Time', "type": 'u8'},
                {"name": 'confirm Key Generate Time', "type": 'u8'},
                {"name": 'identity', "type": 'bytes:4'},
            ],
            "S→C": [
                {"name": 'requested Key Establishment Suite', "type": 'bytes:4'},
                {"name": 'ephemeral Data Generate Time', "type": 'u8'},
                {"name": 'confirm Key Generate Time', "type": 'u8'},
                {"name": 'identity', "type": 'bytes:4'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'ephemeral Data', "type": 'bytes:4'},
            ],
            "S→C": [
                {"name": 'ephemeral Data', "type": 'bytes:4'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'secure Message Authentication Code', "type": 'bytes:4'},
            ],
            "S→C": [
                {"name": 'secure Message Authentication Code', "type": 'bytes:4'},
            ],
        },
        3: {
            "C→S": [
                {"name": 'status Code', "type": 'bytes:4'},
                {"name": 'wait Time', "type": 'u8'},
                {"name": 'key Establishment Suite', "type": 'bytes:4'},
            ],
            "S→C": [
                {"name": 'status Code', "type": 'bytes:4'},
                {"name": 'wait Time', "type": 'u8'},
                {"name": 'key Establishment Suite', "type": 'bytes:4'},
            ],
        },
    },
    # Information (0x0900) [ta.xml]
    0x0900: {
        0: {
            "C→S": [
                {"name": 'inquiry Id', "type": 'u8'},
                {"name": 'data Type Id', "type": 'bytes:4'},
                {"name": 'request Information Payload', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'number', "type": 'u8'},
                {"name": 'buffer', "type": 'u8'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'notification List', "type": 'bytes:4'},
            ],
            "S→C": [
                {"name": 'contents', "type": 'u8'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'preference Type', "type": 'u16'},
                {"name": 'preference Payload', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'status Feedback List', "type": 'u8', "enum": {0: 'SUCCESS', 1: 'FAILURE', 126: 'NOT_AUTHORIZED', 128: 'MALFORMED_COMMAND', 129: 'UNSUP_COMMAND', 130: 'UNSUP_GENERAL_COMMAND', 131: 'UNSUP_MANUF_CLUSTER_COMMAND', 132: 'UNSUP_MANUF_GENERAL_COMMAND', 133: 'INVALID_FIELD', 134: 'UNSUPPORTED_ATTRIBUTE', 135: 'INVALID_VALUE', 136: 'READ_ONLY', 137: 'INSUFFICIENT_SPACE', 138: 'DUPLICATE_EXISTS', 139: 'NOT_FOUND', 140: 'UNREPORTABLE_ATTRIBUTE', 141: 'INVALID_DATA_TYPE', 142: 'INVALID_SELECTOR', 143: 'WRITE_ONLY', 144: 'INCONSISTENT_STARTUP_STATE', 145: 'DEFINED_OUT_OF_BAND', 147: 'ACTION_DENIED', 148: 'TIMEOUT', 149: 'ABORT', 150: 'INVALID_IMAGE', 151: 'WAIT_FOR_DATA', 152: 'NO_IMAGE_AVAILABLE', 153: 'REQUIRE_MORE_IMAGE', 154: 'NOTIFICATION_PENDING', 192: 'HARDWARE_FAILURE', 193: 'SOFTWARE_FAILURE', 195: 'UNSUPPORTED_CLUSTER', 196: 'LIMIT_REACHED'}},
            ],
        },
        3: {
            "C→S": [
                {"name": 'status Feedback', "type": 'u8', "enum": {0: 'SUCCESS', 1: 'FAILURE', 126: 'NOT_AUTHORIZED', 128: 'MALFORMED_COMMAND', 129: 'UNSUP_COMMAND', 130: 'UNSUP_GENERAL_COMMAND', 131: 'UNSUP_MANUF_CLUSTER_COMMAND', 132: 'UNSUP_MANUF_GENERAL_COMMAND', 133: 'INVALID_FIELD', 134: 'UNSUPPORTED_ATTRIBUTE', 135: 'INVALID_VALUE', 136: 'READ_ONLY', 137: 'INSUFFICIENT_SPACE', 138: 'DUPLICATE_EXISTS', 139: 'NOT_FOUND', 140: 'UNREPORTABLE_ATTRIBUTE', 141: 'INVALID_DATA_TYPE', 142: 'INVALID_SELECTOR', 143: 'WRITE_ONLY', 144: 'INCONSISTENT_STARTUP_STATE', 145: 'DEFINED_OUT_OF_BAND', 147: 'ACTION_DENIED', 148: 'TIMEOUT', 149: 'ABORT', 150: 'INVALID_IMAGE', 151: 'WAIT_FOR_DATA', 152: 'NO_IMAGE_AVAILABLE', 153: 'REQUIRE_MORE_IMAGE', 154: 'NOTIFICATION_PENDING', 192: 'HARDWARE_FAILURE', 193: 'SOFTWARE_FAILURE', 195: 'UNSUPPORTED_CLUSTER', 196: 'LIMIT_REACHED'}},
                {"name": 'preference Type', "type": 'u16'},
                {"name": 'preference Payload', "type": 'u8'},
            ],
            "S→C": [
            ],
        },
        4: {
            "C→S": [
                {"name": 'access Control', "type": 'u8'},
                {"name": 'option', "type": 'bytes:4'},
                {"name": 'contents', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'status Feedback List', "type": 'u8', "enum": {0: 'SUCCESS', 1: 'FAILURE', 126: 'NOT_AUTHORIZED', 128: 'MALFORMED_COMMAND', 129: 'UNSUP_COMMAND', 130: 'UNSUP_GENERAL_COMMAND', 131: 'UNSUP_MANUF_CLUSTER_COMMAND', 132: 'UNSUP_MANUF_GENERAL_COMMAND', 133: 'INVALID_FIELD', 134: 'UNSUPPORTED_ATTRIBUTE', 135: 'INVALID_VALUE', 136: 'READ_ONLY', 137: 'INSUFFICIENT_SPACE', 138: 'DUPLICATE_EXISTS', 139: 'NOT_FOUND', 140: 'UNREPORTABLE_ATTRIBUTE', 141: 'INVALID_DATA_TYPE', 142: 'INVALID_SELECTOR', 143: 'WRITE_ONLY', 144: 'INCONSISTENT_STARTUP_STATE', 145: 'DEFINED_OUT_OF_BAND', 147: 'ACTION_DENIED', 148: 'TIMEOUT', 149: 'ABORT', 150: 'INVALID_IMAGE', 151: 'WAIT_FOR_DATA', 152: 'NO_IMAGE_AVAILABLE', 153: 'REQUIRE_MORE_IMAGE', 154: 'NOTIFICATION_PENDING', 192: 'HARDWARE_FAILURE', 193: 'SOFTWARE_FAILURE', 195: 'UNSUPPORTED_CLUSTER', 196: 'LIMIT_REACHED'}},
            ],
        },
        5: {
            "C→S": [
                {"name": 'deletion Options', "type": 'bytes:4'},
                {"name": 'content Ids', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'notification List', "type": 'bytes:4'},
            ],
        },
        6: {
            "C→S": [
                {"name": 'description', "type": 'zstr'},
            ],
            "S→C": [
                {"name": 'notification List', "type": 'bytes:4'},
            ],
        },
        7: {
            "C→S": [
                {"name": 'enable', "type": 'u8'},
            ],
        },
        8: {
            "C→S": [
                {"name": 'timer', "type": 'u32'},
            ],
        },
        9: {
            "C→S": [
                {"name": 'root Id', "type": 'u16'},
            ],
        },
    },
    # Data Sharing (0x0901) [ta.xml]
    0x0901: {
        0: {
            "C→S": [
                {"name": 'file Index', "type": 'u16'},
                {"name": 'file Start Position', "type": 'u32'},
                {"name": 'requested Octet Count', "type": 'u32'},
                {"name": 'file Start Position And Requested Octet Count', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'write Options', "type": 'bytes:4'},
                {"name": 'file Size', "type": 'bytes:4'},
                {"name": 'file Size', "type": 'u8'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'file Index', "type": 'u16'},
                {"name": 'file Start Record', "type": 'u16'},
                {"name": 'requested Record Count', "type": 'u16'},
                {"name": 'file Start Record And Requested Record Count', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'file Index', "type": 'u16'},
                {"name": 'file Start Position', "type": 'u32'},
                {"name": 'octet Count', "type": 'u32'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'status', "type": 'u8'},
                {"name": 'file Index', "type": 'u16'},
                {"name": 'file Index', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'file Index', "type": 'u16'},
                {"name": 'file Start Record', "type": 'u16'},
                {"name": 'record Count', "type": 'u16'},
            ],
        },
        3: {
            "S→C": [
                {"name": 'transmit Options', "type": 'bytes:4'},
                {"name": 'file Index', "type": 'u16'},
                {"name": 'file Start Position', "type": 'u32'},
                {"name": 'file Length', "type": 'u32'},
                {"name": 'file Data', "type": 'bytes:4'},
                {"name": 'buffer', "type": 'u8'},
            ],
        },
        4: {
            "S→C": [
                {"name": 'transmit Options', "type": 'bytes:4'},
                {"name": 'file Index', "type": 'u16'},
                {"name": 'file Start Record', "type": 'u16'},
                {"name": 'record Count', "type": 'u16'},
                {"name": 'record File Data', "type": 'bytes:4'},
                {"name": 'buffer', "type": 'u8'},
            ],
        },
    },
    # Gaming (0x0902) [ta.xml]
    0x0902: {
        0: {
            "C→S": [
                {"name": 'specific Game', "type": 'u8'},
                {"name": 'game Id', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'game Id', "type": 'u16'},
                {"name": 'game Master', "type": 'u8'},
                {"name": 'list Of Game', "type": 'zstr'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'game Id', "type": 'u16'},
                {"name": 'join As Master', "type": 'u8'},
                {"name": 'name Of Game', "type": 'zstr'},
            ],
            "S→C": [
                {"name": 'command Id', "type": 'u8'},
                {"name": 'status', "type": 'bytes:4'},
                {"name": 'message', "type": 'zstr'},
            ],
        },
        2: {
            "C→S": [
            ],
        },
        3: {
            "C→S": [
            ],
        },
        4: {
            "C→S": [
            ],
        },
        5: {
            "C→S": [
            ],
        },
        6: {
            "C→S": [
            ],
        },
        7: {
            "C→S": [
            ],
        },
        8: {
            "C→S": [
                {"name": 'actions', "type": 'bytes:4'},
            ],
        },
        9: {
            "C→S": [
            ],
        },
    },
    # Data Rate Control (0x0903) [ta.xml]
    0x0903: {
        0: {
            "C→S": [
                {"name": 'originator Address', "type": 'bytes:4'},
                {"name": 'destination Address', "type": 'bytes:4'},
                {"name": 'data Rate', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'originator Address', "type": 'bytes:4'},
                {"name": 'destination Address', "type": 'bytes:4'},
                {"name": 'data Rate', "type": 'u8'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'originator Address', "type": 'bytes:4'},
                {"name": 'destination Address', "type": 'bytes:4'},
                {"name": 'data Rate', "type": 'u8'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'originator Address', "type": 'bytes:4'},
                {"name": 'destination Address', "type": 'bytes:4'},
            ],
        },
    },
    # Voice over ZigBee (0x0904) [ta.xml]
    0x0904: {
        0: {
            "C→S": [
                {"name": 'flag', "type": 'bytes:4'},
                {"name": 'codec Type', "type": 'u8'},
                {"name": 'samp Freq', "type": 'u8'},
                {"name": 'codec Rate', "type": 'u8'},
                {"name": 'service Type', "type": 'u8'},
                {"name": 'codec Type S1', "type": 'u8'},
                {"name": 'codec Type S2', "type": 'u8'},
                {"name": 'codec Type S3', "type": 'u8'},
                {"name": 'comp Type', "type": 'u8'},
                {"name": 'comp Rate', "type": 'u8'},
                {"name": 'buffer', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'ack Nack', "type": 'u8'},
                {"name": 'codec Type', "type": 'u8'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'voice Data', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'sequence Number', "type": 'u8'},
                {"name": 'error Flag', "type": 'u8'},
            ],
        },
        2: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'control Type', "type": 'u8'},
            ],
        },
        3: {
            "C→S": [
                {"name": 'ack Nack', "type": 'u8'},
            ],
        },
    },
    # Chatting (0x0905) [ta.xml]
    0x0905: {
        0: {
            "C→S": [
                {"name": 'uid', "type": 'u16'},
                {"name": 'nickname', "type": 'zstr'},
                {"name": 'cid', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
                {"name": 'cid', "type": 'u16'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'cid', "type": 'u16'},
                {"name": 'uid', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'status', "type": 'u8'},
                {"name": 'cid', "type": 'u16'},
                {"name": 'chat Participant List', "type": 'bytes:4'},
            ],
        },
        2: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'cid', "type": 'u16'},
                {"name": 'uid', "type": 'u16'},
                {"name": 'nickname', "type": 'zstr'},
            ],
        },
        3: {
            "C→S": [
                {"name": 'cid', "type": 'u16'},
                {"name": 'uid', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'cid', "type": 'u16'},
                {"name": 'uid', "type": 'u16'},
                {"name": 'nickname', "type": 'zstr'},
            ],
        },
        4: {
            "C→S": [
                {"name": 'name', "type": 'zstr'},
                {"name": 'uid', "type": 'u16'},
                {"name": 'nickname', "type": 'zstr'},
            ],
            "S→C": [
                {"name": 'options', "type": 'bytes:4'},
                {"name": 'chat Room List', "type": 'bytes:4'},
            ],
        },
        5: {
            "C→S": [
                {"name": 'destination Uid', "type": 'u16'},
                {"name": 'source Uid', "type": 'u16'},
                {"name": 'cid', "type": 'u16'},
                {"name": 'nickname', "type": 'zstr'},
                {"name": 'message', "type": 'zstr'},
            ],
            "S→C": [
                {"name": 'cid', "type": 'u16'},
            ],
        },
        6: {
            "C→S": [
                {"name": 'cid', "type": 'u16'},
                {"name": 'uid', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'cid', "type": 'u16'},
                {"name": 'node Information List', "type": 'bytes:4'},
            ],
        },
        7: {
            "S→C": [
                {"name": 'cid', "type": 'u16'},
                {"name": 'uid', "type": 'u16'},
                {"name": 'address', "type": 'bytes:4'},
                {"name": 'endpoint', "type": 'u8'},
            ],
        },
        8: {
            "S→C": [
                {"name": 'status', "type": 'u8'},
                {"name": 'cid', "type": 'u16'},
                {"name": 'uid', "type": 'u16'},
                {"name": 'address', "type": 'bytes:4'},
                {"name": 'endpoint', "type": 'u8'},
                {"name": 'nickname', "type": 'zstr'},
                {"name": 'address Endpoint And Nickname', "type": 'u8'},
            ],
        },
    },
    # Payment (0x0A01) [ta.xml]
    0x0A01: {
        0: {
            "C→S": [
                {"name": 'user Id', "type": 'zstr'},
                {"name": 'user Type', "type": 'u16'},
                {"name": 'service Id', "type": 'u16'},
                {"name": 'good Id', "type": 'zstr'},
            ],
            "S→C": [
                {"name": 'serial Number', "type": 'zstr'},
                {"name": 'currency', "type": 'u32'},
                {"name": 'price Trailing Digit', "type": 'u8'},
                {"name": 'price', "type": 'u32'},
                {"name": 'timestamp', "type": 'zstr'},
                {"name": 'trans Id', "type": 'u16'},
                {"name": 'trans Status', "type": 'u8'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'user Id', "type": 'zstr'},
                {"name": 'user Type', "type": 'u16'},
                {"name": 'service Id', "type": 'u16'},
                {"name": 'good Id', "type": 'zstr'},
            ],
            "S→C": [
                {"name": 'serial Number', "type": 'zstr'},
                {"name": 'currency', "type": 'u32'},
                {"name": 'price Trailing Digit', "type": 'u8'},
                {"name": 'price', "type": 'u32'},
                {"name": 'timestamp', "type": 'zstr'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'serial Number', "type": 'zstr'},
                {"name": 'trans Id', "type": 'u16'},
                {"name": 'trans Status', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'serial Number', "type": 'zstr'},
                {"name": 'status', "type": 'u8'},
            ],
        },
    },
    # Billing (0x0A02) [ta.xml]
    0x0A02: {
        0: {
            "C→S": [
                {"name": 'user Id', "type": 'zstr'},
                {"name": 'service Id', "type": 'u16'},
                {"name": 'service Provider Id', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'user Id', "type": 'zstr'},
                {"name": 'service Id', "type": 'u16'},
                {"name": 'service Provider Id', "type": 'u16'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'user Id', "type": 'zstr'},
                {"name": 'service Id', "type": 'u16'},
                {"name": 'service Provider Id', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'user Id', "type": 'zstr'},
                {"name": 'service Id', "type": 'u16'},
                {"name": 'service Provider Id', "type": 'u16'},
                {"name": 'timestamp', "type": 'zstr'},
                {"name": 'duration', "type": 'u16'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'user Id', "type": 'zstr'},
                {"name": 'service Id', "type": 'u16'},
                {"name": 'service Provider Id', "type": 'u16'},
            ],
        },
        3: {
            "C→S": [
                {"name": 'user Id', "type": 'zstr'},
                {"name": 'service Id', "type": 'u16'},
                {"name": 'service Provider Id', "type": 'u16'},
            ],
        },
        4: {
            "C→S": [
                {"name": 'user Id', "type": 'zstr'},
                {"name": 'status', "type": 'u8'},
            ],
        },
        5: {
            "C→S": [
                {"name": 'user Id', "type": 'zstr'},
                {"name": 'service Id', "type": 'u16'},
                {"name": 'service Provider Id', "type": 'u16'},
            ],
        },
    },
    # Appliance Events and Alert (0x0B02) [ha.xml]
    0x0B02: {
        0: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'alerts Count', "type": 'bytes:4'},
                {"name": 'alert Structures', "type": 'bytes:4'},
            ],
        },
        1: {
            "S→C": [
                {"name": 'alerts Count', "type": 'bytes:4'},
                {"name": 'alert Structures', "type": 'bytes:4'},
            ],
        },
        2: {
            "S→C": [
                {"name": 'event Header', "type": 'u8'},
                {"name": 'event Id', "type": 'u8', "enum": {1: 'End Of Cycle', 4: 'Temperature Reached', 5: 'End Of Cooking', 6: 'Switching Off', 7: 'Wrong Data'}},
            ],
        },
    },
    # Appliance Statistics (0x0B03) [ha.xml]
    0x0B03: {
        0: {
            "S→C": [
                {"name": 'time Stamp', "type": 'bytes:4'},
                {"name": 'log Id', "type": 'u32'},
                {"name": 'log Length', "type": 'u32'},
                {"name": 'log Payload', "type": 'u8'},
            ],
            "C→S": [
                {"name": 'log Id', "type": 'u32'},
            ],
        },
        1: {
            "S→C": [
                {"name": 'time Stamp', "type": 'bytes:4'},
                {"name": 'log Id', "type": 'u32'},
                {"name": 'log Length', "type": 'u32'},
                {"name": 'log Payload', "type": 'u8'},
            ],
            "C→S": [
            ],
        },
        2: {
            "S→C": [
                {"name": 'log Queue Size', "type": 'u8'},
                {"name": 'log Ids', "type": 'u32'},
            ],
        },
        3: {
            "S→C": [
                {"name": 'log Queue Size', "type": 'u8'},
                {"name": 'log Ids', "type": 'u32'},
            ],
        },
    },
    # Electrical Measurement (0x0B04) [ha.xml]
    0x0B04: {
        0: {
            "S→C": [
                {"name": 'profile Count', "type": 'u8'},
                {"name": 'profile Interval Period', "type": 'u8'},
                {"name": 'max Number Of Intervals', "type": 'u8'},
                {"name": 'list Of Attributes', "type": 'u16'},
            ],
            "C→S": [
            ],
        },
        1: {
            "S→C": [
                {"name": 'start Time', "type": 'u32'},
                {"name": 'status', "type": 'u8'},
                {"name": 'profile Interval Period', "type": 'u8'},
                {"name": 'number Of Intervals Delivered', "type": 'u8'},
                {"name": 'attribute Id', "type": 'u16'},
                {"name": 'intervals', "type": 'u8'},
            ],
            "C→S": [
                {"name": 'attribute Id', "type": 'u16'},
                {"name": 'start Time', "type": 'u32'},
                {"name": 'number Of Intervals', "type": 'u8'},
            ],
        },
    },
    # ZLL Commissioning (0x1000) [zll.xml]
    0x1000: {
        0: {
            "C→S": [
                {"name": 'transaction', "type": 'u32'},
                {"name": 'zigbee Information', "type": 'bytes:4'},
                {"name": 'zll Information', "type": 'bytes:4'},
            ],
        },
        1: {
            "S→C": [
                {"name": 'transaction', "type": 'u32'},
                {"name": 'rssi Correction', "type": 'u8'},
                {"name": 'zigbee Information', "type": 'bytes:4'},
                {"name": 'zll Information', "type": 'bytes:4'},
                {"name": 'key Bitmask', "type": 'bytes:4'},
                {"name": 'response Id', "type": 'u32'},
                {"name": 'extended Pan Id', "type": 'bytes:4'},
                {"name": 'network Update Id', "type": 'u8'},
                {"name": 'logical Channel', "type": 'u8'},
                {"name": 'pan Id', "type": 'u16'},
                {"name": 'network Address', "type": 'u16'},
                {"name": 'number Of Sub Devices', "type": 'u8'},
                {"name": 'total Group Ids', "type": 'u8'},
                {"name": 'endpoint Id', "type": 'u8'},
                {"name": 'profile Id', "type": 'u16'},
                {"name": 'device Id', "type": 'u16'},
                {"name": 'version', "type": 'u8'},
                {"name": 'group Id Count', "type": 'u8'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'transaction', "type": 'u32'},
                {"name": 'start Index', "type": 'u8'},
            ],
        },
        3: {
            "S→C": [
                {"name": 'transaction', "type": 'u32'},
                {"name": 'number Of Sub Devices', "type": 'u8'},
                {"name": 'start Index', "type": 'u8'},
                {"name": 'device Information Record Count', "type": 'u8'},
                {"name": 'device Information Record List', "type": 'bytes:4'},
            ],
        },
        6: {
            "C→S": [
                {"name": 'transaction', "type": 'u32'},
                {"name": 'identify Duration', "type": 'u16'},
            ],
        },
        7: {
            "C→S": [
                {"name": 'transaction', "type": 'u32'},
            ],
        },
        16: {
            "C→S": [
                {"name": 'transaction', "type": 'u32'},
                {"name": 'extended Pan Id', "type": 'bytes:4'},
                {"name": 'key Index', "type": 'bytes:4'},
                {"name": 'encrypted Network Key', "type": 'bytes:4'},
                {"name": 'logical Channel', "type": 'u8'},
                {"name": 'pan Id', "type": 'u16'},
                {"name": 'network Address', "type": 'u16'},
                {"name": 'group Identifiers Begin', "type": 'u16'},
                {"name": 'group Identifiers End', "type": 'u16'},
                {"name": 'free Network Address Range Begin', "type": 'u16'},
                {"name": 'free Network Address Range End', "type": 'u16'},
                {"name": 'free Group Identifier Range Begin', "type": 'u16'},
                {"name": 'free Group Identifier Range End', "type": 'u16'},
                {"name": 'initiator Ieee Address', "type": 'bytes:4'},
                {"name": 'initiator Network Address', "type": 'u16'},
            ],
        },
        17: {
            "S→C": [
                {"name": 'transaction', "type": 'u32'},
                {"name": 'status', "type": 'bytes:4'},
                {"name": 'extended Pan Id', "type": 'bytes:4'},
                {"name": 'network Update Id', "type": 'u8'},
                {"name": 'logical Channel', "type": 'u8'},
                {"name": 'pan Id', "type": 'u16'},
            ],
        },
        18: {
            "C→S": [
                {"name": 'transaction', "type": 'u32'},
                {"name": 'extended Pan Id', "type": 'bytes:4'},
                {"name": 'key Index', "type": 'bytes:4'},
                {"name": 'encrypted Network Key', "type": 'bytes:4'},
                {"name": 'network Update Id', "type": 'u8'},
                {"name": 'logical Channel', "type": 'u8'},
                {"name": 'pan Id', "type": 'u16'},
                {"name": 'network Address', "type": 'u16'},
                {"name": 'group Identifiers Begin', "type": 'u16'},
                {"name": 'group Identifiers End', "type": 'u16'},
                {"name": 'free Network Address Range Begin', "type": 'u16'},
                {"name": 'free Network Address Range End', "type": 'u16'},
                {"name": 'free Group Identifier Range Begin', "type": 'u16'},
                {"name": 'free Group Identifier Range End', "type": 'u16'},
            ],
        },
        19: {
            "S→C": [
                {"name": 'transaction', "type": 'u32'},
                {"name": 'status', "type": 'bytes:4'},
            ],
        },
        20: {
            "C→S": [
                {"name": 'transaction', "type": 'u32'},
                {"name": 'extended Pan Id', "type": 'bytes:4'},
                {"name": 'key Index', "type": 'bytes:4'},
                {"name": 'encrypted Network Key', "type": 'bytes:4'},
                {"name": 'network Update Id', "type": 'u8'},
                {"name": 'logical Channel', "type": 'u8'},
                {"name": 'pan Id', "type": 'u16'},
                {"name": 'network Address', "type": 'u16'},
                {"name": 'group Identifiers Begin', "type": 'u16'},
                {"name": 'group Identifiers End', "type": 'u16'},
                {"name": 'free Network Address Range Begin', "type": 'u16'},
                {"name": 'free Network Address Range End', "type": 'u16'},
                {"name": 'free Group Identifier Range Begin', "type": 'u16'},
                {"name": 'free Group Identifier Range End', "type": 'u16'},
            ],
        },
        21: {
            "S→C": [
                {"name": 'transaction', "type": 'u32'},
                {"name": 'status', "type": 'bytes:4'},
            ],
        },
        22: {
            "C→S": [
                {"name": 'transaction', "type": 'u32'},
                {"name": 'extended Pan Id', "type": 'bytes:4'},
                {"name": 'network Update Id', "type": 'u8'},
                {"name": 'logical Channel', "type": 'u8'},
                {"name": 'pan Id', "type": 'u16'},
                {"name": 'network Address', "type": 'u16'},
            ],
        },
        64: {
            "S→C": [
                {"name": 'ieee Address', "type": 'bytes:4'},
                {"name": 'network Address', "type": 'u16'},
                {"name": 'endpoint Id', "type": 'u8'},
                {"name": 'profile Id', "type": 'u16'},
                {"name": 'device Id', "type": 'u16'},
                {"name": 'version', "type": 'u8'},
            ],
        },
        65: {
            "C→S": [
                {"name": 'start Index', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'total', "type": 'u8'},
                {"name": 'start Index', "type": 'u8'},
                {"name": 'count', "type": 'u8'},
                {"name": 'group Information Record List', "type": 'bytes:4'},
            ],
        },
        66: {
            "C→S": [
                {"name": 'start Index', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'total', "type": 'u8'},
                {"name": 'start Index', "type": 'u8'},
                {"name": 'count', "type": 'u8'},
                {"name": 'endpoint Information Record List', "type": 'bytes:4'},
            ],
        },
    },
    # Relay Control (0xC00D) [relay-control.xml]
    0xC00D: {
        0: {
            "C→S": [
                {"name": 'is Enabled', "type": 'u8'},
                {"name": 'magic Number', "type": 'u32'},
            ],
            "S→C": [
                {"name": 'is Enabled', "type": 'u8'},
            ],
        },
        1: {
            "C→S": [
            ],
        },
    },
    # Sample Mfg Specific Cluster 2 (0xFC00) [sample-extensions.xml]
    0xFC00: {
        0: {
            "C→S": [
                {"name": 'arg One', "type": 'u8'},
            ],
        },
    },
    # Configuration Cluster (0xFC01) [silabs.xml]
    0xFC01: {
        0: {
            "C→S": [
                {"name": 'token', "type": 'u16'},
                {"name": 'data', "type": 'zstr'},
            ],
            "S→C": [
                {"name": 'token', "type": 'u16'},
                {"name": 'data', "type": 'zstr'},
            ],
        },
        1: {
            "C→S": [
            ],
        },
        2: {
            "C→S": [
                {"name": 'token', "type": 'u16'},
            ],
        },
        3: {
            "C→S": [
                {"name": 'data', "type": 'zstr'},
            ],
        },
    },
    # MFGLIB Cluster (0xFC02) [silabs.xml]
    0xFC02: {
        0: {
            "C→S": [
                {"name": 'channel', "type": 'u8'},
                {"name": 'power', "type": 'bytes:4'},
                {"name": 'time', "type": 'u16'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'channel', "type": 'u8'},
                {"name": 'power', "type": 'bytes:4'},
                {"name": 'time', "type": 'u16'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'channel', "type": 'u8'},
                {"name": 'power', "type": 'bytes:4'},
                {"name": 'time', "type": 'u16'},
            ],
        },
    },
    # SL Works With All Hubs (0xFC57) [wwah-silabs.xml]
    0xFC57: {
        0: {
            "C→S": [
                {"name": 'number Exempt Clusters', "type": 'u8'},
                {"name": 'cluster Id', "type": 'bytes:4'},
            ],
            "S→C": [
                {"name": 'cluster Id', "type": 'bytes:4'},
                {"name": 'aps Link Key Auth Status', "type": 'u8'},
            ],
        },
        1: {
            "C→S": [
                {"name": 'number Exempt Clusters', "type": 'u8'},
                {"name": 'cluster Id', "type": 'bytes:4'},
            ],
            "S→C": [
                {"name": 'power Notification Reason', "type": 'bytes:4'},
                {"name": 'manufacturer Id', "type": 'u16'},
                {"name": 'manufacturer Reason Length', "type": 'u8'},
                {"name": 'manufacturer Reason', "type": 'u8'},
            ],
        },
        2: {
            "C→S": [
                {"name": 'cluster Id', "type": 'bytes:4'},
            ],
            "S→C": [
                {"name": 'power Notification Reason', "type": 'bytes:4'},
                {"name": 'manufacturer Id', "type": 'u16'},
                {"name": 'manufacturer Reason Length', "type": 'u8'},
                {"name": 'manufacturer Reason', "type": 'u8'},
            ],
        },
        3: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'device Eui64', "type": 'bytes:4'},
                {"name": 'device Short', "type": 'u16'},
            ],
        },
        4: {
            "C→S": [
                {"name": 'first Backoff Time Seconds', "type": 'u8'},
                {"name": 'backoff Seq Common Ratio', "type": 'u8'},
                {"name": 'max Backoff Time Seconds', "type": 'u32'},
                {"name": 'max Redelivery Attempts', "type": 'u8'},
            ],
            "S→C": [
                {"name": 'number Exempt Clusters', "type": 'u8'},
                {"name": 'cluster Id', "type": 'bytes:4'},
            ],
        },
        5: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'current Power Mode', "type": 'u32'},
                {"name": 'available Power Sources', "type": 'u32'},
                {"name": 'current Power Source', "type": 'u32'},
                {"name": 'current Power Source Level', "type": 'u32'},
            ],
        },
        6: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'debug Report Id', "type": 'u8'},
                {"name": 'debug Report Size', "type": 'u32'},
            ],
        },
        7: {
            "C→S": [
                {"name": 'fast Rejoin Timeout Seconds', "type": 'u16'},
                {"name": 'duration Between Rejoins Seconds', "type": 'u16'},
                {"name": 'fast Rejoin First Backoff Seconds', "type": 'u16'},
                {"name": 'max Backoff Time Seconds', "type": 'u16'},
                {"name": 'max Backoff Iterations', "type": 'u16'},
            ],
            "S→C": [
                {"name": 'debug Report Id', "type": 'u8'},
                {"name": 'debug Report Data', "type": 'u8'},
            ],
        },
        8: {
            "C→S": [
            ],
            "S→C": [
                {"name": 'number Of Clusters', "type": 'u8'},
                {"name": 'cluster Id', "type": 'bytes:4'},
            ],
        },
        9: {
            "C→S": [
                {"name": 'enrollment Mode', "type": 'bytes:4'},
            ],
            "S→C": [
                {"name": 'number Of Beacons', "type": 'u8'},
                {"name": 'beacon', "type": 'bytes:4'},
            ],
        },
        10: {
            "C→S": [
            ],
        },
        11: {
            "C→S": [
                {"name": 'check In Interval', "type": 'u16'},
            ],
        },
        12: {
            "C→S": [
            ],
        },
        13: {
            "C→S": [
                {"name": 'wait Time', "type": 'u8'},
            ],
        },
        14: {
            "C→S": [
                {"name": 'channel', "type": 'u8'},
                {"name": 'pan Id', "type": 'u16'},
            ],
        },
        15: {
            "C→S": [
                {"name": 'number Exempt Clusters', "type": 'u8'},
                {"name": 'cluster Id', "type": 'bytes:4'},
            ],
        },
        16: {
            "C→S": [
            ],
        },
        17: {
            "C→S": [
            ],
        },
        18: {
            "C→S": [
                {"name": 'debug Report Id', "type": 'u8'},
            ],
        },
        19: {
            "C→S": [
                {"name": 'standard Beacons', "type": 'u8'},
            ],
        },
        20: {
            "C→S": [
            ],
        },
        21: {
            "C→S": [
            ],
        },
        22: {
            "C→S": [
            ],
        },
        23: {
            "C→S": [
            ],
        },
        24: {
            "C→S": [
            ],
        },
        25: {
            "C→S": [
            ],
        },
        26: {
            "C→S": [
            ],
        },
        27: {
            "C→S": [
            ],
        },
        28: {
            "C→S": [
            ],
        },
        29: {
            "C→S": [
            ],
        },
        30: {
            "C→S": [
                {"name": 'number Of Clusters', "type": 'u8'},
                {"name": 'cluster Id', "type": 'bytes:4'},
            ],
        },
        31: {
            "C→S": [
            ],
        },
        158: {
            "S→C": [
                {"name": 'status', "type": 'u8', "enum": {0: 'SUCCESS', 1: 'FAILURE', 126: 'NOT_AUTHORIZED', 128: 'MALFORMED_COMMAND', 129: 'UNSUP_COMMAND', 130: 'UNSUP_GENERAL_COMMAND', 131: 'UNSUP_MANUF_CLUSTER_COMMAND', 132: 'UNSUP_MANUF_GENERAL_COMMAND', 133: 'INVALID_FIELD', 134: 'UNSUPPORTED_ATTRIBUTE', 135: 'INVALID_VALUE', 136: 'READ_ONLY', 137: 'INSUFFICIENT_SPACE', 138: 'DUPLICATE_EXISTS', 139: 'NOT_FOUND', 140: 'UNREPORTABLE_ATTRIBUTE', 141: 'INVALID_DATA_TYPE', 142: 'INVALID_SELECTOR', 143: 'WRITE_ONLY', 144: 'INCONSISTENT_STARTUP_STATE', 145: 'DEFINED_OUT_OF_BAND', 147: 'ACTION_DENIED', 148: 'TIMEOUT', 149: 'ABORT', 150: 'INVALID_IMAGE', 151: 'WAIT_FOR_DATA', 152: 'NO_IMAGE_AVAILABLE', 153: 'REQUIRE_MORE_IMAGE', 154: 'NOTIFICATION_PENDING', 192: 'HARDWARE_FAILURE', 193: 'SOFTWARE_FAILURE', 195: 'UNSUPPORTED_CLUSTER', 196: 'LIMIT_REACHED'}},
                {"name": 'cluster Status Length', "type": 'u8'},
                {"name": 'cluster Status', "type": 'bytes:4'},
            ],
        },
    },
}

ENUMS_STD: dict[str, dict[int, str]] = {
    'AlertCountType': {0: 'Unstructured'},
    'AlertStructureCategory': {256: 'Warning', 512: 'Danger', 768: 'Failure'},
    'AlertStructurePresenceRecovery': {0: 'Recovery', 4096: 'Presence'},
    'AmiRegistrationState': {0: 'Unregistered', 1: 'Joining Network', 2: 'Joined Network', 3: 'Submitted Registration Request', 4: 'Registration Rejected', 5: 'Registered', 6: 'Registeration Not Possible'},
    'AnonymousDataState': {0: 'No Source Found', 1: 'Source Found'},
    'ApplianceStatus': {1: 'Off', 2: 'Stand By', 3: 'Programmed', 4: 'Programmed Waiting To Start', 5: 'Running', 6: 'Pause', 7: 'End Programmed', 8: 'Failure', 9: 'Programme Interrupted', 10: 'Idle', 11: 'Rinse Hold', 12: 'Service', 13: 'Superfreezing', 14: 'Supercooling', 15: 'Superheating'},
    'AttributeWritePermission': {0: 'Deny Write', 1: 'Allow Write Normal', 2: 'Allow Write Of Read Only', 134: 'Unsupported Attribute', 135: 'Invalid Value', 136: 'Read Only', 141: 'Invalid Data Type'},
    'BarrierControlBarrierPosition': {0: 'Closed', 100: 'Open', 255: 'Unknown'},
    'BarrierControlMovingState': {0: 'Stopped', 1: 'Closing', 2: 'Opening'},
    'BatterySize': {0: 'No Battery', 1: 'Built In', 2: 'Other', 3: 'AA', 4: 'AAA', 5: 'C', 6: 'D', 255: 'Unknown'},
    'CecedSpecificationVersion': {16: 'Compliant With V10 Not Certified', 26: 'Compliant With V10 Certified'},
    'ColorControlOptions': {1: 'Execute If Off'},
    'ColorMode': {0: 'Current Hue And Current Saturation', 1: 'Current X And Current Y', 2: 'Color Temperature'},
    'CommandIdentification': {1: 'Start', 2: 'Stop', 3: 'Pause', 4: 'Start Superfreezing', 5: 'Stop Superfreezing', 6: 'Start Supercooling', 7: 'Stop Supercooling', 8: 'Disable Gas', 9: 'Enable Gas', 10: 'Enable Energy Control', 11: 'Disable Energy Control'},
    'CommissioningStartupControl': {0: 'No Action', 1: 'Form Network', 2: 'Rejoin Network', 3: 'Start From Scratch'},
    'DataQualityId': {0: 'All Data Certified', 1: 'Only Instantaneous Power Not Certified', 2: 'Only Cumulated Consumption Not Certified', 3: 'Not Certified Data'},
    'DehumidifcationLockout': {0: 'not Allowed', 1: 'allowed'},
    'DeviceStatus2Structure': {32: 'Iris Symptom Code'},
    'DoorLockAlarmCode': {0: 'Deadbolt Jammed', 1: 'Reset To Factory Defaults', 3: 'RF Module Power Cycled', 4: 'Tamper Wrong Code Entry Limit', 5: 'Tamper Front Escutcheon', 6: 'Forced Door Open', 7: 'Door Ajar', 8: 'Coerced'},
    'DoorLockEventSource': {0: 'Keypad', 1: 'Rf', 2: 'Manual', 3: 'Rfid', 4: 'Biometric Cred', 255: 'Indeterminate'},
    'DoorLockEventType': {0: 'Operation', 1: 'Programming', 2: 'Alarm'},
    'DoorLockOperatingMode': {0: 'Normal Mode', 1: 'Vacation Mode', 2: 'Privacy Mode', 3: 'No Rf Lock Or Unlock', 4: 'Passage Mode'},
    'DoorLockOperationEventCode': {0: 'Unknown Or Mfg Specific', 1: 'Lock', 2: 'Unlock', 3: 'Lock Invalid Pin Or Id', 4: 'Lock Invalid Schedule', 5: 'Unlock Invalid Pin Or Id', 6: 'Unlock Invalid Schedule', 7: 'One Touch Lock', 8: 'Key Lock', 9: 'Key Unlock', 10: 'Auto Lock', 11: 'Schedule Lock', 12: 'Schedule Unlock', 13: 'Manual Lock', 14: 'Manual Unlock', 16: 'Unlock Coerced User', 17: 'Fingerpint Unlock', 18: 'Face ID Unlock', 19: 'Fingervein Unlock', 20: 'Auto Unlock', 21: 'Application Unlock', 22: 'Unlock Disposable User'},
    'DoorLockProgrammingEventCode': {0: 'Unknown Or Mfg Specific', 1: 'Master Code Changed', 2: 'Pin Added', 3: 'Pin Deleted', 4: 'Pin Changed', 5: 'Id Added', 6: 'Id Deleted', 7: 'Fingerprint Added', 8: 'Fingerprint Deleted', 9: 'Face Id Added', 10: 'Face Id Deleted', 11: 'Fingervein Added', 12: 'Fingervein Deleted'},
    'DoorLockSecurityLevel': {0: 'Network Security', 1: 'Aps Security'},
    'DoorLockSetPinOrIdStatus': {0: 'Success', 1: 'General Failure', 2: 'Memory Full', 3: 'Duplicate Code Error'},
    'DoorLockSoundVolume': {0: 'Silent', 1: 'Low', 2: 'High', 3: 'Medium'},
    'DoorLockState': {0: 'Not Fully Locked', 1: 'Locked', 2: 'Unlocked'},
    'DoorLockType': {0: 'Dead Bolt', 1: 'Magnetic', 2: 'Other', 3: 'Mortise', 4: 'Rim', 5: 'Latch Bolt', 6: 'Cylindrical', 7: 'Tubular', 8: 'Interconnected', 9: 'Dead Latch', 10: 'Door Furniture'},
    'DoorLockUserStatus': {0: 'Available', 1: 'Occupied Enabled', 3: 'Occupied Disabled', 255: 'Not Supported'},
    'DoorLockUserType': {0: 'Unrestricted', 1: 'Year Day Schedule User', 2: 'Week Day Schedule User', 3: 'Master User', 4: 'Non Access User', 5: 'Coerced User', 6: 'Disposable User', 255: 'Not Supported'},
    'DoorState': {0: 'Open', 1: 'Closed', 2: 'Error Jammed', 3: 'Error Forced Open', 4: 'Error Unspecified', 5: 'Error Ajar'},
    'EventIdentification': {1: 'End Of Cycle', 4: 'Temperature Reached', 5: 'End Of Cooking', 6: 'Switching Off', 7: 'Wrong Data'},
    'EzModeCommissioningClusterType': {0: 'Server', 1: 'Client'},
    'FanMode': {0: 'off', 1: 'low', 2: 'medium', 3: 'high', 4: 'on', 5: 'auto', 6: 'smart'},
    'FanModeSequence': {0: 'Low Med High', 1: 'low High', 2: 'Low Med High Auto', 3: 'low High Auto', 4: 'on Auto'},
    'GenericDeviceClass': {0: 'Lighting'},
    'GenericDeviceType': {0: 'Incandescent', 1: 'Spotlight Halogen', 2: 'Halogen Bulb', 3: 'CFL', 4: 'Linear Flourescent', 5: 'Led Bulb', 6: 'Spotlight Led', 7: 'Led Strip', 8: 'Led Tube', 9: 'Generic Indoor Fixture', 10: 'Generic Outdoor Fixture', 11: 'Pendant Fixture', 12: 'Floor Standing Fixture', 224: 'Generic Controller', 225: 'Wall Switch', 226: 'Portable Remote Controller', 227: 'Motion Or Light Sensor', 240: 'Generic Actuator', 241: 'Plugin Unit', 242: 'Retrofit Actuator', 255: 'Unspecified'},
    'HueDirection': {0: 'Shortest Distance', 1: 'Longest Distance', 2: 'Up', 3: 'Down'},
    'HueMoveMode': {0: 'stop', 1: 'Up', 3: 'Down'},
    'HueStepMode': {1: 'Up', 3: 'Down'},
    'IasAceAlarmStatus': {0: 'no Alarm', 1: 'burglar', 2: 'fire', 3: 'emergency', 4: 'police Panic', 5: 'fire Panic', 6: 'emergency Panic'},
    'IasAceArmMode': {0: 'disarm', 1: 'arm Day Home Zones Only', 2: 'arm Night Sleep Zones Only', 3: 'arm All Zones'},
    'IasAceArmNotification': {0: 'all Zones Disarmed', 1: 'only Day Home Zones Armed', 2: 'only Night Sleep Zones Armed', 3: 'all Zones Armed', 4: 'invalid Arm Disarm Code', 5: 'not Ready To Arm', 6: 'already Disarmed'},
    'IasAceAudibleNotification': {0: 'mute', 1: 'default Sound'},
    'IasAceBypassResult': {0: 'zone Bypassed', 1: 'zone Not Bypassed', 2: 'not Allowed', 3: 'invalid Zone Id', 4: 'unknown Zone Id', 5: 'invalid Arm Disarm Code'},
    'IasAcePanelStatus': {0: 'panel Disarmed', 1: 'armed Stay', 2: 'armed Night', 3: 'armed Away', 4: 'exit Delay', 5: 'entry Delay', 6: 'not Ready To Arm', 7: 'in Alarm', 8: 'arming Stay', 9: 'arming Night', 10: 'arming Away'},
    'IasEnrollResponseCode': {0: 'success', 1: 'not Supported', 2: 'no Enroll Permit', 3: 'too Many Zones'},
    'IasZoneState': {0: 'not Enrolled', 1: 'enrolled'},
    'IasZoneType': {0: 'standard Cie', 13: 'motion Sensor', 21: 'contact Switch', 40: 'fire Sensor', 42: 'water Sensor', 43: 'gas Sensor', 44: 'personal Emergency Device', 45: 'vibration Movement Sensor', 271: 'remote Control', 277: 'key Fob', 541: 'keypad', 549: 'standard Warning Device', 550: 'glass Break Sensor', 551: 'carbon Monoxide Sensor', 553: 'security Repeater', 65535: 'invalid Zone Type'},
    'KeypadLockout': {0: 'no Lockout', 1: 'level One Lockout', 2: 'level Two Lockout', 3: 'level Three Lockout', 4: 'level Four Lockout', 5: 'levelfive Lockout'},
    'LevelControlOptions': {1: 'Execute If Off', 2: 'Couple Color Temp To Level'},
    'LevelStatus': {0: 'On Target', 1: 'Below Target', 2: 'Above Target'},
    'LocationMethod': {0: 'Lateration', 1: 'Signposting', 2: 'Rf Fingerprinting', 3: 'Out Of Band'},
    'MeasurementLightSensorType': {0: 'photodiode', 1: 'CMOS'},
    'MeterTypeId': {0: 'Utility Primary Meter', 1: 'Utility Production Meter', 2: 'Utility Secondary Meter', 256: 'Private Primary Meter', 257: 'Private Production Meter', 258: 'Private Secondary Meters', 272: 'Generic Meter'},
    'MoveMode': {0: 'Up', 1: 'Down'},
    'OccupancySensorType': {0: 'PIR', 1: 'Ultrasonic', 2: 'pir And Ultrasonic', 3: 'physical Contact'},
    'OperatingMode': {0: 'normal', 1: 'configure'},
    'PhysicalEnvironment': {0: 'Unspecified', 1: 'First Profile Specified Value', 127: 'Last Profile Specified Value', 255: 'Unknown'},
    'PowerProfileState': {1: 'Power Profile Waiting To Start', 2: 'Power Profile Started', 3: 'Energy Phase Running', 4: 'Energy Phase Ended', 5: 'Energy Phase Waiting To Start', 6: 'Energy Phase Started', 7: 'Power Profile Ended', 8: 'Profile Ready For Scheduling', 9: 'Power Profile Scheduled'},
    'PowerSource': {0: 'Unknown', 1: 'Single Phase Mains', 2: 'Three Phase Mains', 3: 'Battery', 4: 'Dc Source', 5: 'Emergency Mains Constant Power', 6: 'Emergency Mains Transfer Switch', 128: 'Battery Backup'},
    'ProductCode': {0: 'Manufacturer Defined', 1: 'Iternational Article Number', 2: 'Global Trade Item Number', 3: 'Universal Product Code', 4: 'Stock Keeping Unit'},
    'ProductTypeId': {0: 'White Goods', 22017: 'Dishwasher', 22018: 'Tumble Dryer', 22019: 'Washer Dryer', 22020: 'Washing Machine', 24065: 'Oven', 24067: 'Hobs', 24070: 'Electrical Oven', 24073: 'Induction Hobs', 26113: 'Refrigerator Freezer'},
    'PumpControlMode': {0: 'constant Speed', 1: 'constant Pressure', 2: 'proportional Pressure', 3: 'constant Flow', 5: 'constant Temperature', 7: 'automatic'},
    'PumpOperationMode': {0: 'normal', 1: 'minimum', 2: 'maximum', 3: 'local'},
    'RelativeHumidityDisplay': {0: 'not Displayed', 1: 'displayed'},
    'RelativeHumidityMode': {0: 'measure Locally', 1: 'updated Over The Network'},
    'RemoteEnableFlags': {0: 'Disabled', 1: 'Enabled Remote And Energy Control', 7: 'Temporarily Locked Disabled', 15: 'Enabled Remote Control'},
    'ReportingDirection': {0: 'reported', 1: 'received'},
    'SaturationMoveMode': {0: 'stop', 1: 'Up', 3: 'Down'},
    'SaturationStepMode': {1: 'Up', 3: 'Down'},
    'SensingLightSensorType': {0: 'photodiode', 1: 'CMOS'},
    'SetpointAdjustMode': {0: 'heat Setpoint', 1: 'cool Setpoint', 2: 'heat And Cool Setpoints'},
    'SquawkLevel': {0: 'low Level', 1: 'medium Level', 2: 'very High Level'},
    'SquawkMode': {0: 'system Is Armed', 1: 'system Is Disarmed'},
    'SquawkStobe': {0: 'no Strobe', 1: 'use Strobe'},
    'StartOfWeek': {0: 'Sunday', 1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday', 5: 'Friday', 6: 'Saturday'},
    'StartUpOnOffValue': {0: 'Set To Off', 1: 'Set To On', 2: 'Set To Toggle', 255: 'Set To Previous'},
    'Status': {0: 'SUCCESS', 1: 'FAILURE', 126: 'NOT_AUTHORIZED', 128: 'MALFORMED_COMMAND', 129: 'UNSUP_COMMAND', 130: 'UNSUP_GENERAL_COMMAND', 131: 'UNSUP_MANUF_CLUSTER_COMMAND', 132: 'UNSUP_MANUF_GENERAL_COMMAND', 133: 'INVALID_FIELD', 134: 'UNSUPPORTED_ATTRIBUTE', 135: 'INVALID_VALUE', 136: 'READ_ONLY', 137: 'INSUFFICIENT_SPACE', 138: 'DUPLICATE_EXISTS', 139: 'NOT_FOUND', 140: 'UNREPORTABLE_ATTRIBUTE', 141: 'INVALID_DATA_TYPE', 142: 'INVALID_SELECTOR', 143: 'WRITE_ONLY', 144: 'INCONSISTENT_STARTUP_STATE', 145: 'DEFINED_OUT_OF_BAND', 147: 'ACTION_DENIED', 148: 'TIMEOUT', 149: 'ABORT', 150: 'INVALID_IMAGE', 151: 'WAIT_FOR_DATA', 152: 'NO_IMAGE_AVAILABLE', 153: 'REQUIRE_MORE_IMAGE', 154: 'NOTIFICATION_PENDING', 192: 'HARDWARE_FAILURE', 193: 'SOFTWARE_FAILURE', 195: 'UNSUPPORTED_CLUSTER', 196: 'LIMIT_REACHED'},
    'StepMode': {0: 'Up', 1: 'Down'},
    'SwitchActions': {0: 'On', 1: 'Off', 2: 'Toggle'},
    'SwitchType': {0: 'Toggle', 1: 'Momentary', 2: 'Multi Function'},
    'TemperatureDisplayMode': {0: 'celsius', 1: 'fahrenheit'},
    'TemperatureSetpointHold': {0: 'Setpoint Hold Off', 1: 'Setpoint Hold On'},
    'ThermostatControlSequence': {0: 'cooling Only', 1: 'cooling With Reheat', 2: 'heating Only', 3: 'heating With Reheat', 4: 'cooling And Heating', 5: 'cooling And Heating With Reheat'},
    'ThermostatRunningMode': {0: 'Off', 3: 'Cool', 4: 'Heat'},
    'ThermostatSystemMode': {0: 'off', 1: 'auto', 3: 'cool', 4: 'heat', 5: 'emergency Heating', 6: 'precooling', 7: 'fan Only', 8: 'dry', 9: 'sleep'},
    'TimeEncoding': {0: 'Relative', 64: 'Absolute'},
    'WarningEvent': {0: 'Warning1 Overall Power Above Available Power Level', 1: 'Warning2 Overall Power Above Power Threshold Level', 2: 'Warning3 Overall Power Back Below The Available Power Level', 3: 'Warning4 Overall Power Back Below The Power Threshold Level', 4: 'Warning5 Overall Power Will Be Potentially Above Available Power Level If The Appliance Starts'},
    'WarningMode': {0: 'stop', 1: 'burglar', 2: 'fire', 3: 'emergency', 4: 'police Panic', 5: 'fire Panic', 6: 'emergency Panic'},
    'WarningStobe': {0: 'no Strobe', 1: 'use Strobe'},
}
