import requests

from pbpstats import HEADERS, REQUEST_TIMEOUT
from pbpstats.resources.enhanced_pbp.stats_nba.enhanced_pbp_item import StatsEnhancedPbpItem
from pbpstats.resources.enhanced_pbp.start_of_period import StartOfPeriod, InvalidNumberOfStartersException


class StatsStartOfPeriod(StartOfPeriod, StatsEnhancedPbpItem):
    def __init__(self, *args):
        super().__init__(*args)

    def get_period_starters(self):
        try:
            return self._get_period_starters_from_period_events()
        except InvalidNumberOfStartersException:
            return self._get_starters_from_boxscore_request()

    def _get_starters_from_boxscore_request(self):
        """
        makes request to boxscore url for time from period start to first event to get period starters
        """
        base_url = f'https://stats.{self.league_url_part}.com/stats/boxscoretraditionalv2'
        event = self
        while event is not None and event.seconds_remaining == self.seconds_remaining:
            event = event.next_event
        seconds_to_first_event = self.seconds_remaining - event.seconds_remaining

        if self.period == 1:
            start_range = 0
        elif self.period <= 4:
            start_range = int(7200 * (self.period - 1))
        else:
            start_range = int(28800 + 3000 * (self.period - 5))
        end_range = int(start_range + seconds_to_first_event * 10)
        params = {
            'GameId': self.game_id,
            'StartPeriod': 0,
            'EndPeriod': 0,
            'RangeType': 2,
            'StartRange': start_range,
            'EndRange': end_range
        }
        starters_by_team = {}
        response = requests.get(base_url, params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            response_json = response.json()
        else:
            response.raise_for_status()

        headers = response_json['resultSets'][0]['headers']
        rows = response_json['resultSets'][0]['rowSet']
        players = [dict(zip(headers, row)) for row in rows]
        starters = sorted(players, key=lambda k: int(k['MIN'].split(':')[1]), reverse=True)

        for starter in starters[0:10]:
            team_id = starter['TEAM_ID']
            player_id = starter['PLAYER_ID']
            if team_id not in starters_by_team.keys():
                starters_by_team[team_id] = []
            starters_by_team[team_id].append(player_id)

        for team_id, starters in starters_by_team.items():
            if len(starters) != 5:
                raise InvalidNumberOfStartersException(f'GameId: {self.game_id}, Period: {self.period}, TeamId: {team_id}, Players: {starters}')

        return starters_by_team

    @property
    def league_url_part(self):
        if self.game_id[0:2] == '00':
            return 'nba'
        elif self.game_id[0:2] == '20':
            return 'gleague.nba'
        elif self.game_id[0:2] == '10':
            return 'wnba'
