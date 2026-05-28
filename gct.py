"""
Script to analyse what gct is looking like during a run event.
Plan:
1). Bring in the data for a player during a run event.
2). Bring in joint info associated with the player form the run event and build up.
3). Visualoize the run event using the 3d animatiomn plotter.
4). Plot the 'z' coordinates of the 
"""

import pandas as pd
import streamlit as st
import json
import os
import time
import sys
import subprocess

from datetime import datetime
from run_event_animation import create_3d_animation
from football_read_bson import process_bson_files

def quit_program():
    print(f"\nWould you like to quit? \n(y/n)")
    choice = input()
    if choice == 'y':
        return True
    return False

# Create run event parquet file.
def create_run_events_parquet(run_events_dir):
    run_events = sorted(
        [f for f in os.listdir(run_events_dir) if f.endswith('.json')],
        key=lambda x: int(x.split('_run')[0])
    )
    if not run_events:
        print("No run events found")
        return None
    req_cols = ['start_timestamp', 'end_timestamp', 'player_teamId', 'player_roleId', 'player_jerseyNumber',
                'properties_totalRunTime', 'properties_totalSprintTime', 
                'properties_maximumSpeed', 'properties_averageSpeed', 'properties_touches']
    # Create a list fo mini df's and combine all into a big one at the end and write to parquet in pwd. 
    run_event_list = []
    faulty_files = []
    empty_files = []
    for event in run_events:
        try:
            with open(f"{run_events_dir}/{event}", 'r') as run_event_json:
                raw_data = json.load(run_event_json)
                run_event_json.close()

                # Make sure that there is data in the file:
                if not raw_data:
                    print("no data in file")
                    empty_files.append(event)
                    continue
                
                run_event_data_flattened = pd.json_normalize(raw_data, sep='_')[req_cols]
                run_event_list.append(run_event_data_flattened)
        except:
            print('Issue with opening file')
            faulty_files.append(event)
            continue

    # Combine all run_events into 1 df and save:    
    if run_event_list:
        all_run_events_df = pd.concat(run_event_list, ignore_index=True)
        return all_run_events_df
    
    # No run events:
    print()
    return None




# Fucntion to load in the json files from the run events. 
# For now just specify the file path instead of loopiong through. 
def load_run_event_json(file_path):
    print("ABout to begin saving JSON run event data to DF")
    #req_cols = ['start_he_time','end_he_time', 'team_id','role_id', 'jersey_number' ,'total_run_time', 'max_speed', 'min_speed', 'total_distance']
    req_cols = ['start_timestamp', 'end_timestamp', 'player_teamId', 'player_roleId', 'player_jerseyNumber']
    try:    
        with open(file_path, "r") as json_data:
            d = json.load(json_data)
            json_data.close()
            # Lets laod stratight into a df, where nested components become key_1.key_2
            #print(d.head(10))
            if d:
                run_event_flattened = pd.json_normalize(d, sep='_')[req_cols]
                #print(run_event_flattened[req_cols])
                return run_event_flattened
            return None
        
    except: # Add the .json stuff here and use the line from the bson converter.
        print("issue with openeing the file. File path doesnt exsist or file not valid type.")
        return None
    

# Function to create a game half csv of all joints
# csv format:

def load_and_prepare_joint_data(input_dir):
    """
    Load in BSON data fro specified directory, make sure is valid bson format
    and then parse through BSON conversion script. 
    """
    input_bson_files = sorted(
        [f for f in os.listdir(input_dir) if f.endswith('.bson')],
        key = lambda x: int(x.split('.')[0])
    )

    if not input_bson_files:
        print(f"Could not find bson files in specified dir...")
        return None
    
    print("Found Bson files, begining extraction...")

    df = process_bson_files(input_dir, input_bson_files, ball=False, player_joints=True)
    if df is None or df.empty:
        print(f"Data frame either none or empty")
        return None
    
    # Loaded in df of bson files, now ready to process, clean and save the data:
    df['he_time'] = pd.to_numeric(df['he_time'], errors='coerce')
    df.dropna(subset=['he_time'], inplace=True)
    df['x'] = pd.to_numeric(df['x'], errors='coerce')
    df['y'] = pd.to_numeric(df['y'], errors='coerce')
    df['z'] = pd.to_numeric(df['z'], errors='coerce')
    df['team_id'] = pd.to_numeric(df['team_id'], errors='coerce').astype('Int64')
    df['joint_id'] = pd.to_numeric(df['joint_id'], errors='coerce').astype('Int64')
    df['he_time'] = df['he_time'].astype('int64')

    if df.empty:
        print('All valuyes in df were None. nothing to save')
        return None
    
    df.sort_values(by='he_time', inplace=True) # sort by he time
    print("processed and loaded the tracking")

    return df


