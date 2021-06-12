### Easy Stream for nRF24
# This 'easy stream' package extends the normal NRF send/receive commands
# by adding some special characters and indices (and a CRC check) within the 
# packets in order to combine multiple consecutive packets together, extending
# the previous 32 byte limit to any arbitrary length (within reason).
#
# nm3210@gmail.com
# Date Created:  June 12th, 2021 (after testing for a few weeks)
# Last Modified: June 12th, 2021

import os, sys, collections, time # circuitpython built-ins
sys.path.append(os.path.join(os.path.dirname(__file__), ".")) # make sure this folder is in the path
from crc import crc

_specialFirstBinChars = b'c0ffee'
_numBinChars = 2 # 0x00 to 0xff

def packPayload(dataIn, maxLen=32):
    """
    This 'packPayload' will split the input data into individual 'packets'/bins
    that are then reassembled by the associated 'receivePayload' and
    'unpackPayloadBin' functions back into the original input.
    
    The packing mechanism first adds a special sequence of characters to the
    first bin (by default using the six chars in 'c0ffee') so that the receiver
    will know which bin will contain the total number of expected bins. Then it
    will add the aforementioned number of expected bins to be received to the
    string. And finally, a CRC value gets added to the end of the string for
    transmission assurance.
    
    The specific format is
        Bin#0: [SpecialChars] [NumBins] [BinIdx0] <content>
        Bin#1: [BinIdx1] <content>
        Bin#2: [BinIdx2] <content>
        Bin#N: [BinIdxN] <content> [CRC]
        
    Note that many short-length inputs will just be within a single bin
        Bin#0: [SpecialChars] [NumBins] [BinIdx0] <content> [CRC]
    
    Specific examples/usages
        packPayload('A') => [b'c0ffee0100A9479']
        packPayload('123456789') => [b'c0ffee0100123456789e5cc']
        packPayload('123456789'*7) => [b'c0ffee03001234567891234567891234', 
            b'01567891234567891234567891234567', b'028912345678912345678925ba']
    """
    # Add packet header information
    numSpecialChars = len(_specialFirstBinChars)
    binFormat = b'%%0%dx'%_numBinChars # convert to hex
    
    # Calculate CRC
    crcVal = b'%04x'%crc(dataIn) # convert to hex
    
    # Prefix input data with header info
    dataWithHeader = _specialFirstBinChars + '_'*_numBinChars + dataIn + crcVal
    binSize = maxLen - _numBinChars
    
    # Split string into individual packets/bins
    splitPackets = [dataWithHeader[i:i+binSize] for i in range(0, len(dataWithHeader), binSize)]

    # Fill in num bin info
    firstIndexBinLoc = (numSpecialChars+_numBinChars)
    splitPackets[0] = splitPackets[0][:numSpecialChars] + binFormat%len(splitPackets) + splitPackets[0][firstIndexBinLoc:]

    # Fill in bin index
    for index, curPacket in enumerate(splitPackets):
        if index == 0:
            splitPackets[index] = splitPackets[index][:firstIndexBinLoc] + binFormat%index + splitPackets[index][firstIndexBinLoc:]
        else:
            splitPackets[index] = binFormat%index + splitPackets[index]
    return splitPackets

def unpackPayloadBin(binData, debugPrint=False):
    # Look for first bin special chars and pull out the number of bins
    binData = binData.decode() if type(binData) is bytearray or type(binData) is bytes else binData
    numBins = None
    if binData.startswith(_specialFirstBinChars): # first bin check
        numBins = int(binData[len(_specialFirstBinChars):len(_specialFirstBinChars)+_numBinChars],16)
        
    # Pull out index for each bin
    binIdxLoc = len(_specialFirstBinChars)+_numBinChars if numBins is not None else 0
    binIdxVal = int(binData[binIdxLoc:binIdxLoc+_numBinChars],16)
    
    # Snip out contents
    startIdx = binIdxLoc + _numBinChars
    stopIdx = len(binData)
    payloadContent = binData[startIdx:stopIdx]
    
    # Assemble output: [payloadContent, binIdxVal, numBins]
    return payloadContent, binIdxVal, numBins

