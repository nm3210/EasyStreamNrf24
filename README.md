# Easy Stream for NRF24

This 'easy stream' package extends the normal NRF send/receive commands by adding some special characters and indices (and a CRC check) within the packets in order to combine multiple consecutive packets together, extending the previous 32 byte limit to any arbitrary length (within reason).

Package Functions:

* `sendPayload(..)` - 
  * `packPayload(..)` - 
* `receivePayload(..)` - 
  * `unpackPayloadBin(..)` - 
