import os
import bson
import snappy
import struct

import numpy as np
import pandas as pd

#from modules.helpers import print_and_log

########################
########################

class Arrays:
    """
    The Arrays class has a NumPy array instance for
    every field we ingest from the tracking data.

    The class also contains meta data about how to fill the
    array instances and how much memory they will require.
    """

    def __init__(self, ball, com, player_joints, referee_joints,
                 assistant_joints, select_team_id, select_jersey, n_frames):
        self.count = 0                           # index used to fill the array instances
        self.ball_team_id = -1                   # dummy team_id field for the ball
        self.num_empty = -100                    # dummy NaN field (as NumPy integers cannot be set to NaN)
        self.ball = ball                         # ingest the ball (bool)
        self.com = com                           # ingest the CoM's (bool)
        self.player_joints = player_joints       # ingest the player joints (bool) or specify which joints (list)
        self.referee_joints = referee_joints     # ingest the referee joints (bool) or specify which joints (list)
        self.assistant_joints = assistant_joints # ingest the assistant joints (bool) or specifiy which joints (list)
        self.select_team_id = select_team_id     # None or select a specific team_id (int)
        self.select_jersey = select_jersey       # None or select a specific jersey (int)
        self.set_n_rows_max(n_frames)
        self.create_arrays()


    def set_n_rows_max(self, n_frames):
        """
        Calculates the maximum number of rows required by the array instances.
        This needs to be an overestimation to ensure all the data is ingested
        in the case of dodgy tracking scenarios (e.g. a player is duplicated).
        """

        ### algorithm parameters ###
        safety_factor = 2.0
        n_joints_max = 29
        n_teams_max = 2
        n_teammates_max = 11
        n_referees = 1
        n_assistants = 2

        ### perform the calculation ###
        if self.player_joints == True:
            n_player_joints = n_joints_max
        elif self.player_joints == False:
            n_player_joints = 0
        else:
            n_player_joints = len(self.player_joints)

        if self.referee_joints == True:
            n_referee_joints = n_joints_max
        elif self.referee_joints == False:
            n_referee_joints = 0
        else:
            n_referee_joints = len(self.referee_joints)

        if self.assistant_joints == True:
            n_assistant_joints = n_joints_max
        elif self.assistant_joints == False:
            n_assistant_joints = 0
        else:
            n_assistant_joints = len(self.assistant_joints)

        n_teams = n_teams_max if self.select_team_id is None else 1
        n_teammates = n_teammates_max if self.select_jersey is None else 1
        n_players = n_teams * n_teammates

        rows = 0
        if self.ball == True:
            rows += 1
        if self.com == True:
            rows += (n_players + n_referees + n_assistants)
        rows += n_players * n_player_joints
        rows += n_referees * n_referee_joints
        rows += n_assistants * n_assistant_joints

        self.n_rows_max = int(safety_factor * rows * n_frames)


    def create_arrays(self):
        """
        Creates the NumPy array instances to be filled.
        The filling can then be done efficiently, as all
        the required memory has already been reserved.
        """
        self.he_time = np.zeros(self.n_rows_max, dtype=np.int64)
        self.x = np.zeros(self.n_rows_max, dtype=np.float64)
        self.y = np.zeros(self.n_rows_max, dtype=np.float64)
        self.z = np.zeros(self.n_rows_max, dtype=np.float64)
        self.grd_z = np.zeros(self.n_rows_max, dtype=np.float64)
        self.team_id = np.zeros(self.n_rows_max, dtype=np.int8)
        self.role_id = np.zeros(self.n_rows_max, dtype=np.int8)
        self.track_id = np.zeros(self.n_rows_max, dtype=np.int32)
        self.jersey = np.zeros(self.n_rows_max, dtype=np.int8)
        self.joint_id = np.zeros(self.n_rows_max, dtype=np.int8)
        self.game_active = np.zeros(self.n_rows_max, dtype=np.int8)
        self.is_scrubbed = np.zeros(self.n_rows_max, dtype=np.int8)

########################
########################

def binary_unsigned_array_decode(val):
    """
    Converts a bytes string into a list of 8-bit unsigned integers.
    """

    return list(struct.unpack('B' * len(val), val))

########################
########################

def binary_integer_array_decode(val):
    """
    Converts a bytes string into a list of 32-bit integers.
    """

    return list(struct.unpack('i' * int(len(val) / 4), val))

########################
########################