def load_dashboard(game_name):

    # Need to prepare headline stats too.
    dashboard_script = 'summary_dashboard.py'

    command = [
        sys.executable,
        '-m',
        'streamlit',
        'run',
        dashboard_script,
        str(game_name)
    ]

    try:
        subprocess.run(command, check=True)
    except KeyboardInterrupt:
        print("Closing dashboard.")



def prep_data_for_animation(pre_processed_data):
    #time_to_analyse = 2
    #frame_rate = 50
    #start_he_time = 720651714118321

    all_unique_time = pre_processed_data['he_time'].unique()
    # Should be all sorted but ensure that in chronologic al order:
    #all_unique_time.sort()
    print(f"Sorted {len(all_unique_time)} into chronological order succesfully")

    #if start_he_time not in all_unique_time:
    #    print("Could not find start time  in he_list")
    #    return None

    # Found the start time, now grab the next number
    #total_frames = time_to_analyse * frame_rate
    #start_time_idx = list(all_unique_time).index(start_he_time)
    #he_time_list = all_unique_time[start_time_idx: start_time_idx + total_frames]
    #print(f"Sucesffuly grabbed {total_frames} timestamps")

    # Filter the incoming df for the target times:
    req_cols_for_skeletons = ['x','y', 'z', 'joint_id', 'he_time']
    filtered_rows_subset = pre_processed_data[pre_processed_data['he_time'].isin(all_unique_time)]
    filtered_cols_subset = filtered_rows_subset[req_cols_for_skeletons]

    return filtered_cols_subset, all_unique_time


# Switched from more generic animate 3d skeleton call to gct_anmiation for more detailed animations. 
def animate_3d_skeleton(animation_data, time_list, run_event_id):
    """
    Function to animate a series pre-deterined time windows.
    Find and save the next 
    """
    print("About to start the 3d plot...")
    show_joint_numbers = False
    #joint_segment = "left_fa" # Add this parameter into below fucntion call to isolate just the foot ankle.
    create_3d_animation(animation_data, time_list, run_event_id,show_joint_numbers,color='r')
    


