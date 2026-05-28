import pandas as pd
import streamlit as st
import json
import os
import time
import sys
import subprocess
import altair as alt


# Fucntion to plot the duration and max speeds of a selected player:
def create_ind_runs_chart(player_runs, clicked_team, clicked_jersey):
    
    # Make sure that there is a sequence of these player runs:
    
    #player_runs['run_seq'] = 'Run ' + player_runs['run_seq'].astype(str)

    # Now render the chart of these runs:
    bar_color = 'blue' if clicked_team == 0 else 'orange'

    # base plot to then add the two plots on top of each other:
    base_chart = alt.Chart(player_runs).encode(
        x=alt.X('run_seq:N', title='Run seq', sort=None)
    )

    # Define the listener for the chart:
    ind_pl_runs_chart_listner = alt.selection_point(
        fields=['run_seq'], 
        empty='none', 
        name='ind_pl_runs_chart_listner',
        clear=False)

    # Bar Chart:
    duration_bar_chart = base_chart.mark_bar(color=bar_color, opacity=0.6).encode(
        y=alt.Y("properties_totalRunTime:Q", title="Duration (secs)"),
        tooltip=[
            alt.Tooltip('run_seq:N', title='run number'),
            alt.Tooltip('properties_totalRunTime:Q', title='run time (secs)')
        ],
        
    )
    

    # Line Graph:
    max_speed_line = base_chart.mark_line(
        color='red',
        opacity=0.6
    ).encode(
        y=alt.Y('properties_maximumSpeed:Q', title='Max Speed (m/s)'),
        tooltip=[
            alt.Tooltip('run_seq:N', title='Run event number'),
            alt.Tooltip('properties_maximumSpeed:Q', title='Max speed (m/s)')
        ],
    )

    combined_chart = (
        alt.layer(duration_bar_chart, max_speed_line)
        .resolve_scale(y='independent')
        .properties(height=260)
        .add_params(ind_pl_runs_chart_listner)
    )

    return combined_chart
    