def binary_float_array_decode(val):
    """
    Converts a bytes string into a list of 32-bit floats.
    """

    return list(struct.unpack('f' * int(len(val) / 4), val))

########################
########################

def binary_double_array_decode(val):
    """
    Converts a bytes string into a list of 64-bit floats.
    """

    return list(struct.unpack('d' * int(len(val) / 8), val))

########################
########################

def read_bson_str(bson_str, decompress=True):
    """
    Decodes a BSON string into form we can work with.
    """

    if decompress == True:
        try:
            bson_data = bson.decode(snappy.decompress(bson_str))
        except:
            bson_data = None

    elif decompress == False:
        try:
            bson_data = bson.decode(bson_str)
        except:
            bson_data = None

    else:
        try:
            bson_data = bson.decode(snappy.decompress(bson_str))
        except:
            try:
                bson_data = bson.decode(bson_str)
            except:
                bson_data = None

    return bson_data

########################
########################

def read_bson_file(bson_file):
    """
    Reads the binary contents of a BSON file.
    """

    with open(bson_file, 'rb') as infile:
        bson_str = infile.read()

    return read_bson_str(bson_str)

########################
########################

def reshape_db_data(data):
    """
    Formats the BSON data from MySQL into the same style as BSON files.
    """

    new_data = {'time': data['time']}
    results = data['results']

    if 'systemFrameData' in results:
        new_data['version'] = 5
        new_data = new_data | {'systemFrameData': results['systemFrameData']['data']}

    if 'ballFrameData' in results:
        new_data = new_data | {'ballFrameData': results['ballFrameData']['data']}
    elif 'ballTracking' in results:
        new_data = new_data | results['ballTracking']['data']

    if 'personFrameData' in results:
        new_data = new_data | {'personFrameData': results['personFrameData']['data']}
    elif 'PersonFrame' in results:
        new_data = new_data | results['PersonFrame']['data'] # NB: includes version, precision, and playerTracking

    return new_data

########################
########################

def setup_joints(p, joints_param, precision, auto_detect_precision=False):
    """
    Determines the three arrays required to perform a
    joint fill for a given person (at a given timestamp).
    """

    ### get all the joint ids belonging to the person and then decode ###
    joint_ids = p.get('jointIds', [])
    if isinstance(joint_ids, bytes):
        if auto_detect_precision == True:
            try:
                joint_ids = binary_integer_array_decode(joint_ids) # NB: try high precision first as it can fail
            except:
                joint_ids = binary_unsigned_array_decode(joint_ids)
        elif precision == 1:
            joint_ids = binary_integer_array_decode(joint_ids)
        else:
            joint_ids = binary_unsigned_array_decode(joint_ids)

    ### get all the joint positions belonging to the person and then decode ###
    joint_pos = p.get('positions', [])
    if isinstance(joint_pos, bytes):
        if auto_detect_precision == True:
            try:
                joint_pos = binary_double_array_decode(joint_pos) # NB: try high precision first as it can fail
            except:
                joint_pos = binary_float_array_decode(joint_pos)
        elif precision == 1:
            joint_pos = binary_double_array_decode(joint_pos)
        else:
            joint_pos = binary_float_array_decode(joint_pos)

    ### determine the person's joints to be ingested ###
    ingest_joint_ids = joint_ids if joints_param == True else joints_param

    return joint_ids, joint_pos, ingest_joint_ids

########################
########################

