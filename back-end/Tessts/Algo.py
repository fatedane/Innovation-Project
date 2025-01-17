from flask import jsonify
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import json
from pprint import pprint
import csv
import json


def incoming_games():
    matchs = pd.read_csv("matches_csv\\events.csv")
    tomorrow = datetime.today().date() 
    incoming_match_ids = []

    for index, row in matchs.iterrows():
        event_date = datetime.strptime(row['event_date'], '%Y-%m-%d').date()
        if event_date >= tomorrow:
            incoming_match_ids.append(row['event_key'])

    return incoming_match_ids

def Algo(match_id):

    matchs = pd.read_csv("matches_csv\\events.csv")
    odds_data = pd.read_csv("odds_csv\\odds.csv")
    # Trouver le match correspondant à l'ID donné
    match = matchs[matchs['event_key'] == match_id].iloc[0]

    # Extraire les informations des joueurs et leur ID
    player1 = match['event_first_player']
    player2 = match['event_second_player']
    player1_id = match['first_player_key']
    player2_id = match['second_player_key']

    # Calculer le nombre total de matches disputés par chaque joueur
    total_matches_player1 = matchs[(matchs['event_first_player'] == player1) | (matchs['event_second_player'] == player1)].shape[0]
    total_matches_player2 = matchs[(matchs['event_first_player'] == player2) | (matchs['event_second_player'] == player2)].shape[0]

    # Calculer le nombre de victoires de chaque joueur
    wins_player1 = matchs[(matchs['event_winner'] == 'First Player') & ((matchs['event_first_player'] == player1) | (matchs['event_second_player'] == player1))].shape[0]
    wins_player2 = matchs[(matchs['event_winner'] == 'Second Player') & ((matchs['event_first_player'] == player2) | (matchs['event_second_player'] == player2))].shape[0]

    # Calculer le pourcentage de victoire de chaque joueur
    win_percentage_player1 = (wins_player1 / total_matches_player1) * 100
    win_percentage_player2 = (wins_player2 / total_matches_player2) * 100

    return (win_percentage_player1, player1_id), (win_percentage_player2, player2_id)

def RESPONSE(match_ids):

    matchs = pd.read_csv("matches_csv\\events.csv")
    odds_data = pd.read_csv("odds_csv\\odds.csv")
    # Créer une liste pour stocker les informations de chaque match
    matches_list = []

    for match_id in match_ids:
        # Vérifier si l'ID du match existe dans les données des cotes
        if match_id not in odds_data['id_match'].values:
            continue

        # Filtrer les lignes correspondant au match donné dans les données principales
        match_info = matchs[matchs['event_key'] == match_id].iloc[0]

        # Calculer les pourcentages de victoire des joueurs pour le match donné
        (win_percentage_player1, player1_id), (win_percentage_player2, player2_id) = Algo(match_id)

        # Extraire les noms des joueurs à partir des données principales
        player1_name = match_info['event_first_player']
        player2_name = match_info['event_second_player']
        player1_logo = match_info['event_first_player_logo']
        player2_logo = match_info['event_second_player_logo']

        # Filtrer les lignes correspondant au match donné dans les données des cotes
        match_odds = odds_data[odds_data['id_match'] == match_id]

        # Récupérer le nom du tournoi à partir du fichier principal
        tournament_name = match_info['tournament_name']

        # Trouver les cotes maximales pour chaque joueur
        if not match_odds['cote_Home'].empty:
            max_odd_player1 = match_odds['cote_Home'].max()
            bookmaker_odd_player1 = match_odds.loc[match_odds['cote_Home'].idxmax()]['bookmaker']
        else:
            max_odd_player1 = None
            bookmaker_odd_player1 = None

        if not match_odds['cote_Away'].empty:
            max_odd_player2 = match_odds['cote_Away'].max()
            bookmaker_odd_player2 = match_odds.loc[match_odds['cote_Away'].idxmax()]['bookmaker']
        else:
            max_odd_player2 = None
            bookmaker_odd_player2 = None

        # Ajouter les informations du match à la liste
        match_info = {
            "event_id": match_id,
            "tournament_name": tournament_name,
            "player_1": player1_name,
            "player_1_logo": player1_logo,
            "player_2": player2_name,
            "player_2_logo": player2_logo,
            "win_percentage_player_1": float(win_percentage_player1),
            "win_percentage_player_2": float(win_percentage_player2),
            "odd_player_1": float(max_odd_player1) if max_odd_player1 is not None else None,
            "bookmaker_odd_player_1": bookmaker_odd_player1,
            "odd_player_2": float(max_odd_player2) if max_odd_player2 is not None else None,
            "bookmaker_odd_player_2": bookmaker_odd_player2
        }
        matches_list.append(match_info)

    # Créer le dictionnaire final
    response_dict = {"matches": matches_list}

    # Convertir le dictionnaire en format JSON
    json_response = json.dumps(response_dict, indent=2)

    # pprint(response_dict)
    return response_dict

def RESPONSE2(response):
    match_infos = response["matches"]
    # Calculer le meilleur ratio pour chaque match
    for match_info in match_infos:
        ratio_player_1 = match_info["win_percentage_player_1"] * match_info.get("odd_player_1", 0)
        ratio_player_2 = match_info["win_percentage_player_2"] * match_info.get("odd_player_2", 0)
        match_info["meilleur_ratio"] = max(ratio_player_1, ratio_player_2)
    
    # Trier les matchs par meilleur ratio de manière décroissante
    match_infos.sort(key=lambda x: x["meilleur_ratio"], reverse=True)
    
    # Ajouter le rang à chaque match et garder les trois premiers
    for i, match_info in enumerate(match_infos[:3]):
        match_info["rang"] = i + 1
    
    return match_infos

def algo_répartition(match_infos, repartition):
    # Calculer la note pour chaque match
    for match_info in match_infos:
        note_player_1 = match_info.get("odd_player_1", 1) * match_info["win_percentage_player_1"]
        note_player_2 = match_info.get("odd_player_2", 1) * match_info["win_percentage_player_2"]
        match_info["note"] = max(note_player_1, note_player_2)
    
    # Trier les matchs par note de manière décroissante
    match_infos.sort(key=lambda x: x["note"], reverse=True)

    for i, match_info in enumerate(match_infos[:3]):
        match_info["repartition"] = repartition[i]

    print(match_infos)
    return match_infos


repartition = [["50", "33", "25"], ["25", "33", "25"], ["25", "33", "50"]]
data = algo_répartition(RESPONSE2(RESPONSE(incoming_games())), repartition)

# print(data)
# print(resultat)