def dashboard_config(total_run_events_df, game_name):
    team_0_name = game_name.split('_')[4]
    team_1_name = game_name.split('_')[5]

    # Need to prepare headline stats too.
    total_runs = len(total_run_events_df)
    max_speed = total_run_events_df.properties_maximumSpeed.max()

    total_run_events_team_0_df = total_run_events_df[total_run_events_df['player_teamId'] == 0]
    total_run_events_team_1_df = total_run_events_df[total_run_events_df['player_teamId'] == 1]

    team_0_runs = len(total_run_events_team_0_df)
    team_0_distance = (total_run_events_team_0_df['properties_totalRunTime'] * total_run_events_team_0_df['properties_averageSpeed']).sum()
    team_1_distance = (total_run_events_team_1_df['properties_totalRunTime'] * total_run_events_team_1_df['properties_averageSpeed']).sum()

    st.set_page_config(layout='wide')
    st.title(f"{team_0_name} vs {team_1_name} run events dashboard (currently 1st H only)")
    st.subheader('Headline stats:')
    col1, col2, col3 = st.columns([1,1,2])
    col1.metric(label='total run events: ', value=total_runs)
    col2.metric(label='max speed recorded: ', value=f"{str(round(max_speed,2))} ms^-2")
    col3.metric(label=f"{team_0_name}:{team_1_name} runs breakdown", value=f"""{str(team_0_runs)} ({str(round(team_0_distance/1000,2))} k) | 
                {str(total_runs - team_0_runs)} ({str(round(team_1_distance/1000,2) )} k)""")
    
    st.markdown('---')
    st.subheader('Runs breakdown by players:')
    team_0_col_0, team_1_col_1 = st.columns(2)

    runs_by_team_data = (
        total_run_events_df.groupby(['player_teamId', 'player_jerseyNumber'])
        .size()
        .reset_index(name='total_runs')
    )

    run_bar_colours = ['blue', 'orange']
    team_names = [team_0_name, team_1_name]
    team_ids = [0,1]
    cols = [team_0_col_0, team_1_col_1]

    # Clickers for the leadership board:
    #click_listener_team_0 = alt.selection_point(fields=['player_jerseyNumber'], empty='none', name='team_0_select')
    #click_listener_team_1 = alt.selection_point(fields=['player_jerseyNumber'], empty='none', name='team_1_select')

    #team_player_runs_listener = alt.selection_point(fields=['player_jerseyNumber'], empty='none', name='selected_jersey')

    #click_listeners = [click_listener_team_0, click_listener_team_1]
    selected_list = []

    # Now create the line graphs for each of the teams:
    #for color, team_name, team_id, col, click_listener in zip(run_bar_colours, team_names, team_ids, cols, click_listeners):
    for color, team_name, team_id, col in zip(run_bar_colours, team_names, team_ids, cols):
        with col:
            st.markdown(f"Team {team_name}")
            bar_data = runs_by_team_data[runs_by_team_data['player_teamId'] == team_id]

            # Define listsner and bind to chart on the fly - but give the same name:
            run_event_leaderboard_listener = alt.selection_point(fields=['player_teamId', 'player_jerseyNumber'], empty='none', name='run_event_leaderboard_listener', clear=False)

            if not bar_data.empty:
                # Build the chart:
                runs_leadership_chart = (
                    alt.Chart(bar_data)
                    .mark_bar(color=color)
                    .encode(
                        x=alt.X(
                            'total_runs:Q', title="Number of runs"
                        ),
                        y=alt.Y(
                            'player_jerseyNumber:N',
                            title="Player Jersey",
                            sort='-x',
                            axis=alt.Axis(
                                labelOverlap=False,
                                tickMinStep=1
                            )
                        ),
                        tooltip=[
                            alt.Tooltip(
                                'player_jerseyNumber:N', title= 'Jersey Number'
                            ),
                            alt.Tooltip(
                                'total_runs:Q',title='Total runs and sprints'
                            )
                        ],
                    )
                    #.add_params(click_listener)
                    .add_params(run_event_leaderboard_listener)
                    .properties(height=300)
                )

                selected_list.append(
                    st.altair_chart(
                        altair_chart=runs_leadership_chart, use_container_width=True, on_select='rerun', key=f"chart_team_{team_id}"
                    )
                )
            else:
                st.info("No run events from team !")

    st.markdown('---')
    st.subheader('Breakdown of selected plaeyers runs:')

    # initioalise variables:
    clicked_team = None
    clicked_jersey = None


   # callback listeners from the lederbard charts:
    team_0_leadershboard_selector = (
        st.session_state.get("chart_team_0", {})
        .get("selection", {})
        .get("run_event_leaderboard_listener")
    )
    team_1_leadershboard_selector = (
        st.session_state.get("chart_team_1", {})
        .get("selection", {})
        .get("run_event_leaderboard_listener")
    )

    # Establish the selected jersey numbers and define as None if not one selcted:
    team_0_leadershboard_selected_jersey = team_0_leadershboard_selector[0]["player_jerseyNumber"] if team_0_leadershboard_selector else None
    team_1_leadershboard_selected_jersey = team_1_leadershboard_selector[0]["player_jerseyNumber"] if team_1_leadershboard_selector else None

    # Initialize our short-term change detectors if they don't exist
    if "prev_team_0_jersey" not in st.session_state:
        st.session_state["prev_team_0_jersey"] = None
    if "prev_team_1_jersey" not in st.session_state:
        st.session_state["prev_team_1_jersey"] = None
    if "locked_team" not in st.session_state:
        st.session_state["locked_team"] = None
    if "locked_jersey" not in st.session_state:
        st.session_state["locked_jersey"] = None

    # Check if jersey number for team 0 has changed or not:
    if team_0_leadershboard_selected_jersey is not None and team_0_leadershboard_selected_jersey != st.session_state["prev_team_0_jersey"]:
        st.session_state["locked_team"] = 0
        st.session_state["locked_jersey"] = team_0_leadershboard_selected_jersey

    # Check if team 1 jersey is different from the last time:
    elif team_1_leadershboard_selected_jersey is not None and team_1_leadershboard_selected_jersey != st.session_state["prev_team_1_jersey"]:
        st.session_state["locked_team"] = 1
        st.session_state["locked_jersey"] = team_1_leadershboard_selected_jersey


    # 3. Save the current values into memory for the NEXT frame comparison
    st.session_state["prev_team_0_jersey"] = team_0_leadershboard_selected_jersey
    st.session_state["prev_team_1_jersey"] = team_1_leadershboard_selected_jersey

    # 4. Use these locked variables as the absolute ground truth for your charts
    clicked_team = st.session_state["locked_team"]
    clicked_jersey = st.session_state["locked_jersey"]
            

    st.text(f"Test\nClicked team = {clicked_team} and jersey = {clicked_jersey}")
    

    if clicked_team is not None and clicked_jersey is not None:
        #st.text(f"Test\nClicked team = {clicked_team} and jersey = {clicked_jersey}")
        player_runs = total_run_events_df[(total_run_events_df['player_teamId'] == clicked_team) & 
                                          (total_run_events_df['player_jerseyNumber'] == clicked_jersey)].copy()
        
        player_runs['run_seq'] = range(1, len(player_runs) + 1)

        # Individual player runs bar chart with max speed superimposed:
        ind_runs_chart = create_ind_runs_chart(player_runs, clicked_team, clicked_jersey)

        st.altair_chart(ind_runs_chart, use_container_width=True, on_select='rerun', key=f"ind_runs_chart")

        # Then lets add a new break and begin the run event visualiaztion:
        st.markdown('---')
        
        selected_run_id = None
        
        # Load in the listener:
        ind_run_listener = st.session_state.get('ind_runs_chart', {}).get('selection', {}).get('ind_pl_runs_chart_listner')


        if ind_run_listener:
         
            selected_run_id = ind_run_listener[0]['run_seq']

        
            st.text(f"Run Seq number = {str(selected_run_id)}")

            # Start and end time_stamps from selected run event
            selected_run_event = player_runs[player_runs['run_seq'] == selected_run_id].iloc[0]
            start_timestamp = selected_run_event['start_timestamp']
            end_timestamp = selected_run_event['end_timestamp']

            st.text(f"""Player team = {clicked_team}\nPlayer jersey = {clicked_jersey}\n
                    Start time = {start_timestamp}\nEnd time = {end_timestamp}""")



    else:
        st.info("Please select a player !")





if __name__ == '__main__':

    # Load in game name from main script call:
    try:
        game_name = sys.argv[1]
    except IndexError:
        print(f"game name not sent to executable properly.")

    print(f"Game name = {game_name}")
    #Load in main run events df into workspace:
    try:
        run_events_df = pd.read_parquet(f"run_events_{game_name}.parquet")
    except FileNotFoundError:
        print(f"Cannot find the run evenst file!")

    if not run_events_df.empty:
        print("\nFound run events, attempting to render dashboard...")
        dashboard_config(run_events_df, game_name)
