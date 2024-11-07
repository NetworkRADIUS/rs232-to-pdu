## RS-232 to Tripplite PDU Tool

The RS-232 to Tripplite PDU tool allows admins to send byte strings through an RS-232 connector to control a Tripplite 
PDU. Supported operations are to turn a specific outlet port ON, OFF, and CYCLE.

---

## Supported Serial Commands

This tool expects commands conforming to the grammar below.

Turn outlet on: ```on <bank> <port>```\
Turn outlet off: ```of <bank> <port>```\
Cycle (restart) outlet: ```cy <bank> <port>```

In all cases, ```<bank>``` and ```<port>``` are expected to be ```uint8``` values.\
In all cases, this tool will send a ```SET``` command to the SNMP agent.

---

## Health Check

This tool will perform a health check on a regular frequency. Each health check will send a ```GET``` command to the 
SNMP agent. If a response is successfully received, the health check is considered to have passed. If the command 
timed-out or returned an error, the health check is considered to have failed. At this point, the tool will log this 
event, but continue on with other operations.

Health checks will have priority over other commands. Even though health checks will be placed into the same buffer as 
others, health checks will always have the highest possible priority.

Healthcheck frequency are configurable in the `config.yaml` file, under `healthcheck.frequency`.

---

## SNMP Command Buffering
To prevent the SNMP agent from being overwhelmed by commands, this tool will not send a command to the SNMP agent until 
a response for the previous command has been received. As such, all queued commands will be stored in a priority 
buffer. The priority given to commands will follow the order the commands were received by the tool. This is to prevent 
commands being sent out of order.

That is to say, this buffer acts as a FIFO queue with respect to the serial commands, but uses a priority queue to 
enable instantaneous healthchecks.

---

## SNMP Authentication

This tool supports v1, v2, and v3 SNMP authentication.

The authentication version for each bank should be listed in the `config.yaml` file. However, it is important to note 
that only a single version is allowed for each bank. That is, a bank cannot use more than one authentication scheme.

On config load, a check is performed to ensured that each bank uses exactly one authentication scheme.

When using SNMP v3, the user may also choose what security level they desire. The accepted values are ```noAuthNoPriv```
, ```authNoPriv```, and ```authPriv```.

```noAuthNoPriv```: SNMP request will be sent without any credentials aside from username (no authentication or confidentiality)\
```authNoPriv```: SNMP request will be sent with a username and authorization passphrase (authentication but no confidentiality)\
```authPriv```: SNMP request will be sent with username, authorization and privacy passphrase (authentication and confidentiality)

---

## Logging

This tools supports the option of configuring logging output to a file, syslog, or stream. Only one destination may be specified. The destination should be placed under `log.file`, `log.syslog`, or `log.stream`. For file and stream outputs, a single string is expected as the destination. For syslog, a `facility` field is required.

If no logging configuration is present, the tool will default to stdout as the destination.

Below are sample configurations.

```yaml
# config.yaml

# Sample 1 : logging to file
log:
  file: destination.log

# Sample 2 : logging to syslog based on facility
log:
  syslog:
    facility: user

# Sample 3: logging to stream
log:
  stream: stdout
```

---

## Config Format

This tool expects a configuration file called ```config.yaml```, placed under ```/etc/ser2snmp/```. This file must 
conform the yaml format and have the following sections.

```log```:\
\- ```file``` | ```stream```: logging destination as a string
\- ```syslog```:
&emsp;\- ```facility```: facility name for syslogs

```serial```:\
\- ```device```: string value of serial port tty file\
\- ```timeout```: time in seconds before timing out serial connection

```healthcheck```:\
\- ```frequency```: time in seconds in between healthchecks

```snmp```:\
\- ```retry```:\
&emsp;\- ```max_attempts```: integer value of maximum attempts allowed for an SNMP command\
&emsp;\- ```delay```: time in seconds to wait between SNMP command retries\
&emsp;\- ```timeout```: time in seconds before timing out SNMP commands

```banks```:\
\- ```<bank number>*```\
&emsp; \- ```snmp```:\
&emsp;&emsp; \- ```v1``` | ```v2```:\
&emsp;&emsp;&emsp; \- ```public_community```: string value of public community name\
&emsp;&emsp;&emsp; \- ```private_community```: string value of private community name\
&emsp;&emsp; \- ```v3```:\
&emsp;&emsp;&emsp; \- ```user```: string value of SNMP username\
&emsp;&emsp;&emsp; \- ```auth_protocol```: string value of authentication protocol\
&emsp;&emsp;&emsp; \- ```auth_passphrase```: string value of authentication passphrase\
&emsp;&emsp;&emsp; \- ```priv_protocol```: string value of privacy protocol\
&emsp;&emsp;&emsp; \- ```priv_passphrase```: string value of privacy passphrase\
&emsp;&emsp;&emsp; \- ```security_level```: ```noAuthNoPriv``` | ```authNoPriv``` | ```authPriv```\
&emsp;&emsp; \- ```ip_address```: string value of IP address of SNMP agent\
&emsp;&emsp; \- ```port```: integer value of network port of SNMP agent\
&emsp;&emsp; \- ```outlets```:\
&emsp;&emsp;&emsp; \- ```<port number>*```: string value of OID for this port

### Sample Config

```
log:
  file: {{ log_destination }}

serial:
  device: {{ device }}
  timeout: 0

healthcheck:
  frequency: 5

snmp:
  retry:
    max_attempts: 3
    delay: 5
    timeout: 5

devices:
  '001':
    snmp:
      v1:
        public_community: {{ public_community_name }}
        private_community: {{ private_community_name }}
      ip_address: {{ ip_address }}
      port: {{ port }}
      outlets:
        '001': {{ oid }}
        '002': {{ oid }}
  '002':
    snmp:
      v2:
        public_community: {{ public_community_name }}
        private_community: {{ private_community_name }}
      ip_address: {{ ip_address }}
      port: {{ port }}
      outlets:
        '001': {{ oid }}
        '002': {{ oid }}
  '003':
    snmp:
      v3:
        user: {{ snmp_user }}
        auth_protocol: {{ snmp_auth }}
        auth_passphrase: '{{ snmp_auth_passphrase }}'
        priv_protocol: {{ snmp_priv }}
        priv_passphrase: '{{ snmp_priv_passphrase }}'
        security_level: {{ snmp_security_level }}
      ip_address: {{ ip_address }}
      port: {{ port }}
      outlets:
        '001': {{ oid }}
        '002': {{ oid }}
```
