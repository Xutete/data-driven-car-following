"""
This is a simulation of car-following and lane changing behaviour on a generic 
section of motorway

Requirements: 
    1. Run M01_Deep_Car_Following_Model first and save the model to a pickle
    2. Run A02_data_distributions and save all the required pickles


Author: Minh Kieu, University of Leeds, Nov 2019
"""
# Import
import numpy as np
import matplotlib.pyplot as plt
import pickle
import pandas as pd

'''
DEFINE AGENTS
'''

class Car:
    def __init__(self, bus_params):
        # Parameters to be defined
        
        #dynamic variables
        self.position = 0 #X position of the car
        self.LaneID = [] #current lane that the vehicle is on
        self.speed = 0 #current speed of the vehicle
        self.acceleration = 0 #current acceleration of the vehicle
        self.is_changing_lane = 0 #1 if the driver is looking for a lane change
        
        [setattr(self, key, value) for key, value in car_params.items()]
        # Fixed parameters
        self.dt = 1 #time interval in seconds of the simulation
        self.Left_Pre_X = [] #position of preceding car on the left
        self.Left_Pre_Speed = []  #speed of preceding car on the left
        self.Left_Al_X = [] #position of alongside car on the left
        self.Left_Al_Speed=[] #speed of alongside car on the left
        self.Left_Fol_X=[] #position of Following car on the left
        self.Left_Fol_Speed=[] #speed of Following car on the left
        self.Right_Pre_X=[]
        self.Right_Pre_Speed=[]
        self.Right_Al_X=[]
        self.Right_Al_Speed=[]
        self.Right_Fol_X=[]
        self.Right_Fol_Speed=[]
        
        return
    def move(self):
        self.speed += self.speed * self.dt
        self.position += self.speed * self.dt
        return

    def change_lane(self): 
        
        #current lane: self.LaneID
        #find out the utility of changing lane to the left    
        
        #find out the utility of changing lane to the right        
        
        
        

class BusStop:
    def __init__(self, position, busstopID, arrival_rate, departure_rate,activation):
        # Parameters to be defined
        self.busstopID = busstopID
        self.position = position
        self.arrival_rate = arrival_rate
        self.departure_rate = departure_rate
        self.actual_headway = []  # store departure times of buses
        self.arrival_time = [0]  # store arrival time of buses
        self.visited = []  # store all visited buses
        self.activation = activation

