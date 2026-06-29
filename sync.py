import re
sf='app/scrapers/espn_requests_scraper.py'
t=open(sf).read()
t=re.sub(r'"stadium_name"\s*:\s*venue\.get\("fullName"\)','"stadium_name":STADIUMS.get(int(team.get("id")), {}).get("name")',t)
open(sf,'w').write(t)

from app.database import engine,Base,SessionLocal
from app.scrapers.factory import get_scraper

from app.scrapers.news_scraper import fetch_news
from app.scrapers.sync_all_stats import sync_all_stats

from app import models
Base.metadata.create_all(bind=engine)
db=SessionLocal()
scraper=get_scraper("espn")
for m in [models.Standing,models.Match,models.Player,models.Week,models.Team,models.Stadium,models.Season]:
    db.query(m).delete()
db.commit()
smap={}
for s in scraper.get_stadiums():
    st=models.Stadium(**s);db.add(st);db.flush();smap[s["name"]]=st.id
tmap={}
for t in scraper.get_teams():
    tm=models.Team(id=t["id"],name=t["name"],short_name=t.get("short_name"),city=t.get("city"),colors=t.get("colors"),founded=t.get("founded"),stadium_id=smap.get(t.get("stadium_name")));db.add(tm);db.flush();tmap[t["name"]]=tm.id;tmap[t["id"]]=tm.id
for p in scraper.get_players():
    db.add(models.Player(id=p["id"],name=p["name"],position=p.get("position"),number=p.get("number"),nationality=p.get("nationality"),birth_date=p.get("birth_date"),photo_url=p.get("photo_url"),team_id=tmap.get(p.get("team_name"))))
sn=models.Season(name="2025",year=2025,tournament_type="Liga MX");db.add(sn);db.flush()
matches=scraper.get_matches()
team_matches={}
for i,m in enumerate(matches):
    if not m.get("match_date"): continue
    hid=m.get("home_team_id");aid=m.get("away_team_id")
    if hid: team_matches.setdefault(hid,[]).append((m["match_date"],i))
    if aid: team_matches.setdefault(aid,[]).append((m["match_date"],i))
for team_id,lst in team_matches.items():
    lst.sort(key=lambda x:x[0])
    for j,(d,i) in enumerate(lst):
        if matches[i].get("home_team_id")==team_id:
            matches[i]["week"]=j+1

# Validación de jornadas
for team_id,lst in team_matches.items():
    seen=sorted({matches[i]["week"] for d,i in lst if matches[i].get("week")})
    expected=list(range(1,len(seen)+1))
    if seen!=expected:
        print(f"⚠️ Jornadas mal para equipo {team_id}: {seen}")

for m in matches:
    hid=tmap.get(m.get("home_team_id")) or tmap.get(m.get("home_team"));aid=tmap.get(m.get("away_team_id")) or tmap.get(m.get("away_team"))
    if hid and aid:db.add(models.Match(season_id=sn.id,home_team_id=hid,away_team_id=aid,match_date=m.get("match_date"),home_score=m.get("home_score"),away_score=m.get("away_score"),status=m.get("status","scheduled"),week_number=m.get("week")))
for s in scraper.get_standings():
    db.add(models.Standing(season_id=sn.id,team_id=tmap.get(s.get("team_name")),position=s["position"],played=s["played"],won=s["won"],drawn=s["drawn"],lost=s["lost"],goals_for=s["goals_for"],goals_against=s["goals_against"],goal_difference=s["goals_for"]-s["goals_against"],points=s["points"]))
sync_all_stats(db, matches, scraper, tmap, "2025")

print("OK estadios",len(smap),"equipos",len(tmap),"jugadores",len(db.query(models.Player).all()),"partidos",len(db.query(models.Match).all()))
# News sync
print("Sincronizando noticias...")
db.query(models.News).delete()
for n in fetch_news(limit=50):
    db.add(models.News(**n))
db.commit()
print("OK noticias", len(db.query(models.News).all()))
db.close()
