import json
import os
import re
import urllib
import urllib.request
import time

from bs4 import BeautifulSoup
import gspread
import gspread_dataframe as gd
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd


CONFIG_FILE = os.path.join(os.path.dirname(__file__), "gspread_config.json")
ROCHADE_URL = "https://rochadeeuropa.com/lichess-turniere-beendet/"
BUNDESLIGA_REGEXP = r"|".join(["(1. DE-Quarantäne Team Battle)",
                               "([0-9]+\. ?DE[ -]Quarantäne Teams 1-10)",
                               "(5. Quarantäne-Liga Teams 1-10)",
                               "([0-9]+\. ?Quarantäne-Bundesliga ?$)",
                               "([0-9]+\. ?Quarantäne-Welt-Bundesliga ?$)",
                               ])
SHEETNAME = "Ewige Quarantäne-Bundesligatabelle"
TEAM_NAME_DICT = {}  # store team names in global variable in order to minimize api calls


def get_bundesliga_tournaments():
    """
    scrape rochadeeuropa.com in order to find lichess quarantaine bundesliga matches.
    Rochade URL and regex to determine which tournament was actually a bundesliga tournaments are
    taken from configurable global variables
    """
    # scrape rochade finished lichess tournaments
    response = urllib.request.urlopen(ROCHADE_URL)
    html = response.read()
    soup = BeautifulSoup(html, 'html.parser')

    # parse table
    data = []
    table = soup.find('table', attrs={'class':'tablepress tablepress-id-3'})
    table_body = table.find('tbody')

    rows = table_body.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        data.append([ele.text.strip() for ele in cols])
    # filter for bundesliga
    buli_tournaments = [el for el in data if re.match(BUNDESLIGA_REGEXP, el[1])]
    return buli_tournaments


def get_individual_results(tournament_id):
    """
    For individual results for a given tournament we use lichess API
    """
    api_url = f"https://lichess.org/api/tournament/{tournament_id}/results"
    api_response = urllib.request.urlopen(api_url)
    player_results = api_response.read()
    return pd.DataFrame([json.loads(pl) for pl in player_results.splitlines()])

def call_api(api_url):
    """
    call api or wait a minute and then call api.
    This is in order not to get a too many requests error.
    This way lichess keeps its API responsive
    """
    try:
        return urllib.request.urlopen(api_url)
    except urllib.error.HTTPError:
        print("waiting one minute for API to be responsive again")
        time.sleep(61)
        return call_api(api_url)

def get_team_name(team_id):
    try:
        return TEAM_NAME_DICT[team_id]
    except KeyError:
        api_url = f"https://lichess.org/api/team/{team_id}"
        api_response = call_api(api_url)
        team_name = json.loads(api_response.read())["name"]
        TEAM_NAME_DICT[team_id] = team_name
        return team_name


def get_team_results(tournament_url):
    """
    Use API to get team results
    """
    
    tournament_id = tournament_url.split("/")[-1]
    api_url = f"https://lichess.org/api/tournament/{tournament_id}/teams"
    api_response = call_api(api_url)
    team_results = json.loads(api_response.read())["teams"]
    relevant_keys = ["rank", "id", "score"]
    team_results = [[team_result[col] for col in relevant_keys] for team_result in team_results]
    teams_df = pd.DataFrame(team_results, columns=relevant_keys)
    teams_df["Team"] = teams_df["id"].map(get_team_name)
    return teams_df


def build_individual_alltime(individual_results: pd.DataFrame) -> pd.DataFrame:
    """
    aggregate individual results to alltime-results table
    """
    individual_results["count"] = 1
    individual_results["champion"] = (individual_results["rank"] == 1).astype(int)
    agg_dict = {"score": "sum", "count": "count", "champion": "sum", "performance": "mean", "rank": "mean", }
    all_time_indiv = individual_results.groupby("username", as_index=False).agg(agg_dict)\
        .sort_values("score", ascending=False)
    all_time_indiv.columns = ["Name", "Gesamtpunkte", "Teilnahmen", "Turniersiege",
                              "Durchschnittsperformance", "Durchschnittsplatzierung"]
    all_time_indiv.index = range(1, len(all_time_indiv) + 1)
    all_time_indiv["Durchschnittsscore"] = all_time_indiv["Gesamtpunkte"] / all_time_indiv["Teilnahmen"]
    return all_time_indiv

def build_teams_alltime(team_results: pd.DataFrame) -> pd.DataFrame:
    """
    aggregate team results to alltime-results table
    """
    team_results["count"] = 1
    team_results["champion"] = (team_results["rank"] == 1).astype(int)
    agg_dict = {"score": "sum", "count": "count", "champion": "sum", "rank": "mean"}
    all_time_teams = team_results.groupby("Team", as_index=False).agg(agg_dict).sort_values("score", ascending=False)
    all_time_teams.columns = ["Team", "Gesamtpunkte", "Teilnahmen", "Meisterschaften", "Durchschnittsplatzierung"]
    all_time_teams.index = range(1, len(all_time_teams) + 1)
    all_time_teams = all_time_teams.reset_index().rename(columns={"index": "Rang"})
    return all_time_teams


def connect_to_spreadsheet():
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']

    credentials = ServiceAccountCredentials.from_json_keyfile_name(CONFIG_FILE, scope)

    gc = gspread.authorize(credentials)
    return gc


def write_to_spreadsheet(df):
    sheet_connection = connect_to_spreadsheet()
    ws = sheet_connection.open(SHEETNAME).worksheet("Sheet1")
    gd.set_with_dataframe(ws, df)


def run():
    team_df = pd.DataFrame()
    individual_df = pd.DataFrame()

    buli_tournaments = get_bundesliga_tournaments()
    for tournament in buli_tournaments:
        print(f"Downloading data of tournament {tournament[1]} on {tournament[0]}")
        team_df = team_df.append(get_team_results(tournament[4]))
        # for now only export teams df
        # individual_df = individual_df.append(get_individual_results(tournament[4].split("/")[-1]))

    all_time_teams = build_teams_alltime(team_df)
    write_to_spreadsheet(all_time_teams.round({"Durchschnittsplatzierung": 1}))


if __name__ == "__main__":
    run()
