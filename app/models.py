from pydantic import BaseModel


class ChampionSummary(BaseModel):
    token_id: int
    name: str
    class_: str  # 'class' is reserved in Python
    base_win_rate: float
    games: int
    avg_score: float
    favorable: int
    unfavorable: int

    class Config:
        populate_by_name = True

    def model_dump(self, **kwargs):
        d = super().model_dump(**kwargs)
        # Rename class_ back to class for JSON output
        d['class'] = d.pop('class_')
        return d


class Supporter(BaseModel):
    name: str
    class_: str
    career_elims: float
    career_deps: float

    class Config:
        populate_by_name = True

    def model_dump(self, **kwargs):
        d = super().model_dump(**kwargs)
        d['class'] = d.pop('class_')
        return d


class Matchup(BaseModel):
    date: str
    opponent: str
    opponent_class: str
    opponent_win_rate: float
    my_supporters: list[dict]
    opp_supporters: list[dict]
    my_avg_elims: float
    my_avg_deps: float
    opp_avg_elims: float
    opp_avg_deps: float
    score: float
    edge: str


class Champion(BaseModel):
    token_id: int
    name: str
    class_: str
    base_win_rate: float

    class Config:
        populate_by_name = True

    def model_dump(self, **kwargs):
        d = super().model_dump(**kwargs)
        d['class'] = d.pop('class_')
        return d


class ChampionMatchups(BaseModel):
    champion: dict
    matchups: list[Matchup]
