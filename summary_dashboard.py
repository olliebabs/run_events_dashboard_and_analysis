import pandas as pd
import streamlit as st
import json
import os
import time
import sys
import subprocess
import altair as alt

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
    st.title(f"{team_0_name} vs {team_1_name} run events dashboard ")
    st.subheader('Headline stats:')
    col1, col2, col3 = st.columns([1,1,2])
    col1.metric(label='total run evnts: ', value=total_runs)
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
    click_listener_team_0 = alt.selection_point(fields=['player_jerseyNumber'], empty='none', name='team_0_select')
    click_listener_team_1 = alt.selection_point(fields=['player_jerseyNumber'], empty='none', name='team_1_select')

    team_player_runs_listener = alt.selection_point(fields=['player_jerseyNumber'], empty='none', name='selected_jersey')

    click_listeners = [click_listener_team_0, click_listener_team_1]
    selected_list = []

    # Now create the line graphs for each of the teams:
    for color, team_name, team_id, col, click_listener in zip(run_bar_colours, team_names, team_ids, cols, click_listeners):
        with col:
            st.markdown(f"Team {team_name}")
            bar_data = runs_by_team_data[runs_by_team_data['player_teamId'] == team_id]

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
                    .add_params(team_player_runs_listener)
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

    for id in team_ids:
        state=st.session_state.get(f"chart_team_{id}", {}).get('selection', {})

        if 'selected_jersey' in state and state['selected_jersey']:
            clicked_jersey = state['selected_jersey'][0]['player_jerseyNumber']
            clicked_team = team_id
            break

            

    st.text(f"Test\nClicked team = {clicked_team} and jersey = {clicked_jersey}")
    

    if clicked_team is not None and clicked_jersey is not None:
        st.text(f"Test\nClicked team = {clicked_team} and jersey = {clicked_jersey}")
        player_runs = total_run_events_df[(total_run_events_df['player_teamId'] == clicked_team) & 
                                          (total_run_events_df['player_jerseyNumber'] == clicked_jersey)].copy()

        # Make sure that there is a sequence of these player runs:
        player_runs['run_seq'] = range(1, len(player_runs) + 1)
        #player_runs['run_seq'] = 'Run ' + player_runs['run_seq'].astype(str)

        # Now render the chart of these runs:
        bar_color = 'blue' if clicked_team == 0 else 'orange'

        # base plot to then add the two plots on top of each other:
        base_chart = alt.Chart(player_runs).encode(
            x=alt.X('run_seq:N', title='Run seq', sort=None)
        )

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
        )


        st.altair_chart(combined_chart, use_container_width=True)
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
