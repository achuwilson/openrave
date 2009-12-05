#!/usr/bin/env python
#
# Copyright (C) 2009 Rosen Diankov
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License. 
import os, time, signal, threading
import numpy # nice to be able to explicitly call some functions
from numpy import *
from optparse import OptionParser
from openravepy import *

from Tkinter import *
import tkFileDialog
import Image, ImageDraw, ImageTk

class CameraViewerGUI(threading.Thread):
    class Container:
        pass
    def __init__(self,sensor,title='Camera Viewer'):
        threading.Thread.__init__(self)
        self.sensor = sensor
        self.title = title
        self.lastid = -1
        self.imagelck = threading.Lock()

    def updateimage(self):
        data = self.sensor.GetSensorData()
        if data is not None and not self.lastid == data.id:
            width = data.imagedata.shape[1]
            height = data.imagedata.shape[0]
            self.imagelck.acquire()
            self.image = Image.frombuffer('RGB',[width,height], data.imagedata.tostring(), 'raw','RGB',0,1)
            self.imagelck.release()

            photo = ImageTk.PhotoImage(self.image)
            if self.container is None:
                self.container = self.Container()
                self.container.width = width
                self.container.height = height
                self.container.main = self.main
                self.container.canvas = Canvas(self.main, width=width, height=height)
                self.container.canvas.pack(expand=1, fill=BOTH)#side=TOP,fill=X)#
                self.container.obr = None

            self.container.canvas.create_image(self.container.width/2, self.container.height/2, image=photo)
            self.container.obr = photo
            self.lastid = data.id
        self.main.after(100,self.updateimage)

    def saveimage(self,filename):
        self.imagelck.acquire()
        self.image.save(filename)
        self.imagelck.release()

    def run(self):
        self.main = Tk()
        self.main.title(self.title)      # window title
        self.main.resizable(width=True, height=True)
        self.container = None
        self.main.after(0,self.updateimage)
        self.main.mainloop()

class HRP2GraspingScene:
    def __init__(self,scenefilename,robotname=None):
        self.orenv = Environment()
        self.orenv.SetViewer('qtcoin')
        if not self.orenv.Load(scenefilename):
            raise ValueError('failed to open %s openrave file'%scenefilename)
        if len(self.orenv.GetRobots()) == 0:
            raise ValueError('no robots found in scene %s'%scenefilename)

        if robotname is None:
            self.robot = self.orenv.GetRobots()[0]
        else:
            self.robot = [r for r in self.orenv.GetRobots() if r.GetName()==robotname][0]
        
        # create a camera viewer for every camera sensor
        self.viewers = []
        for attachedsensor in self.robot.GetSensors():
            if attachedsensor.GetSensor() is not None:
                sensordata = attachedsensor.GetSensor().GetSensorData()
                if sensordata is not None and sensordata.type == Sensor.SensorType.Camera:
                    attachedsensor.GetSensor().SendCommand('power 1')
                    title = attachedsensor.GetName()
                    if len(title) == 0:
                        title = attachedsensor.GetSensor().GetName()
                        if len(title) == 0:
                            title = 'Camera Sensor'
                    self.viewers.append(CameraViewerGUI(sensor=attachedsensor.GetSensor(),title=title))
        print 'found %d camera sensors on robot %s'%(len(self.viewers),self.robot.GetName())
        for viewer in self.viewers:
            viewer.start()
        self.prevaction = signal.signal(signal.SIGINT,lambda x,y: self.sighandle(x,y))
    
    def sighandle(self,x,y):
        self.quitviewers()
        self.prevaction(x,y)

    def quitviewers(self):
        for viewer in self.viewers:
            viewer.main.quit()
    def __del__(self):
        self.quitviewers()
        self.orenv.Destroy()

if __name__=='__main__':
    parser = OptionParser(description='Visibility Planning Module.')
    parser.add_option('--scene',
                      action="store",type='string',dest='scene',default='scenes/r602cerealmanip.env.xml',
                      help='OpenRAVE scene to load')
    parser.add_option('--robotname',
                      action="store",type='string',dest='robotname',default=None,
                      help='Specific robot sensors to display (otherwise first robot found will be displayed)')
    (options, args) = parser.parse_args()
    scene = HRP2GraspingScene(options.scene,options.robotname)
    scene.quitviewers()