class Model:
    def __init__(self, model_params, TrafficSpeed0,ArrivalRate,DepartureRate,IncreaseRate,maxDemand):        
        [setattr(self, key, value) for key, value in model_params.items()]        
        # Initial Condition
        self.maxDemand=maxDemand
        self.IncreaseRate=IncreaseRate
        self.TrafficSpeed0 = TrafficSpeed0
        self.TrafficSpeed = TrafficSpeed0
        self.ArrivalRate = ArrivalRate        
        #no passengers board from the first and last stops
        self.ArrivalRate[-1] = 0
        self.ArrivalRate[0] = 0
        self.DepartureRate = DepartureRate
        #no passengers alight from the first two stops, but all alight from the last stop
        self.DepartureRate[0] = 0
        self.DepartureRate[1] = 0
        self.DepartureRate[-1] = 1
        #Fixed parameters
        self.current_time = 0  # current time step of the simulation        
        self.GeoFence = self.dt * TrafficSpeed0 + 5  # an area to tell if the bus reaches a bus stop
        self.StopList = np.arange(0, self.NumberOfStop * self.LengthBetweenStop, self.LengthBetweenStop)  # this must be a list
        self.FleetSize = int(self.EndTime / self.Headway)
        self.initialise_busstops()
        self.initialise_buses()        
        return
    
    #we need this agent2state for future application of data assimilation
    def agents2state(self, do_measurement=False):
        '''
        This function stores the system state of all agents in a state vector with format:
            [bus_status1,bus_position1,bus_velocity1,...,bus_statusN,bus_positionN,bus_velocityN,busstop_arrivalrate1,busstop_departurerate1,...,busstop_arrivalrateM,busstop_departurerateM,TrafficSpeed]
        '''
        state_bus = np.ravel([(bus.status, bus.position, bus.velocity, bus.occupancy) for bus in self.buses])
        if do_measurement:
            state = state_bus  # other data not provided
        else:
            state_busstop = np.ravel([(busstop.arrival_rate, busstop.departure_rate) for busstop in self.busstops])
            state_traffic = np.ravel(self.TrafficSpeed)
            state = np.concatenate((state_bus, state_busstop, state_traffic))
        return state

    #similar to the previous function
    def state2agents(self, state):
        '''
        This function converts the stored system state vectir back into each agent state
        '''
        # buses status, position and velocity
        for i in range(len(self.buses)):
            self.buses[i].status = int(state[4 * i])
            self.buses[i].position = state[4 * i + 1]
            self.buses[i].velocity = state[4 * i + 2]
            self.buses[i].occupancy = int(state[4 * i + 3])
        # bus stop arrival and departure rate
        for i in range(len(self.busstops)):
            self.busstops[i].arrival_rate = state[4 * self.FleetSize + 2 * i]
            self.busstops[i].departure_rate = state[4 * self.FleetSize + 2 * i + 1]
        # traffic speed
        self.TrafficState = state[-1]
        return
    
    '''
    DEFINE THE STEP FUNCTION TO MOVE AGENTS TO THE NEXT TIME STEP
    '''

    def step(self):
        '''
        This function moves the whole state one time step ahead
        '''
        
        #Apply dynamic changes at every time step
        # Decrease the traffic Speed every 100 time steps, until the traffic speed is 20% off at the EndTime
        self.TrafficSpeed = self.TrafficSpeed0 * (1-self.current_time/((100/self.IncreaseRate)*self.EndTime))
        # increase the arrival rate every 100 time step, until the demand is 50% more        
        self.ArrivalRate = np.random.uniform(self.minDemand* (1+self.current_time/((100/self.IncreaseRate)*self.EndTime)) / 60, self.maxDemand * (1+self.current_time/((100/self.IncreaseRate)*self.EndTime)) / 60, self.NumberOfStop)
        for busstop in self.busstops:
            busstop.arrival_rate = self.ArrivalRate[busstop.busstopID]
        
        # This is the main step function to move the model forward
        self.current_time += self.dt
        # Loop through each bus and let it moves or dwells
        for bus in self.buses:
            #print('now looking at bus ',bus.busID)
            # CASE 1: INACTIVE BUS (not yet dispatched)
            if bus.status == 0:  # inactive bus (not yet dispatched)
                # check if it's time to dispatch yet?
                # if the bus is dispatched at the next time step
                if self.current_time >= (bus.dispatch_time - self.dt):
                    bus.status = 1  # change the status to moving bus
                    bus.velocity = min(self.TrafficSpeed, bus.velocity + bus.acceleration * self.dt)
            # CASE 2: Moving buses ( on the road)        
            if bus.status == 1:  # moving bus
                bus.velocity = min(self.TrafficSpeed, bus.velocity + bus.acceleration * self.dt)
                bus.move()
                if bus.position > self.NumberOfStop * self.LengthBetweenStop:
                    bus.status = 3  # this is to stop bus after they reach the last stop
                    bus.velocity = 0
                # if after moving, the bus enters a bus stop with passengers on it, then we move the status to dwelling
                def dns(x, y): return abs(x - y)
                if min(dns(self.StopList, bus.position)) <= self.GeoFence:  # reached a bus stop
                    # Investigate the info from the current stop
                    Current_StopID = int(min(range(len(self.StopList)), key=lambda x: abs(self.StopList[x] - bus.position)))  # find the nearest bus stop
                    #print('Current_StopID:',Current_StopID)   
                    if Current_StopID != bus.visited:
                        #Store the visited stop                         
                        bus.visited = Current_StopID
                        # passenger arrival rate
                        arrival_rate = self.busstops[Current_StopID].arrival_rate
                        if arrival_rate<0: arrival_rate=0
                        # passenger departure rate
                        departure_rate = self.busstops[Current_StopID].departure_rate
                        # Now calculate the number of boarding and alighting
                        boarding_count = 0
                        # if the bus is the first bus to arrive at the bus stop
                        if self.busstops[Current_StopID].arrival_time[-1] == 0:
                            if self.busstops[Current_StopID].activation <= self.current_time:
                                boarding_count = np.random.poisson(arrival_rate * self.Headway)
                            alighting_count = int(bus.occupancy * departure_rate)
                        else:
                            timegap = self.current_time - self.busstops[Current_StopID].arrival_time[-1]
                            boarding_count = min(np.random.poisson(arrival_rate*timegap), bus.size - bus.occupancy)                        
                            alighting_count = int(bus.occupancy * departure_rate)
                        # If there is at least 1 boarding or alighting passenger
                        if boarding_count > 0 or alighting_count > 0:  # there is at least 1 boarding or alighting passenger
                            # change the bus status to dwelling
                            bus.status = 2  # change the status of the bus to dwelling
                            bus.velocity = 0                            
                            bus.leave_stop_time = self.current_time + boarding_count * self.BoardTime + alighting_count * self.AlightTime + self.StoppingTime  # total time for dwelling
                            bus.occupancy = min(bus.occupancy - alighting_count + boarding_count, bus.size)
                        # store the headway and arrival times
                        self.busstops[Current_StopID].arrival_time.extend([self.current_time])  # store the arrival time of the bus
                        if self.busstops[Current_StopID].arrival_time[-1] != 0:
                            self.busstops[Current_StopID].actual_headway.extend([self.current_time - self.busstops[Current_StopID].arrival_time[-1]])# store the headway to the previous bus                            
                        

            # CASE 3: DWELLING BUS (waiting for people to finish boarding and alighting)
            if bus.status == 2:
                # check if people has finished boarding/alighting or not?
                # if the bus hasn't left and can leave at the next time step
                if self.current_time >= (bus.leave_stop_time - self.dt):
                    bus.status = 1  # change the status to moving bus
                    bus.velocity = min(self.TrafficSpeed, bus.velocity + bus.acceleration * self.dt)

            bus.groundtruth.append([bus.status, bus.position, bus.velocity, bus.occupancy])
            bus.trajectory.extend([bus.position])
        return

    def initialise_busstops(self):
        self.busstops = []
        for busstopID in range(len(self.StopList)):
            position = self.StopList[busstopID]  # set up bus stop location
            # set up bus stop location
            arrival_rate = self.ArrivalRate[busstopID]
            # set up bus stop location
            departure_rate = self.DepartureRate[busstopID]
            activation = busstopID * int(self.LengthBetweenStop/(self.TrafficSpeed)) - 1*60
            # define the bus stop object and add to the model
            busstop = BusStop(position, busstopID, arrival_rate, departure_rate,activation)
            self.busstops.append(busstop)
        return

    def initialise_buses(self):
        self.buses = []
        for busID in range(self.FleetSize):
            bus_params = {
                "dt": self.dt,
                "busID": busID,
                # all buses starts at the first stop,
                "position": -self.TrafficSpeed * self.dt,
                "occupancy": 0,
                "size": 100,
                "acceleration": self.BusAcceleration / self.dt,
                "velocity": 0,  # staring speed is 0
                "leave_stop_time": 9999,  # this shouldn't matter but just in case
                "dispatch_time": busID * self.Headway,                
                "status": 0  # 0 for inactive bus, 1 for moving bus, and 2 for dwelling bus, 3 for finished bus
                }
            # define the bus object and add to the model
            bus = Bus(bus_params)
            self.buses.append(bus)
        return