def process_data(data, arrays, auto_detect_precision=False):
    """
    Processes a frame of BSON data and uses it to fill the
    next elements within the different NumPy array instances.
    Returns 0 if the array instances are successfully filled,
    and 1 if the array instances run out of memory.

    When auto_detect_precision is set to True, the precision
    of the array decoding is determined automatically, rather
    than using the precision value within the BSON data. It
    exists because the precision value was incorrect in the
    contexts table for the 2023-24 season.
    """

    he_time = data.get('time')
    num_empty = arrays.num_empty

    version = data.get('version', 1)
    if version >= 5:
        ball_key = 'ballFrameData'
        player_key = 'personFrameData'
        system_data = data.get('systemFrameData', {})
        precision = system_data.get('precision', 0) # NB: default is 0 from v5 onwards
        game_active = 1 * system_data.get('gameActive', num_empty)
    else:
        ball_key = 'ballTracking'
        player_key = 'playerTracking'
        precision = data.get('precision', 1) # NB: default is 1 before v5
        game_active = 1 * data.get('gameActive', num_empty)

    ### ball fill (even if it is missing) ###
    if arrays.ball == True:
        arrays.count += 1
        c = arrays.count
        if c >= arrays.n_rows_max:
            return 1
        arrays.he_time[c] = he_time
        arrays.team_id[c] = arrays.ball_team_id
        arrays.role_id[c] = num_empty
        arrays.track_id[c] = num_empty
        arrays.jersey[c] = num_empty
        arrays.joint_id[c] = num_empty
        arrays.game_active[c] = game_active

        if ball_key in data:
            bt = data[ball_key]
            r = bt.get('position', (num_empty, num_empty, num_empty))
            if isinstance(r, bytes):
                r = binary_double_array_decode(r) # NB: always 64-bit regardless of system precision
            arrays.x[c] = r[0]
            arrays.y[c] = r[1]
            arrays.z[c] = r[2]
            arrays.grd_z[c] = bt.get('heightOfGround', num_empty)
            arrays.is_scrubbed[c] = bt.get('isFromScrubbing', 0)
        else:
            arrays.x[c] = num_empty
            arrays.y[c] = num_empty
            arrays.z[c] = num_empty
            arrays.grd_z[c] = num_empty
            arrays.is_scrubbed[c] = 0

    ### the remaining logic corresponds to player and referee CoM/joints data ###
    if data.get(player_key, {}).get('people') is not None:

        ### loop through the people ###
        people_list = data[player_key]['people']
        for p in people_list:

            ### only want players and referees ###
            # role_id = 1: outfield player
            # role_id = 2: goalkeeper
            # role_id = 3: referee
            # role_id = 4: assistant referee 1 (+ve X)
            # role_id = 5: assistant referee 2 (-ve X)
            role_id = p.get('roleId', num_empty)
            if role_id not in (1, 2, 3, 4, 5):
                continue

            ### only use the selected team (if specified) ###
            team_id = p.get('teamId', num_empty)
            if arrays.select_team_id is not None and arrays.select_team_id != team_id:
                continue

            ### only use the selected jersey (if specified) ###
            jersey = p.get('jerseyNumber', num_empty)
            try:
                jersey = int(jersey)
            except:
                jersey = num_empty
            if arrays.select_jersey is not None and arrays.select_jersey != jersey:
                continue

            ### get additional player metrics ###
            track_id = p.get('trackId', num_empty)
            is_scrubbed = p.get('isFromScrubbing', 0)

            ### center-of-mass fill ###
            if arrays.com == True:
                arrays.count += 1
                c = arrays.count
                if c >= arrays.n_rows_max:
                    return 1
                r = p.get('centerOfMass', (num_empty, num_empty, num_empty))
                if isinstance(r, bytes):
                    if auto_detect_precision == True:
                        try:
                            r = binary_double_array_decode(r) # NB: try high precision first as it can fail
                        except:
                            r = binary_float_array_decode(r)
                    elif precision == 1:
                        r = binary_double_array_decode(r)
                    else:
                        r = binary_float_array_decode(r)
                arrays.he_time[c] = he_time
                arrays.x[c] = r[0]
                arrays.y[c] = r[1]
                arrays.z[c] = r[2]
                arrays.grd_z[c] = p.get('heightOfGround', num_empty)
                arrays.team_id[c] = team_id
                arrays.role_id[c] = role_id
                arrays.track_id[c] = track_id
                arrays.jersey[c] = jersey
                arrays.joint_id[c] = num_empty
                arrays.game_active[c] = game_active
                arrays.is_scrubbed[c] = is_scrubbed

            ### player joint setup ###
            if arrays.player_joints != False and role_id in (1, 2):
                joint_ids, joint_pos, ingest_joint_ids = setup_joints(
                    p, arrays.player_joints, precision, auto_detect_precision
                )

            ### referee joint setup ###
            elif arrays.referee_joints != False and role_id == 3:
                joint_ids, joint_pos, ingest_joint_ids = setup_joints(
                    p, arrays.referee_joints, precision, auto_detect_precision
                )

            ### assistant joint setup ###
            elif arrays.assistant_joints != False and role_id in (4, 5):
                joint_ids, joint_pos, ingest_joint_ids = setup_joints(
                    p, arrays.assistant_joints, precision, auto_detect_precision
                )

            ### no joint data to be processed ###
            else:
                continue

            ### joint fill ###
            for ingest_joint_id in ingest_joint_ids:
                if ingest_joint_id not in joint_ids:
                    continue
                joint_index = joint_ids.index(ingest_joint_id)
                arrays.count += 1
                c = arrays.count
                if c >= arrays.n_rows_max:
                    return 1
                x, y, z = joint_pos[3 * joint_index: 3 * joint_index + 3]
                arrays.he_time[c] = he_time
                arrays.x[c] = x
                arrays.y[c] = y
                arrays.z[c] = z
                arrays.grd_z[c] = num_empty
                arrays.team_id[c] = team_id
                arrays.role_id[c] = role_id
                arrays.track_id[c] = track_id
                arrays.jersey[c] = jersey
                arrays.joint_id[c] = ingest_joint_id
                arrays.game_active[c] = game_active
                arrays.is_scrubbed[c] = is_scrubbed

    ### the fill was a success ###
    return 0

