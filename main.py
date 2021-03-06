import datetime
import os
import pickle
import time

import cv2
import pygame as pg

from autonomous_vehicle import AutonomousVehicle
from constants import CONSTANTS as C
from controlled_vehicle import ControlledVehicle
from sim_data import Sim_Data
from sim_draw import Sim_Draw

game_joystick = None


class Main():

    def __init__(self):

        # Setupq
        self.duration = 600
        self.P = C.PARAMETERSET_2  # Scenario parameters choice

        # Time handling
        self.clock = pg.time.Clock()
        self.fps = C.FPS
        self.running = True
        self.paused = False
        self.end = False
        self.frame = 0
        self.car_num_display = 0
        self.human_data = []
        self.joystick = None
        self.recordPerson = True

        # Sim output
        #output_name = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

        output_name = 'xiangyu_r'
        os.makedirs("./sim_outputs/%s" % output_name)
        self.sim_data = Sim_Data()
        self.sim_out = open("./sim_outputs/%s/output.pkl" % output_name, "wb")
        self.human_dataFile = open("./sim_outputs/%s/human_data.txt" % output_name, "wb")
        self.robot_dataFile = open("./sim_outputs/%s/robot_data.txt" % output_name, "wb")
        self.fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.out = cv2.VideoWriter("./sim_outputs/%s/recording.avi" % output_name, self.fourcc, 20.0, (640, 480))

        # self.sim_out = open("./sim_outputs/output_test.pkl", "wb")

        # Vehicle Definitions ('aggressive,'reactive','passive_aggressive')
        self.car_1 = ControlledVehicle(scenario_parameters=self.P,
                                       car_parameters_self=self.P.CAR_1,
                                       who=1)  # M
        self.car_2 = AutonomousVehicle(scenario_parameters=self.P,
                                       car_parameters_self=self.P.CAR_2,
                                       loss_style='reactive',
                                       who=0)  # H

        # Assign 'other' cars
        self.car_1.other_car = self.car_2
        self.car_2.other_car = self.car_1
        self.car_2.states_o = self.car_1.states
        self.car_2.actions_set_o = self.car_1.actions_set

        # while not self.init_controller():
        #     print 'Adjust controls'

        self.sim_draw = Sim_Draw(self.P, C.ASSET_LOCATION)

        pg.display.flip()
        self.capture = True  # if input("Capture video (y/n): ") else False
        if self.capture:
            self.output_dir = "./sim_outputs/%s/video/" % output_name
            os.makedirs(self.output_dir)

        if self.recordPerson:
            self.cap = cv2.VideoCapture(0)
        # Go

        self.human_data.append(0)
        self.human_data.append(1)
        self.human_data.append(1)
        self.trial()

    def trial(self):

        while self.running:

            if self.recordPerson:
                try:
                    ret, frame = self.cap.read()
                    if ret:
                        # frame = cv2.flip(frame, 0)
                        self.out.write(frame)
                except Exception, e:
                    print 'Exception: {}'.format(e)

            if game_joystick is not None:
                axes = game_joystick.get_numaxes()

                self.human_data = []
                for i in range(axes):
                    axis = game_joystick.get_axis(i)
                    # print type(axis)
                    # print("Axis {} value: {:>6.3f}".format(i, axis))
                    if i == 0:
                        self.human_data.append(round(axis, 3))
                    elif i == 2:
                        self.human_data.append(round(axis, 3))
                    elif i == 3:
                        self.human_data.append(round(axis, 3))
                print 'human_data: {}'.format(self.human_data)

            if not self.paused:
                self.car_1.update(self.human_data)
                self.car_2.update(self.frame)
                # self.machine_vehicle.update(self.human_vehicle, self.frame)

                # Update data
                self.sim_data.append_car1(states=self.car_1.states,
                                          actions=self.car_1.actions_set,
                                          action_sets=self.car_1.planned_actions_set)

                self.sim_data.append_car2(states=self.car_2.states,
                                          actions=self.car_2.actions_set,
                                          action_sets=self.car_2.planned_actions_set,
                                          predicted_theta_other=self.car_2.predicted_theta_other,
                                          predicted_theta_self=self.car_2.predicted_theta_self,
                                          predicted_actions_other=self.car_2.predicted_actions_other,
                                          predicted_others_prediction_of_my_actions=
                                          self.car_2.predicted_others_prediction_of_my_actions)

            if self.frame >= self.duration:
                break

            sz = len(self.car_1.states)
            sz1 = len(self.car_2.states)
            ts = time.time()
            self.human_dataFile.write(str(self.car_1.states[sz - 1][0]) + ", " + str(self.car_1.states[sz - 1][1]) + ", " + str(ts) + "\n")
            self.robot_dataFile.write(str(self.car_2.states[sz1 - 1][0]) + ", " + str(self.car_2.states[sz1 - 1][1]) + ", " + str(ts) + "\n")

            # Draw frame
            self.sim_draw.draw_frame(self.sim_data, self.car_num_display, self.frame)

            if self.capture:
                pg.image.save(self.sim_draw.screen, "%simg%03d.jpeg" % (self.output_dir, self.frame))

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    pg.quit()
                    self.running = False

                elif event.type == pg.KEYDOWN:
                    if event.key == pg.K_p:
                        self.paused = not self.paused

                    if event.key == pg.K_q:
                        pg.quit()
                        self.running = False

                    if event.key == pg.K_d:
                        self.car_num_display = ~self.car_num_display

            # Keep fps
            self.clock.tick(self.fps)

            if not self.paused:
                self.frame += 1

        pg.quit()
        pickle.dump(self.sim_data, self.sim_out, pickle.HIGHEST_PROTOCOL)

        self.human_dataFile.close()
        self.robot_dataFile.close()
        if self.recordPerson:
            self.cap.release()
            self.out.release()
            cv2.destroyAllWindows()

        print('Output pickled and dumped.')
        if self.capture:
            # Compile to video
            os.system("ffmpeg -f image2 -framerate 5 -i %simg%%03d.jpeg %s/output_video.gif " % (
            self.output_dir, self.output_dir))
            # Delete images
            [os.remove(self.output_dir + file) for file in os.listdir(self.output_dir) if ".jpeg" in file]
            print("Simulation video output saved to %s." % self.output_dir)
        print("Simulation ended.")