def run_model(model_params,TrafficSpeed,ArrivalRate,DepartureRate,IncreaseRate,do_ani,do_spacetime_plot,do_reps,uncalibrated):  #this function is to quickly run the model
    '''
    Model runing and plotting
    '''
    model = Model(model_params, TrafficSpeed,ArrivalRate,DepartureRate,IncreaseRate)

    if do_ani or do_spacetime_plot or uncalibrated:
        for time_step in range(int(model.EndTime / model.dt)):
            model.step()
            if do_ani:
                text0 = ['Traffic Speed:  %.2f m/s' % (model.TrafficSpeed)]
                plt.text(0, 0.025, "".join(text0))
                text2 = ['Alighted passengers:  %d' % (len(model.alighted_passengers))]
                plt.text(0, 0.02, "".join(text2))
                plt.text(0, 0.015, 'Number of waiting passengers')
                plt.plot(model.StopList, np.zeros_like(model.StopList), "|", markersize=20, alpha=0.3)
                plt.plot(model.StopList, np.zeros_like(model.StopList), alpha=0.3)
                for busstop in model.busstops:
                    # this is the value where you want the data to appear on the y-axis.
                    val = 0.
                    plt.plot(busstop.position, np.zeros_like(busstop.position) + val, 'ok', alpha=0.2)
                    plt.text(busstop.position, np.zeros_like(busstop.position) + val + 0.01, len(busstop.passengers))
                for bus in model.buses:
                    plt.plot(bus.position, np.zeros_like(bus.position) + val, '>', markersize=10)
                    text1 = ['BusID= %d, occupancy= %d, speed= %.2f m/s' % (bus.busID + 1, len(bus.passengers), bus.velocity)]
                    if bus.status != 0:
                        plt.text(0, -bus.busID * 0.003 - 0.01, "".join(text1))
                plt.axis('off')
                plt.pause(1 / 30)
                plt.clf()
            plt.show()
        if do_spacetime_plot :
            plt.figure(3, figsize=(16 / 2, 9 / 2))
            x = np.array([bus.trajectory for bus in model.buses]).T        
            t = np.arange(0, model.EndTime, model.dt)
            x[x <= 0 ] = np.nan
            x[x >= (model.NumberOfStop * model.LengthBetweenStop)] = np.nan            
            plt.ylabel('Distance (m)')
            plt.xlabel('Time (s)')
            plt.plot(t, x, linewidth=.5,linestyle = '-')
            plt.pause(1 / 300) 
        
        if  uncalibrated:
            plt.figure(3, figsize=(16 / 2, 9 / 2))
            #plt.clf()            
            x = np.array([bus.trajectory for bus in model.buses]).T        
            t = np.arange(0, model.EndTime, model.dt)
            x[x <= 0 ] = np.nan
            x[x >= (model.NumberOfStop * model.LengthBetweenStop)] = np.nan            
            plt.ylabel('Distance (m)')
            plt.xlabel('Time (s)')
            plt.plot(t, x, linewidth=.5,linestyle = '--')
            plt.pause(1 / 300)    
        
        '''
        Now export the output data
        '''
   
        GPSData = model.buses[0].trajectory
        for b in range(1, model.FleetSize):
            GPSData = np.vstack((GPSData, model.buses[b].trajectory))
        GPSData[GPSData < 0] = 0        
        GPSData=np.transpose(GPSData)

        StateData = model.buses[0].states
        for b in range(1, model.FleetSize):
            StateData = np.hstack((StateData, model.buses[b].states))
        StateData[StateData < 0] = 0
    
        import pandas as pd
        GroundTruth = pd.DataFrame(model.buses[0].groundtruth)
        for b in range(1, model.FleetSize):
            GroundTruth = np.hstack((GroundTruth, model.buses[b].groundtruth))
        GroundTruth[GroundTruth < 0] = 0
    
        ArrivalData = ()
        for b in range(len(model.busstops)):
            ArrivalData += tuple([model.busstops[b].arrival_time])
                
        return model, model_params, ArrivalData, StateData, GroundTruth, GPSData

    if do_reps: #make a lot of replications
        RepGPS = []
        
        for time_step in range(int(model.EndTime / model.dt)):
            model.step()                
        
        RepGPS = model.buses[0].trajectory
        for b in range(1, model.FleetSize):
            RepGPS = np.vstack((RepGPS, model.buses[b].trajectory))
        RepGPS[RepGPS < 0] = 0        
        RepGPS=np.transpose(RepGPS)       
      
        return RepGPS        
 