########################
########################

def format_df(arrays, dupe_warning=False):
    """
    Converts the data within the Arrays object
    into a Pandas DataFrame and then cleans it up.
    """

    ### create the DataFrame object ###
    df = pd.DataFrame({
        'he_time': arrays.he_time,
        'x': arrays.x,
        'y': arrays.y,
        'z': arrays.z,
        'grd_z': arrays.grd_z,
        'team_id': arrays.team_id,
        'role_id': arrays.role_id,
        'track_id': arrays.track_id,
        'jersey': arrays.jersey,
        'joint_id': arrays.joint_id,
        'game_active': arrays.game_active,
        'is_scrubbed': arrays.is_scrubbed
    })

    ### remove the rows that were not filled (the arrays were created with dummy element values of zero) ###
    df = df[df.he_time != 0].copy()

    ### counts the number of instances with duplicated player rows in a frame ###
    if dupe_warning == True:
        df2 = df[
            (df.team_id != arrays.num_empty) &
            (df.role_id != arrays.num_empty) &
            (df.jersey != arrays.num_empty)
        ].copy()
        dupe_count = df2.duplicated(['he_time', 'team_id', 'role_id', 'jersey', 'joint_id']).sum()
       # if dupe_count > 0:
       #     print_and_log(f'WARNING: found {dupe_count} instances with duplicated players in frames', 'warning')

    ### sort data, drop duplicates, and set NaN values ###
    df = df.sort_values(by=['he_time', 'track_id']) # NB: sorting by track_id creates consistency when dropping duplicates
    df = df.drop_duplicates(subset=['he_time', 'team_id', 'role_id', 'jersey', 'joint_id'])
    df = df.replace(arrays.num_empty, np.nan) # NB: this is done here as NumPy integers cannot be set to NaN

    return df

########################
########################

def process_bson_files(read_dir, files, ball=True, com=True, player_joints=False, referee_joints=False,
                       assistant_joints=False, select_team_id=None, select_jersey=None, dupe_warning=False):
    """
    Ingests the BSON files specified by 'read_dir' and 'files'.
    The data is processed according to the configuration of the
    optional arguments, and is returned as a Pandas DataFrame.
    """

    n_frames = len(files)
    arrays = Arrays(ball, com, player_joints, referee_joints, assistant_joints, select_team_id, select_jersey, n_frames)

    for file in files:
        file = os.path.join(read_dir, file)
        data = read_bson_file(file)
        if data is not None:
            if process_data(data, arrays) == 1:
               # print_and_log('WARNING: dataframe ran out of allocated memory whilst filling', 'warning')
                break

    return format_df(arrays, dupe_warning)

########################
########################

def process_bson_db(bsons, ball=True, com=True, player_joints=False, referee_joints=False,
                    assistant_joints=False, select_team_id=None, select_jersey=None, dupe_warning=False):
    """
    Ingests the BSON data from the 'bsons' object (which is the
    context column of the *_contexts MySQL table as a Pandas Series).
    The data is processed according to the configuration of the
    optional arguments, and is returned as a Pandas DataFrame.
    """

    n_frames = len(bsons)
    arrays = Arrays(ball, com, player_joints, referee_joints, assistant_joints, select_team_id, select_jersey, n_frames)

    for bson in bsons:
        data = read_bson_str(bson)
        if data is not None:
            data = reshape_db_data(data)
            # TODO: stop using auto_detect_precision once confident it is not needed
            if process_data(data, arrays, auto_detect_precision=True) == 1:
                #print_and_log('WARNING: dataframe ran out of allocated memory whilst filling', 'warning')
                break

    return format_df(arrays, dupe_warning)

########################
########################