# Balance test bot for Red Planet Outpost: plays 200 missions per strategy and reports survival and science.
# AI disclosure: written with AI assistance from Claude (Anthropic), reviewed and run by the Orbit Cousins team.
import json, sys
from playwright.sync_api import sync_playwright
SMART = "(a,S)=>{const lv=S.forecastFor===S.sol?S.weather[S.sol].level:0; return lv>=2?{life:3,green:2,shield:3,comms:1,science:0}:{life:3,green:2,shield:1,comms:1,science:2}}"
# name: (allocation strategy, cover the habitat with Mars soil when asked?)
STRATS = {
 "naive_no_shield": ("a=>({life:3,green:2,shield:0,comms:1,science:3})", False),
 "shield1_always":  ("a=>({life:3,green:2,shield:1,comms:1,science:2})", False),
 "smart_no_cover":  (SMART, False),
 "smart_cover":     (SMART, True),
 "shield2_always":  ("a=>({life:3,green:2,shield:2,comms:1,science:1})", False),
}
js = """
([strat, cover, seed]) => {
  const f = eval(strat); const R = window.RPO; R.newGame({seed}); let S=R.S; let guard=0;
  while(!S.over && guard++<60){
    if(S.pendingCard && S.pendingCard.id==="cover"){ R.chooseCard(cover?0:1); }
    else if(S.pendingCard){ R.chooseCard(S.pendingCard.choices.length>1 && (!S.pendingCard.choices[0].need || S.pendingCard.choices[0].need()) ? 0 : 1); }
    let al = f(S.alloc, S);
    S.alloc = {life:0,green:0,shield:0,comms:0,science:0};
    let avail = R.available() - S.extraUse;
    // trim science, then shield, then comms to fit
    for(const k of ["science","shield","comms","green","life"]){ while(Object.values(al).reduce((a,b)=>a+b,0)>avail && al[k]>0) al[k]--; }
    // spend extra on science if battery full
    S.alloc = al; R.runSol();
  }
  return {win:S.result.win, fail:S.result.fail||null, sol:S.history.length, sci:S.sciSent, dose:+S.dose.toFixed(1), air:S.air, food:S.food};
}
"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.goto("file://" + __import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__file__), "..", "index.html")) + "")
    for name, (s, cover) in STRATS.items():
        res = [pg.evaluate(js, [s, cover, seed]) for seed in range(1, 201)]
        wins = [r for r in res if r["win"]]
        fails = {}
        for r in res:
            if not r["win"]: fails[r["fail"]] = fails.get(r["fail"],0)+1
        avg = lambda k, L: round(sum(r[k] for r in L)/max(1,len(L)),1)
        print(f"{name:18s} win {len(wins):3d}/200  sci(win) {avg('sci',wins):5}  dose {avg('dose',res):5}  fails {fails}  avg fail sol {avg('sol',[r for r in res if not r['win']])}")
    b.close()