def plot(model_params, StateData, GroundTruth):
    # plotting the space-time diagram
    GroundTruth[GroundTruth == 0] = np.nan
    GroundTruth[GroundTruth > (model_params['NumberOfStop'] * model_params['LengthBetweenStop'])] = np.nan
    StateData[StateData == 0] = np.nan
    StateData[StateData > (model_params['NumberOfStop']*model_params['LengthBetweenStop'])] = np.nan
    plt.plot(StateData[:, range(1, np.size(GroundTruth, 1), 4)])    
    return

if __name__ == '__main__':
    
    NumberOfStop=20
    minDemand=0.5
    maxDemand=1
    #Initialise the ArrivalRate and DepartureRate
    ArrivalRate = np.random.uniform(minDemand / 60, maxDemand / 60, NumberOfStop)
    DepartureRate = np.sort(np.random.uniform(0.05, 0.5,NumberOfStop))
    #DepartureRate = np.linspace(0.05, 0.5,NumberOfStop)
    DepartureRate[0]=0
    TrafficSpeed=14
    #Initialise the model parameters
    model_params = {        
        "dt": 10,
        "minDemand":minDemand,
        "maxDemand":maxDemand,
        "NumberOfStop": NumberOfStop,
        "LengthBetweenStop": 2000,
        "EndTime": 6000,
        "Headway": 5 * 60,
        "BurnIn": 1 * 60,
        "AlightTime": 1,
        "BoardTime": 3,
        "StoppingTime": 3,
        "BusAcceleration": 3  # m/s          
    }

    #runing parameters    
    
    do_reps = False #whether we should export the distribution of headways
    do_spacetime_plot = False
    do_ani = False
    do_spacetime_rep_plot = False
    uncalibrated=False
    do_data_export_realtime = False
    do_data_export_historical= False
    do_two_plots = True
    
    if do_two_plots:                 
        plt.figure(3, figsize=(16 / 2, 9 / 2))
        plt.clf() 

        IncreaseRate=1
        model = Model(model_params, TrafficSpeed,ArrivalRate,DepartureRate,IncreaseRate)
        for time_step in range(int(model.EndTime / model.dt)):
            model.step()
        x = np.array([bus.trajectory for bus in model.buses]).T        
        t = np.arange(0, model.EndTime, model.dt)
        x[x <= 0 ] = np.nan
        x[x >= (model.NumberOfStop * model.LengthBetweenStop)] = np.nan            
        plt.plot(t, x,'r', linewidth=1,linestyle = '--')
        
        IncreaseRate=10
        model = Model(model_params, TrafficSpeed,ArrivalRate,DepartureRate,IncreaseRate)
        for time_step in range(int(model.EndTime / model.dt)):
            model.step()
        x = np.array([bus.trajectory for bus in model.buses]).T        
        t = np.arange(0, model.EndTime, model.dt)
        x[x <= 0 ] = np.nan
        x[x >= (model.NumberOfStop * model.LengthBetweenStop)] = np.nan            
        plt.ylabel('Distance (m)')
        plt.xlabel('Time (s)')
        plt.plot(t, x,'k', linewidth=1.5,linestyle = '-')
                
        plt.plot([],[], 'r',linestyle = '--',linewidth=1, label='Dynamic change = 1%')
        plt.plot([],[], 'k',linestyle = '-',linewidth=1.5, label='Dynamic change = 10%')
        plt.legend()           
        plt.show()
        plt.savefig('Fig_spacetime_2dynamic.pdf', dpi=200,bbox_inches='tight')
        do_spacetime_plot=False    

    if do_ani or do_spacetime_plot:
        model, model_params, ArrivalData, StateData, GroundTruth,GPSData = run_model(model_params,TrafficSpeed,ArrivalRate,DepartureRate,IncreaseRate,do_ani,do_spacetime_plot,do_reps,uncalibrated)
        plt.show()
        
        with open('BusSim_data_dynamic.pkl', 'wb') as f:
            pickle.dump([model_params, ArrivalRate, ArrivalData, DepartureRate, StateData, GroundTruth,GPSData], f)
    
    GPSData = []
    if do_reps:
        NumReps = 100
        #GPSData = [run_model(model_params,do_ani,do_spacetime_plot,do_reps,uncalibrated)]
        for r in range(NumReps):
            RepGPS = run_model(model_params,TrafficSpeed,ArrivalRate,DepartureRate,IncreaseRate,do_ani,do_spacetime_plot,do_reps,uncalibrated)             
            GPSData.append(RepGPS)            
        meanGPS = np.mean(GPSData,axis=0)
        stdGPS = np.std(GPSData,axis=0)
        
        
        with open('BusSim_headway_100reps_dynamic_IncreaseRate_70percent.pkl', 'wb') as f:
            pickle.dump([model_params,meanGPS,stdGPS], f)
            
    if do_spacetime_rep_plot:  #plot a few replications using the same data to see the spread        
        NumReps = 20
        do_spacetime_plot = True
        uncalibrated = False
        for r in range(NumReps):
            run_model(model_params,TrafficSpeed,ArrivalRate,DepartureRate,IncreaseRate,do_ani,do_spacetime_plot,do_reps,uncalibrated)    

        model2 = Model(model_params, TrafficSpeed,ArrivalRate,DepartureRate,IncreaseRate)
        for time_step in range(int(model2.EndTime / model2.dt)):
            model2.step()

        x = np.array([bus.trajectory for bus in model2.buses]).T        
        t = np.arange(0, model2.EndTime, model2.dt)
        x[x <= 0 ] = np.nan
        x[x >= (model2.NumberOfStop * model2.LengthBetweenStop)] = np.nan            
        plt.ylabel('Distance (m)')
        plt.xlabel('Time (s)')
        plt.plot(t, x, linewidth=2, color='black')
        plt.pause(1 / 300) 
        plt.plot([],[], 'r',linestyle = '-',linewidth=.5, label='Historical')
        plt.plot([],[], 'black',linestyle = '-',linewidth=2, label='Real-time')
        plt.legend()
        plt.show()
        plt.savefig('Fig_spacetime_dynamic.pdf', dpi=200,bbox_inches='tight')

        GroundTruth = pd.DataFrame(model2.buses[0].groundtruth)
        for b in range(1, model2.FleetSize):
            GroundTruth = np.hstack((GroundTruth, model2.buses[b].groundtruth))
        GroundTruth[GroundTruth < 0] = 0


        with open('Synthetic_realtime_GPS.pkl','wb') as f2:
            pickle.dump([model_params,t,x,GroundTruth],f2)
            

    if do_data_export_realtime: #this is the section where we export multiple pickles, each is for a synthetic 'real-time' GPS data of IncreaseRate
        do_spacetime_plot = True        
        for IncreaseRate in range(1,21,1):        
            model2 = Model(model_params, TrafficSpeed,ArrivalRate,DepartureRate,IncreaseRate)
            for time_step in range(int(model2.EndTime / model2.dt)):
                model2.step()
            
            #del model2.buses[0] #remove the first bus 
            
            plt.figure(3, figsize=(16 / 2, 9 / 2))
            plt.clf() 
            x = np.array([bus.trajectory for bus in model2.buses]).T        
            t = np.arange(0, model2.EndTime, model2.dt)
            x[x <= 0 ] = np.nan
            x[x >= (model2.NumberOfStop * model2.LengthBetweenStop)] = np.nan            
            plt.ylabel('Distance (m)')
            plt.xlabel('Time (s)')
            plt.plot(t, x, linewidth=1)
            #plt.pause(1 / 300) 
            #plt.plot([],[], 'r',linestyle = '-',linewidth=.5, label='Historical')
            #plt.plot([],[], 'black',linestyle = '-',linewidth=2, label='Real-time')
            #plt.legend()
            name0 = ['C:/Users/geomlk/Dropbox/Minh_UoL/DA/ABM/BusSim/Figures/Fig_spacetime_IncreaseRate_',str(IncreaseRate),'.pdf']
            str1 = ''.join(name0)
            plt.savefig(str1, dpi=200,bbox_inches='tight')    
            
            GroundTruth = pd.DataFrame(model2.buses[0].groundtruth)
            for b in range(1, model2.FleetSize):
                GroundTruth = np.hstack((GroundTruth, model2.buses[b].groundtruth))
            GroundTruth[GroundTruth < 0] = 0    
            
            name0 = ['C:/Users/geomlk/Dropbox/Minh_UoL/DA/ABM/BusSim/Data/Realtime_data_IncreaseRate_',str(IncreaseRate),'.pkl']
            str1 = ''.join(name0)    
            with open(str1,'wb') as f2:
                pickle.dump([model_params,t,x,GroundTruth],f2)

    if do_data_export_historical:  #plot a few replications using the same data to see the spread        
        do_reps=True
        NumReps = 20
        for IncreaseRate in range(11,21,1):
            print('Increase Rate = ',IncreaseRate)
            for r in range(NumReps):
                RepGPS = run_model(model_params,TrafficSpeed,ArrivalRate,DepartureRate,IncreaseRate,do_ani,do_spacetime_plot,do_reps,uncalibrated)             
                GPSData.append(RepGPS)            
            meanGPS = np.mean(GPSData,axis=0)
            stdGPS = np.std(GPSData,axis=0)
            name0 = ['C:/Users/geomlk/Dropbox/Minh_UoL/DA/ABM/BusSim/Data/Historical_data_IncreaseRate_',str(IncreaseRate),'.pkl']
            str1 = ''.join(name0)    
            with open(str1,'wb') as f2:
                pickle.dump([model_params,meanGPS,stdGPS],f2)
     
