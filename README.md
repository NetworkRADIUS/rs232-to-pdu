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

---

## Config Format

This tool expects a configuration file called ```config.yaml```, placed under ```/etc/ser2snmp/```. This file must conform the yaml format and have the following sections.

```serial_configs```:\
\- ```serial_port```: string value of serial port tty file\
\- ```timeout```: time in seconds before timing out serial connection

```snmp_retry```:
\- ```max_attempts```: integer value of maximum attempts allowed for an SNMP command\
\- ```retry_delay```: time in seconds to wait between SNMP command retries\
\- ```timeout```: time in seconds before timing out SNMP commands

```banks```:
\- ```<bank number>*```
&emsp;\- ```pdu_auth```:
&emsp;&emsp; \- ```user```: string value of SNMP username\
&emsp;&emsp; \- ```auth```: string value of authentication protocol\
&emsp;&emsp; \- ```auth_passphrase```: string value of authentication passphrase\
&emsp;&emsp; \- ```priv```: string value of privacy protocol\
&emsp;&emsp; \- ```priv_passphrase```: string value of privacy passphrase\
&emsp; \- ```ip_address```: string value of IP address of SNMP agent\
&emsp; \- ```snmp_port```: integer value of network port of SNMP agent\
&emsp; \- ```ports```:\
&emsp;&emsp; \- ```<port number>*```: string value of OID for this port

---

## SNMP Command Buffering
To prevent the SNMP agent from being overwhelmed by commands, this tool will not send a command to the SNMP agent until a response for the previous command has been received. As such, all queued commands will be stored in a priority buffer. The priority given to commands will follow the order the commands were received by the tool. This is to prevent commands being sent out of order.

---

## Health Check

This tool will perform a health check on a regular interval. Each health check will send a ```GET``` command to the SNMP agent. If a response is successfully received, the health check is considered to have passed. If the command timed-out or returned an error, the health check is considered to have failed. At this point, the tool will log this event, but continue on with other operations.

Health checks will have priority over other commands. Even though health checks will be placed into the same buffer as others, health checks will always have the highest possible priority.