if __name__ == "__main__":

    done = False
    pg.init()
    pg.joystick.init()
    joystick_count = pg.joystick.get_count()
    data = []
    while not done:
        print('Please adjust controls, before proceeding.')
        # EVENT PROCESSING STEP
        for event in pg.event.get():  # User did something
            if event.type == pg.QUIT:  # If user clicked close
                done = True  # Flag that we are done so we exit this loop

            # Possible joystick actions: JOYAXISMOTION JOYBALLMOTION JOYBUTTONDOWN JOYBUTTONUP JOYHATMOTION
            if event.type == pg.JOYBUTTONDOWN:
                print("Joystick button pressed.")
            if event.type == pg.JOYBUTTONUP:
                print("Joystick button released.")

        # For each joystick:
        for i in range(joystick_count):
            joystick = pg.joystick.Joystick(i)
            game_joystick = joystick
            game_joystick.init()

            # Get the name from the OS for the controller/joystick
            name = game_joystick.get_name()
            # print("Joystick name: {}".format(name))

            # Usually axis run in pairs, up/down for one, and left/right for
            # the other.
            axes = game_joystick.get_numaxes()
            # print("Number of axes: {}".format(axes))
            data = []
            for i in range(axes):
                axis = game_joystick.get_axis(i)
                # print("Axis {} value: {:>6.3f} round: {}".format(i, axis, round(axis, 0)))
                if i == 0 or i == 2 or i == 3:
                    data.append(round(axis, 3))
            # print(data)
            if data[1] == 1.000 and data[2] == 1.000:
                done = True

    # pg.quit()

    Main()
