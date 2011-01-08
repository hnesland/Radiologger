#!/usr/bin/python
#
# Script to scan for activity on frequency ranges and log unique
# frequencies with a few seconds of audio.
#
import serial
import time
import re
import threading
import alsaaudio
import sys

run = 1
doRec = 0
currentFrequency = ""
LCDSCREEN = ""

scannedFrequencies = []

def writeout(str):
   print time.strftime("%Y-%m-%d %H:%M:%S"), str

rlog = open("rec_freqscan.log", 'a')
freqlog = open("frequencies.log", 'a')

class RecordThread (threading.Thread):
   
   def run(self):
      global currentFrequency
      global run
      global doRec
      global rlog

      if doRec == 1:
         rlog.write( '%(time)s %(freq)s START RECORD\n' % {'time': time.strftime("%Y-%m-%d %H:%M:%S"), 'freq': currentFrequency})
         filename = 'audio/freqscan_%(time)s_%(freq)s.raw' % {'time': time.strftime("%Y%m%d%H%M%S"), 'freq': currentFrequency.replace(" ", "_")}

         f = open(filename, 'wb')

         card = 'plughw:CARD=Intel,DEV=0'
         inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NONBLOCK, card)
         inp.setchannels(1)
         inp.setrate(8000*2)
         inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
         inp.setperiodsize(160)

         out = alsaaudio.PCM(alsaaudio.PCM_PLAYBACK, card=card)
         out.setchannels(1)
         out.setrate(8000*2)
         out.setformat(alsaaudio.PCM_FORMAT_S16_LE)
         out.setperiodsize(160)
         
         while doRec:
            l, data = inp.read()
            
            if l:
               f.write(data)
               out.write(data)
               time.sleep(.001)

         # Thread finished
         rlog.write( '%(time)s %(freq)s STOP RECORD\n' % {'time': time.strftime("%Y-%m-%d %H:%M:%S"), 'freq': currentFrequency})
         f.close()

class InputThread (threading.Thread):
   def run(self):
      global ser
      global run
      global doRec
      global scannedFrequencies
      global LCDSCREEN
      while run:
         val = raw_input('')

         if val == 'q':
            run = 0
            doRec = 0
            writeout("Quitting")
            return

         if val == 's':
            ser.write("KEY00\r")
            ser.readline(eol="\r")
            writeout("Skipped frequency")

         if val == 'd':
            writeout("Dumping frequency table")
            print "--"
            print scannedFrequencies
            print "--"

         if val == 'l':
            writeout("Dumping LCD screen")
            print LCDSCREEN

InputThread().start()

ser = serial.Serial()
ser.port = '/dev/ttyUSB0'
ser.baudrate = 19200
ser.open()

"""
LCD1 [SRCH + 5k       ][####            ]
LCD2 [ 454.6750  FM   ][                ]
LCD3 [Range 4         ][                ]
LCD4 [                ][                ]
LCD1 [     + 5k       ][                ]
LCD2 [ 472.0400  FM   ][                ]
LCD3 [Range -234------][         #      ]
LCD4 [                ][                ]
"""

recordStarted = 0
openChannel = 0

try:

   while run:
      ser.write("LCD\r")
      LCD1 = ser.readline(eol="\r")
      LCD2 = ser.readline(eol="\r")
      LCD3 = ser.readline(eol="\r")
      LCD4 = ser.readline(eol="\r")
      LCDSCREEN = LCD1 + "\n" + LCD2 + "\n" + LCD3 + "\n" + LCD4
      
      currentFrequencyRe = re.search('LCD2\s\[\s+(\S+).*\]', LCD2)
      if currentFrequencyRe != None:
         currentFrequency = currentFrequencyRe.group(1).strip()
         """if lastFrequency != currentFrequency:
            print "Frequency: %s" % currentFrequency
         """
      scannerStatusRe = re.search('LCD1\s\[(\S+)\s.*\]', LCD1)
      if scannerStatusRe != None:
         scannerStatus = scannerStatusRe.group(1).strip()
         if scannerStatus == 'SRCH':
            openChannel = 1
            if doRec == 0:
               writeout("Activity on frequency: %s" % currentFrequency)
               if currentFrequency not in scannedFrequencies:
                  writeout("New frequency: %s" % currentFrequency)
                  writeout("Start record for max 15 seconds")
                  freqlog.write( '%(time)s %(freq)s MHz\n' % {'time': time.strftime("%Y-%m-%d %H:%M:%S"), 'freq': currentFrequency})
                  freqlog.flush()
                  doRec = 1
                  recordStarted = time.time()
                  RecordThread().start()
                  scannedFrequencies.append(currentFrequency)
               else:
                  writeout("Resuming scan.")
                  ser.write("KEY00\r")
                  ser.readline(eol="\r")
                  openChannel = 0

            elif recordStarted + 15 < time.time():
               doRec = 0
               writeout("Stop record. Resuming scan.")
               ser.write("KEY00\r")
               ser.readline(eol="\r")
               openChannel = 0
      else:
         openChannel = 0
            
      
      if doRec == 1 and openChannel == 0:
         writeout("Transmission ended. Stop record. Resume scan.")
         doRec = 0

      lastFrequency = currentFrequency
      time.sleep(0.2)
   ser.close()
except KeyboardInterrupt:
   writeout("Got ^C. Cleaning up..")
   ser.close()
   doRec = 0
   run = 0

