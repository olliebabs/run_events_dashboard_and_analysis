"""
take in a df which contains a spcefiied time widnow or range of a df.
plot using a 3d visualizer. 
Contains 'show_joint_numbers' variable which toggles the joint numbers to be shown on the skeleton. 
Adding a zoom, and a start/stop button onto the visual.
Next itteration will have a subset of the joints. i.e select a limb segment and just visualize that only.
"""

import matplotlib.pyplot as plt
import matplotlib.animation as animation

from matplotlib.widgets import Button, Slider # Stopped using the slider for now (Zoom based slider to start with.)
from matplotlib.animation import FuncAnimation
import matplotlib.gridspec as gridspec

import pandas as pd
import numpy as np

is_paused = False
current_frame = 0

def create_3d_animation(animation_subset, target_timestamps, run_event_id,show_joint_numbers=False, joint_seg=None, color='r'):
    # Define figure and axis limits:
    fig = plt.figure(1, figsize=(8,7))
    #ax = fig.add_subplot(121, projection="3d")
    #ax_joint_graph = fig.add_subplot(122)
    


    gs = gridspec.GridSpec(3,2, width_ratios=[1.2,1], wspace=0.3,hspace=0.4) # This defines the 3d grid to put the skeletons and the plots

    ax = fig.add_subplot(gs[:,0], projection="3d") # Plot area for the skeleton
    

    ax_joint_graph_21 = fig.add_subplot(gs[0,1]) # Plot area for heel joint 
    ax_joint_graph_20 = fig.add_subplot(gs[1,1]) # Plot area for big toe
    ax_joint_graph_19 = fig.add_subplot(gs[2,1]) # Plot area for little toe

    graph_ax = [ax_joint_graph_21, ax_joint_graph_20, ax_joint_graph_19]
    joint_columns = [
        21,
        20,
        19,
    ]  # Replace with your actual column names
    colors = ["blue", "green", "purple"]
    labels = ["21 Z", "20 Z", "19 Z"]

    # Animation state variable:
     # Default is to not be pasused and then toggle if selected.

    #Finding 3d coordinate constraints for the skeletal viuslation script:
    x_min, x_max = animation_subset['x'].min(), animation_subset['x'].max()
    y_min, y_max = animation_subset['y'].min(), animation_subset['y'].max()
    z_min, z_max = (
        0,
        2.5
    ) # maybe update this after. - probs include a slightly negative z aswell, sicne pitch not perfectly flat. 

    # Brining in the z data for a joint to get the run event plotting logic (lets start with left heel (joint_21)):

    """
    Legacy code for 1 plot only:
    left_heel_data = animation_subset[animation_subset['joint_id'] == 21]

    # only want the z data:
    #left_heel_z_data = left_heel_data['z']

    # Creat sub plot of the subplot:
    #foot_joint_subplots = ax_joint_graph.add_s

    #Run event z point plot:
    ax_joint_graph.plot(
        left_heel_data['he_time'],
        left_heel_data['z'],
        label="Z value",
        color='blue',
        alpha=0.7 # check what this alpha thing does.
    )

    # Title and label the plot:
    ax_joint_graph.set_xlabel('time')
    ax_joint_graph.set_ylabel('z position')
    ax_joint_graph.set_title("Z position of the heel:")
    ax_joint_graph.legend(loc='upper left')

    # Add the tracker line that moves with the animation:
    start_time = left_heel_data['he_time'].iloc[0]
    tracker_line = ax_joint_graph.axvline(
        x=start_time, color='red', linestyle='--', linewidth=1.5
    )


    """
    tracker_lines = []
    start_he_time = animation_subset['he_time'].iloc[0]

    # do the initial plots for the 3 different joints and then define the tracker line that will zip through:
    for idx, (ax_joint_graph, col, color, label) in enumerate(zip(graph_ax, joint_columns, colors, labels)):
        
        # Grab the data for the joint first and then create the plot:
        joint_data = animation_subset[animation_subset['joint_id'] == col]
        relative_time = joint_data['he_time'] - start_he_time

        ax_joint_graph.plot(
            relative_time,
            joint_data['z'],
            label=label,
            color=color,
            alpha=0.7 
        )

        # And now plot the velocity. velocity being then the change in disatnce with time.
        delta_z = joint_data['z'].diff(periods=2)
        delta_t = (joint_data['he_time'].diff(periods=2)) * 10**-6
        #print(f"\ndleta z :")
        #print(delta_z.head(10))
        #print(f'\ndelta t:')
        #print(delta_t.head(10))
        velocity_z = (delta_z/delta_t).shift(-1)
        velocity_z = velocity_z.fillna(0)

        # And now for the accleration:
        delta_v = velocity_z.diff(periods=2)
        acceleration_z = (delta_v/delta_t).shift(-1).fillna(0)

        ax_velocity = ax_joint_graph.twinx()
        ax_velocity.axhline(0, color='black', linestyle='-', linewidth=1, alpha=0.3)

        ax_velocity.plot(
            relative_time,
            velocity_z,
            label=label,
            color=color,
            linestyle='--',
            alpha=0.5 # check what this alpha thing does. This is the transparancy.!
        )

        #Accel axis and its right shift:
        ax_accel = ax_joint_graph.twinx()
        ax_accel.spines['right'].set_position(('axes',1.08))

        ax_accel.plot(
            relative_time,
            acceleration_z,
            label=label,
            color=color,
            linestyle=':',
            alpha=0.6

        )


        # Title and label the plot:
        if idx == len(joint_columns) -1:
            ax_joint_graph.set_xlabel('time')
            ax_velocity.set_ylabel('Velocity')
            ax_accel.set_ylabel('Accel')
        ax_joint_graph.set_ylabel('z position')
        ax_joint_graph.set_title(f"Joint {col}")
        
        #ax_joint_graph.legend(loc='upper left')

        # Maybe add in the y-limts here based on what the values are: (for the 3 plots actualyl best to fix to max of the 3 so same.)
        ##############

        # Add the tracker line that moves with the animation:
        tracker_line = ax_joint_graph.axvline(
            x=0, color='red', linestyle='--', linewidth=1.5
        )

        tracker_lines.append(tracker_line)






    # Create pause and play buttons and fucntionality:
    def toggle_pause(event):
        global is_paused
        if is_paused: # event is clciking the button, resume the animation and change the button text back to pause.
            ani.resume()
            button_pause.label.set_text("Pause")
        else:
            ani.pause()
            button_pause.label.set_text("Play")
        is_paused = not is_paused # Flip the global variable after the event.
        fig.canvas.draw_idle()

    #define the zoom stuff:
    def update_zoom(val):
        current_zoom = val

        x_center = (x_max + x_min) /2
        y_center = (y_max + y_min) /2
        z_center = (z_max + z_min) /2

        ax.set_xlim(x_center - current_zoom, x_center + current_zoom)
        ax.set_ylim(y_center - current_zoom, y_center + current_zoom)
        ax.set_zlim(z_center - current_zoom, z_center + current_zoom)

        fig.canvas.draw_idle() # this creates the button.

    # Define the button and zoom stuff too:
    ax_pause = plt.axes([0.45,0.02,0.1,0.040])
    button_pause = Button(ax_pause, "Pause", color='lightgray', hovercolor='0.9')
    button_pause.on_clicked(toggle_pause)

    # Frame by frame arrow buttons:
    ax_prev = plt.axes([0.39, 0.02, 0.04, 0.04])
    ax_next = plt.axes([0.57, 0.02, 0.04, 0.04])

    btn_prev = Button(ax_prev, "<")
    btn_next = Button(ax_next, ">")

    total_frames = len(animation_subset)

    # Silly scipt to try to get a scroller, didnt work very well :(
    #ax_zoom = plt.axes([0.2,0.13,0.6,0.03])
    #initial_range = (x_max - x_min) / 2
    #slider_zoom = Slider(
    #    ax_zoom,
    #    "Zoom Range",
    #    initial_range * 0.2,
    #    initial_range * 2.0,
    #    valinit=initial_range,
    #)
    #slider_zoom.on_changed(update_zoom)
    
        

    

    def update(frame_number):
        global is_paused, current_frame

        # Sync counter to ensure that we know what the current frame is:
        if not is_paused:
            current_frame = frame_number

        #Save previous parameters before clearing the screen this time more for the rubbsih zoom stuff:
        current_xlim = ax.get_xlim()
        current_ylim = ax.get_ylim()
        current_zlim = ax.get_zlim()

        # clear previous frame:
        ax.clear()

        # Ensure that the axis limits are locked and equal: # only use these if notusing the zoom function!!
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        ax.set_zlim(z_min, z_max)
        #ax.set_xlim(current_xlim)
        #ax.set_ylim(current_ylim)
        #ax.set_zlim(current_zlim)

        # Force equal scsaling to avoid the frog stick person:
        ax.set_aspect('equal')
        ax.set_box_aspect(None) # Double check this bit !!!!

        #Labelling to stays constant too: #  Double check the units. 
        ax.set_xlabel('X (Width)')
        ax.set_ylabel('Y (Length)')
        ax.set_zlabel('Z (Height)')
        ax.set_title(f'Run Event: {run_event_id}')

        # Establish the current he time from the preloaded he times:
        current_he_time = target_timestamps[frame_number]
        #print("Current he time = " + str(current_he_time))

        # Then isolate the joint info for the proposed time:
        skeletal_data_4_frame = animation_subset[(animation_subset['he_time'] == current_he_time) & (animation_subset['joint_id'] != "NaN")].copy()
        #print(skeletal_data_4_frame.info(verbose=True))
        # Convert to numeric 


        skeletal_data_4_frame_cleaned = skeletal_data_4_frame.dropna(subset=['joint_id'])
        #print("--------------------------------")
        #print(skeletal_data_4_frame_cleaned.head(30))
        

        #Now construct the skeletons with Jess skelton builder script:
        # Define the core connections based on the provided joint IDs

        if joint_seg == "left_fa": # Joint segemnts for left foot ankle only. 
            joint_connections = [
                (13,14), (14, 19), (14, 20), (14, 21)
            ]
        else:
            joint_connections = [
                (0, 1), (1, 2), (2, 3), (3, 4),
                (1, 5), (5, 6), (6, 7),
                (8, 9), (9, 10), (10, 11),
                (8, 12), (12, 13), (13, 14),
                (0, 15), (0, 16), (15, 17), (16, 18),
                (14, 19), (14, 20), (14, 21),
                (11, 22), (11, 23), (11, 24),
                (7, 25), (7, 26),
                (4, 27), (4, 28),
                (2, 9), (5, 12), (9, 12) # Trunk connections
            ]

        




        joints = skeletal_data_4_frame_cleaned.set_index('joint_id')

        x_list, y_list, z_list = [], [], []
        for start_id, end_id in joint_connections:
            if start_id in joints.index and end_id in joints.index:
                p1 = joints.loc[start_id]; p2 = joints.loc[end_id]
                x_list.extend([p1['x'], p2['x'], np.nan])
                y_list.extend([p1['y'], p2['y'], np.nan])
                z_list.extend([p1['z'], p2['z'], np.nan])

        
        ax.plot(x_list, y_list, z_list, color=color, marker='o', markersize=2, alpha=0.7)
        #ax.scatter(joints['x'], joints['y'], joints['z'], s=10, c=color, zorder=3)

        if show_joint_numbers == True:
            for _, row in skeletal_data_4_frame_cleaned.iterrows():
                joint_num = row['joint_id']
                x,y,z = row['x'], row['y'], row['z'] # Grab x,y,z of where the joint actually is before then adding a slight offset to it:
                ax.text(
                    x + 0.025,
                    y,
                    z + 0.025,
                    str(int(joint_num)),
                    color="black",
                    fontsize=6,
                    weight="bold"
                )

        # Add the superimposed track line to the visual:
        #print(f"frame_number = {frame_number}")
        for line in tracker_lines:
            line.set_xdata([current_he_time - start_he_time])


    def step_forward(event):
        global current_frame
        if is_paused:
            if current_frame < total_frames - 1:
                print(f"curent frame = {current_frame}")

                current_frame += 1
                update(current_frame)
                #print(f"current frame = {current_frame}") 
                fig.canvas.draw_idle()

            
    def step_backward(event):
        global current_frame
        if is_paused:
            if current_frame > 0:
                current_frame -= 1
                update(current_frame)
                fig.canvas.draw_idle()

    btn_next.on_clicked(step_forward)
    btn_prev.on_clicked(step_backward)

    # Create the animation:
    ani = animation.FuncAnimation(
        fig, update, frames=len(target_timestamps), interval=20, blit=False
    ) # Double check what the blit does!!! # Interval = 1000(ms) / Camera rate(Hz)
    


    #Plot:
    plt.show()