##########
if __name__ == '__main__':

    game_name = '2025_07_05_PSG_Bayern_Munchen'

    run_event_file_path = f"C:/Users/OliverBarbaresi/Documents/projects/football/skeletal/gct/data/{game_name}/ds_football_app_output/{game_name}/run_events/"
    bson_tracking_data_file_path = f"C:/Users/OliverBarbaresi/Documents/projects/football/skeletal/gct/data/2025_07_05_PSG_Bayern_Munchen/input_data/psg_bayern_munich_1h_bsons/"
    current_folder_contents = os.listdir()

    print(f"Welcome to run events app  for game {game_name}!!")
    time.sleep(2)

    counter = 0
    while True:
        if counter != 0:
            quit = quit_program()
            if quit:
                break
        
        # First check to see if there are run events:
        if f"run_events_{game_name}.parquet" not in current_folder_contents:
        # Go to run event dir and create file into current dir.
            run_events_df = create_run_events_parquet(run_event_file_path)
            if run_events_df is None:
                print(f"Run events is empty, quitting program")
                break
                # Save to parquet in pwd:
            print(f"\nStarting run events save to parquet format...")
            run_events_df.to_parquet(f"run_events_{game_name}.parquet")
            print(f"Finished run events parquet save!")
    
        # Next make sure that we have the joint info otherwise process this too:
        if "joint_data_1st_half.parquet" not in current_folder_contents:
            print(f"\nJoint tracking info not in folder.\nBeginining joint data processing...")
            joint_data_df = load_and_prepare_joint_data(bson_tracking_data_file_path)
            if joint_data_df is None:
                print("Processed bson data resulted in a an empty or invalid df...")
                break
            else:
                print("\nSaving joint df to parquet...")
                joint_data_df.to_parquet('joint_data_1st_half.parquet')
                print("Finished saving joint data to parquet")
        
        time.sleep(2)
        print("\nRun events and joint data files successfully found!")
        print("Loading in run events...")
        total_run_events_df = pd.read_parquet(f"run_events_{game_name}.parquet")
        print(total_run_events_df.info(verbose=True))
        print(f"\n{total_run_events_df.head(10)}")
        print(f"\nTotal runs from team 0: {len(total_run_events_df[total_run_events_df['player_teamId'] == 0])}")
        print(f"Total runs from team 1: {len(total_run_events_df[total_run_events_df['player_teamId'] == 1])}")
        print(f"Total runs from team 2: {len(total_run_events_df[total_run_events_df['player_teamId'] == 2])}")

        print(f"\nTotal players from team 0: {total_run_events_df[total_run_events_df['player_teamId'] == 0]['player_jerseyNumber'].nunique()}")
        print(f"Total players from team 1: {total_run_events_df[total_run_events_df['player_teamId'] == 1]['player_jerseyNumber'].nunique()}")
        print(f"Total players from team 2: {total_run_events_df[total_run_events_df['player_teamId'] == 2]['player_jerseyNumber'].nunique()}")

        print("Loading streamlit animation:")

        load_dashboard(game_name)
        
    
        counter =+ 1

        # run events here so lets load in parquet events into workspace:
        #all_run_events_df = pd.read_parquet('')

    time.sleep(2)
    print("thanks for youtr time come back soon!")
    

    """

    # First a program to loop through all run eventsa and save to a local data structure. 1st check if exists
    current_folder_contents = os.listdir()
    if 'run_events.parquet' not in current_folder_contents:
        # Go to run event dir and create file into current dir.
        run_events_df = create_run_events_parquet(run_event_file_path)
        if run_events_df is not None:
            # Save to parquet in pwd:
            run_events_df.to_parquet(f'run_events_{}.parquet')

    # select a run event, but in the finished product this will be looped through to get the gct:
    run_event_id =  '805032150502353'

    run_event_file_path = f"C:/Users/OliverBarbaresi/Documents/projects/football/skeletal/gct/data/2025_07_05_PSG_Bayern_Munchen/ds_football_app_output/2025_07_05_PSG_Bayern_Munchen/run_events/{run_event_id}_run_t0j29.json"
    bson_tracking_data_file_path = f"C:/Users/OliverBarbaresi/Documents/projects/football/skeletal/gct/data/2025_07_05_PSG_Bayern_Munchen/input_data/psg_bayern_munich_1h_bsons/"
    
    run_event_df = load_run_event_json(run_event_file_path)
    if run_event_df is not None:
        print("Loaded the run event data in succesfully!")
        #print(run_event_df.info(verbose=True))
        #print(run_event_df.head(10))
        #start_run_time = datetime.now()

        req_cols = ['he_time', 'x', 'y', 'z', 'grd_z', 'team_id', 'role_id',
        'track_id', 'jersey', 'joint_id']

        # Loop through folder run events:
        for idx, run_event in run_event_df.iterrows():
            
            # Check is there is a csv file contaitining the processed joint outputs, load one in, save and then process the saved with the parquet storage. 

            # Check to see if there is a jpoint data .csv file, othwerwise create one:
            if "joint_data_1st_half.parquet" not in current_folder_contents:
                print(f"\nJoint tracking info not in folder.\nBeginining joint data processing...")
                joint_data_df = load_and_prepare_joint_data(bson_tracking_data_file_path)
                if joint_data_df is None:
                    print("Processed bson data resulted in a an empty or invalid df...")
                else:
                    print("Saving joint df to parquet...")
                    print(joint_data_df.head(10))
                    joint_data_df.to_parquet('joint_data_1st_half.parquet')
                    print("Finished saving joint data to parquet")
            
            print("Found joint data parquet file")
            # Load in filtered version of df from parquet storage:
            req_joint_cols = ['he_time', 'x', 'y', 'z', 'grd_z', 'team_id', 'role_id','track_id', 'jersey', 'joint_id']
            filtered_joint_df = pd.read_parquet(
                'joint_data_1st_half.parquet',
                columns=req_joint_cols,
                filters=[
                    ('team_id', '==', int(run_event['player_teamId'])),
                    ('role_id', '==', int(run_event['player_roleId'])),
                    ('jersey', '==', float(run_event['player_jerseyNumber'])),
                    ('he_time', '>=', run_event['start_timestamp']),
                    ('he_time', '<=', run_event['end_timestamp'])
                ]
            )

            # Now good to build the animation with this filtered data.
            windowed_data, he_time_list = prep_data_for_animation(filtered_joint_df)
            
            print(f"The collected ellapsed time for this event = {float(he_time_list[-1] - he_time_list[0]) * (10**-6)}")
            if windowed_data is None:
                print(f"No data from the windowed event.\nMoving onto the next run event")
                continue
            print("Sneak peak at the windowed data:")
            print(f"{windowed_data.head(40)}\n")
                # Now ready to visualize in 3d:
            animate_3d_skeleton(windowed_data, he_time_list, run_event_id)


        #game_tracking_data = pd.read_parquet('football_tracking_og.parquet', columns=req_cols, dtype_backend='pyarrow').sort_values(by='he_time', ignore_index=True)



   


    else:
        print(f"Issue with loading in run event {run_event_id}")
    # Load in game data into local datasturcture:
    
   
    
    # Check is there is a csv file contaitining the processed joint outputs, load one in, save and then process the saved with the parquet storage. 
    
    """

    """
    game_tracking_data = pd.read_parquet('football_tracking_og.parquet', columns=req_cols, dtype_backend='pyarrow').sort_values(by='he_time', ignore_index=True)



    #game_tracking_data = pd.read_csv(f"football_tracking_og.csv")
    print("Game track data set structure:")
    print(game_tracking_data.info(verbose=True))
    print(game_tracking_data.head(300))
   
    if run_event_df is not None:
        # Next step is to load the joint info and process that per run event:
        for index, row in run_event_df.iterrows():
            print(row)
            print(f'idx = {index} and start_time  = {row['start_timestamp']}')
            #filtered_track_player_data = game_tracking_data[(game_tracking_data['team_id'] == 0) & (game_tracking_data['role_id'] == 1) &
            #                                                (game_tracking_data['jersey'] == 9)] 
            filtered_track_player_data = game_tracking_data[(game_tracking_data['team_id'] == int(row['player_teamId'])) & (game_tracking_data['role_id'] == int(row['player_roleId'])) &
                                                            (game_tracking_data['jersey'] == float(row['player_jerseyNumber'])) & 
                                                            (game_tracking_data['he_time'] >= row['start_timestamp']) & (game_tracking_data['he_time'] <= row['end_timestamp'])] # Probs just save the whole player data first and then save isolate the run event data.
            print(filtered_track_player_data.head(200))
            print(f"\ntotal run time to bring in skeletal data = {datetime.now() - start_run_time}")

            # Now ready to visualize the animation!
            windowed_data, he_time_list = prep_data_for_animation(filtered_track_player_data)
            print(f"TIme list : \n{he_time_list}")
            print(f"\n\n windowed data: \n{windowed_data}")

            print(f"The collected ellapsed time for this event = {float(he_time_list[-1] - he_time_list[0]) * (10**-6)}")
            if windowed_data is not None:
                print("Sneak peak at the windowed data:")
                print(f"{windowed_data.head(40)}\n")

                # Now ready to visualize in 3d:
                animate_3d_skeleton(windowed_data, he_time_list, run_event_id)

    """

##############
##############