def receivePayload(nrfRef, timeoutDur=0.1, updateDur=0.1, debugPrint=False):
    """
    Automatically parse multiple consecutive payloads packed via `packPayload`
    and sent over a link with nrf.send(payload). There is a healthy bit of
    validation for CRC values and the expected number of bins within the first
    packet/bin to make sure 
    
    Specific examples/usages
        Received packets: [b'c0ffee0100A9479']
        Output = 'A'
        
        Received packets: [b'c0ffee0100123456789e5cc']
        Output = '123456789'
        
        Received packets: [b'c0ffee03001234567891234567891234', 
            b'01567891234567891234567891234567', b'028912345678912345678925ba']
        Output = '123456789123456789123456789123456789123456789123456789123456789'
    
    """
    # Start a new receive payload set
    receivedPayloadBins = {} # dict
    numExpectedBins = None
    
    # Setup timeout
    startTimer = time.monotonic_ns() # start timer
    
    # Continually look for transmitted data
    while len(receivedPayloadBins) is not numExpectedBins:
        # Check for timeout
        if time.monotonic_ns() > startTimer + timeoutDur*1e9:
            if debugPrint == True:
                print("Timeout reached")
            break
        
        # Listen for data
        nrfRef.listen = True # enable listen processing (high power usage for some reason)
        time.sleep(updateDur) # allow listening on the radio for a while
        nrfRef.listen = False # disable listen processing (back to standby power)
        if not nrfRef.available():
            continue
        
        # grab information about the received payload
        payload_size, pipe_number = (nrfRef.any(), nrfRef.pipe)
        
        # Pull out any received data
        buffer = nrfRef.read() # also clears nrfRef.irq_dr status flag
        
        if debugPrint == True:
            print("Received {} bytes on pipe {}: {}".format(
                payload_size, pipe_number, buffer))
                
        # Unpack payload
        payloadContent, binIdxVal, numBins = unpackPayloadBin(buffer, debugPrint)
        
        # Check for total number of bins
        if numBins is not None: # in the first payload
            numExpectedBins = numBins
            
            # Check if the receivedPayloadBins already has content
            if numExpectedBins < len(receivedPayloadBins):
                receivedPayloadBins = {} # reset
        
        # Add/update payload
        receivedPayloadBins[binIdxVal] = payloadContent
        
        # Reset timer now that a new packet has been detected
        startTimer = time.monotonic_ns() # start timer
    
    # Pull out all the contents
    receivedPayloadBins = collections.OrderedDict(sorted(receivedPayloadBins.items())) # sort
    totalPayload = ''.join(list(receivedPayloadBins.values()))
    
    # Extract the CRC
    payloadCrc = totalPayload[-4:]
    totalPayload = totalPayload[:-4]
    
    # Check whether contents match CRC
    calculatedCrc = '%04x'%crc(totalPayload)
    payloadCrc = payloadCrc.decode() if type(payloadCrc) is bytearray or type(payloadCrc) is bytes else payloadCrc
    calculatedCrc = calculatedCrc.decode() if type(calculatedCrc) is bytearray or type(calculatedCrc) is bytes else calculatedCrc
    if payloadCrc != calculatedCrc:
        if debugPrint == True:
            print('Payload''s CRC (%s) does not match calculated CRC (%s)' % (payloadCrc, calculatedCrc))
        return None
    
    # Return payload
    return totalPayload

def sendPayload(nrfRef, payload, debugPrint=False):
    # Configure the module to transmit
    nrfRef.power = True
    nrfRef.listen = False
    
    # Attempt to send the payload
    packedPayload = packPayload(payload)
    if debugPrint == True:
        print(f'Attempting to transmit payload \'{payload}\'')
        print(packedPayload)
    numRetries = 12;
    gotAckBack = nrfRef.send(packedPayload, force_retry=numRetries)
    
    # Check whether the send was 'successful' (got an ack back)
    if debugPrint == True:
        if gotAckBack == True:
            print(f'  Succesfully transmitted payload \'{payload}\' (received ack back)')
        else:
            print(f'  No ack was received back for payload \'{payload}\'')
    
    # Disable the module to conserve power
    nrfRef.power = False
    
    # Return value of whether an ack was received back
    return gotAckBack
