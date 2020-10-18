# All-Time Standings in Lichess Quarantaine Bundesliga

This repo contains a python code to generate and update the all-time standings in the Lichess Quarantaine Bundesliga.  
There is also a jupyter notebook for more experimental development.

## Output:
### All-Time Team Standings of Lichess Quarantaine Bundesliga
The all-time team standings are written to a google spreadsheet and published on www.rochadeeuropa.com
![Teams Table](resources/alltime_table_teams.png)
### All-Time Individual Standings of Lichess Quarantaine Bundesliga
The all-time individual table is not published at the moment. 
The code for generating and maintaining it however is already there.
![Players Table](resources/alltime_table_players.png)
## Prerequisites:
### Necessary Python Installation:
- Python 3.7, preferably anaconda
- packages in `requirements.txt` to be installed via `pip install -r requirements.txt`

## How to run:
1. Fill the config template with you google sheet connection and rename the file to `gspread_config.json`  
2. Execute script by calling `python update_all_time_table.py`
