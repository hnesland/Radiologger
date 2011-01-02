#!/usr/bin/python
import serial
import time
import re
import threading
import alsaaudio

ignored_frequencies = ['168.1000', '166.4500', '166.0000', '138.0000','168.0750']
run = 1
doRec = 0
lastFreq = ""

def writeout(str):
   print time.strftime("%Y-%m-%d %H:%M:%S"), str

rlog = open("rec.log", 'a')
alog = open("act.log", 'a')

class RecordThread (threading.Thread):
   
   def run(self):
      global lastFreq
      global run
      global doRec
      global rlog

      if doRec == 1:
         rlog.write( '%(time)s %(freq)s START RECORD\n' % {'time': time.strftime("%Y-%m-%d %H:%M:%S"), 'freq': lastFreq})
         filename = 'audio/%(time)s_%(freq)s.raw' % {'time': time.strftime("%Y%m%d%H%M%S"), 'freq': lastFreq.replace(" ", "_")}

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
         rlog.write( '%(time)s %(freq)s STOP RECORD\n' % {'time': time.strftime("%Y-%m-%d %H:%M:%S"), 'freq': lastFreq})
         f.close()

ser = serial.Serial()
ser.port = '/dev/ttyUSB0'
ser.baudrate = 19200
ser.open()

"""
LCD1 [     +   C 015  ][                ]
LCD2 [  SCAN          ][                ]
LCD3 [Bank  1--------0][      #         ]
LCD4 [                ][                ]
LCD1 [SCAN +   C 020  ][####            ]
LCD2 [ 167.3500  FM   ][                ]
LCD3 [AMK OSL CH 2    ][                ]
LCD4 [BLAALYS         ][                ]
"""
try:

   while run:
      ser.write("LCD\r")
      LCD1 = ser.readline(eol="\r")
      LCD2 = ser.readline(eol="\r")
      LCD3 = ser.readline(eol="\r")
      LCD4 = ser.readline(eol="\r")
      
      #print LCD1,"\n", LCD2, "\n", LCD3, "\n", LCD4

      m1 = re.search('LCD1\s\[(\S+).*\]', LCD1)
      if m1 != None:
         if m1.group(1).strip() == 'SCAN':
            m2 = re.search('LCD2\s\[(.*?)\]', LCD2)
            if m2 != None:
               lastFreq = m2.group(1).strip()
               if doRec == 0:
                  alog.write("%(time)s %(freq)s START\n" % {'time': time.strftime("%Y-%m-%d %H:%M:%S"), 'freq': m2.group(1).strip()})
                  writeout(m2.group(1).strip() + " START")

                  if lastFreq[:8].strip() in ignored_frequencies:
                     writeout(lastFreq + " RESUME SCAN") 
                     ser.write("KEY00\r");
                     ser.readline(eol="\r")
                  else:
                     doRec = 1
                     RecordThread().start()

      else:
         if doRec == 1:
            doRec = 0
            alog.write( "%(time)s %(freq)s END\n" % {'time':time.strftime("%Y-%m-%d %H:%M:%S"), 'freq': lastFreq })
   
      time.sleep(0.2)
   ser.close()
except KeyboardInterrupt:
   writeout("Got ^C. Cleaning up..")
   ser.close()
   doRec = 0
   run = 0

