## RS-232 to Tripplite PDU Tool

The RS-232 to Tripplite PDU tool allows admins to send byte strings through an RS-232 connector to control a Tripplite PDU. Supported operations are to turn a specific outlet port ON, OFF, and CYCLE.

---

## Supported Serial Commands

This tool expects commands conforming to the grammar below.

Turn outlet on: ```on <bank> <port>```\
Turn outlet off: ```of <bank> <port>```\
Cycle (restart) outlet: ```cy <bank> <port>```

In all cases, ```<bank>``` and ```<port>``` are expected to be ```uint8``` values.\
In all cases, this tool will send a ```SET``` command to the SNMP agent.

Note that the SNMP agent may "flatten" multiple banks into seemingly a single bank, with the ports being serialized.

---

## Config Format

This tool expects a configuration file called ```config.ini```, placed under ```src/```. This file must conform the INI format and have the following sections.

#### ```SERIAL_CONFIGS```
```SERIAL_PORT```: string value of file location of serial port\
```TIMEOUT```: time in seconds before timing out serial connection

####  ```PDU_AUTH```
```USER```: string value of SNMP user name\
```AUTH```: string value of authentication protocol\
```AUTH_PASSPHRASE```: string value of authentication passphrase\
```PRIV```: string value of privacy protocol\
```PRIV_PASSPHRASE```: string value of privacy passphrase

#### ```PDU_LOCATION```
```IP_ADDRESS```: string value of IP address of SNMP agent\
```PORT```: integer value of network port of SNMP agent

#### ```SNMP_RETRY```
```MAX_ATTEMPTS```: integer value of number of maximum attempts for an SNMP command\
```RETRY_DELAY```: time in seconds to wait before attempting a retry after a SNMP command failure
```TIMEOUT```: time in seconds before timing out SNMP command

In addition to the above sections, each power bank must have its own section, titled as ```BANK<# padded to 3 digits>```. Within each of these sections, each port must have its own attribute, titled as ```PORT<# padded to 3 digits>```. The value of each of these attributes must be the matching ```OID``` for the port. A sample section is provided below.

#### ```[BANK001]```
```PORT001 = 1.3.6.1.4.1.850.1.1.3.2.3.3.1.1.6.1.1```\
```PORT002 = 1.3.6.1.4.1.850.1.1.3.2.3.3.1.1.6.1.2```\
```PORT003 = 1.3.6.1.4.1.850.1.1.3.2.3.3.1.1.6.1.3```\
```PORT004 = 1.3.6.1.4.1.850.1.1.3.2.3.3.1.1.6.1.4```

---

## SNMP Command Buffering
To prevent the SNMP agent from being overwhelmed by commands, this tool will not send a command to the SNMP agent until a response for the previous command has been received. As such, all queued commands will be stored in a priority buffer. The priority given to commands will follow the order the commands were received by the tool. This is to prevent commands being sent out of order.

---

## Health Check

This tool will perform a health check on a regular interval. Each health check will send a ```GET``` command to the SNMP agent. If a response is successfully received, the health check is considered to have passed. If the command timed-out or returned an error, the health check is considered to have failed. At this point, the tool will log this event, but continue on with other operations.

Health checks will have priority over other commands. Even though health checks will be placed into the same buffer as others, health checks will always have the highest possible priority.
