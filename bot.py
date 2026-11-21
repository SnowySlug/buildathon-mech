"""Placement-focused mechfight/1 bot; no score claim without live matches."""

import math
import random
import time
import gc
import mechfight as mf
from navigation import World

TAU=2*math.pi


def angle_delta(a,b):
    return (a-b+math.pi)%TAU-math.pi


def unit(x,y):
    size=math.hypot(x,y)
    return [x/size,y/size] if size>1e-8 else [0.0,0.0]


def intercept(origin,target,velocity,speed):
    r=[target[i]-origin[i] for i in range(3)]
    a=sum(v*v for v in velocity)-speed*speed
    b=2*sum(r[i]*velocity[i] for i in range(3))
    c=sum(v*v for v in r)
    disc=b*b-4*a*c
    times=[]
    if abs(a)<1e-8:
        if abs(b)>1e-8 and -c/b>0: times=[-c/b]
    elif disc>=0:
        root=math.sqrt(disc)
        times=[t for t in ((-b-root)/(2*a),(-b+root)/(2*a)) if t>0]
    t=min(times) if times else math.sqrt(c)/max(speed,1)
    t=min(t,2.0)
    return [target[i]+velocity[i]*t for i in range(3)]


class Bot:
    name="Snowy-Economy-v9"

    def __init__(self,hello):
        self.config=hello["config"]
        self.rng=random.Random(hello["seed"])
        self.phase=self.rng.random()*TAU
        self.world=World(hello["map"]["dir"],self.config)
        self.path=[]
        self.goal=None
        self.plan_at=-100
        self.last_position=None
        self.stuck=0
        self.history={}
        self.loot_memory={}
        self.cube_memory={}
        self.previous_move=[0,0]
        self.target_id=None
        self.combat_target=None
        self.combat_range=75
        self.healing=False
        self.last_hurt=-100
        self.last_dealt=-100
        gc.collect();gc.disable()

    def secondary(self,me):
        return next((weapon for weapon in me["weapons"] if weapon and weapon["kind"]!="gun"),None)

    def target_score(self,enemy,me):
        distance=math.dist(enemy["pos"][:2],me["pos"][:2])
        score=distance+enemy.get("hp",1400)*.10+enemy.get("cubes",0)*10
        if enemy["id"]==self.target_id:score-=45
        weapon=self.secondary(me)
        if weapon and weapon["kind"]=="lightning" and "laser" in enemy.get("weapons",[]):score-=30
        return score

    def update_memory(self,obs):
        now=obs["t"];me=obs["self"]
        for pickup in obs["pickups"]:self.loot_memory[pickup["id"]]=(pickup,now)
        for cube in obs["cubes"]:self.cube_memory[cube["id"]]=(cube,now)
        visible_loot={pickup["id"] for pickup in obs["pickups"]}
        visible_cubes={cube["id"] for cube in obs["cubes"]}
        for store,visible,expiry in ((self.loot_memory,visible_loot,12),(self.cube_memory,visible_cubes,10)):
            for identifier,(item,seen) in list(store.items()):
                if now-seen>expiry or (math.dist(item["pos"][:2],me["pos"][:2])<4 and identifier not in visible):
                    store.pop(identifier,None)
        for event in obs.get("events",[]):
            if event["type"]=="damaged":self.last_hurt=now;self.healing=False
            elif event["type"]=="hit":self.last_dealt=now
            elif event["type"]=="took":self.loot_memory.pop(event["id"],None)

    def choose_upgrade(self,offer,me):
        priority={"nanites":8,"servos":8,"armor":9,"plating":8.5,"jets":8,
                  "reactor":8,"gun_velocity":8.5,"gun_damage":10,"gun_rate":9.5,
                  "gun_mag":9,"laser_damage":9,"laser_charge":8.5,
                  "lightning_range":11,"lightning_efficiency":10,"gyros":6,
                  "sensors":4,"capacitor":5,"mortar_reload":6,"mortar_velocity":5,
                  "mortar_splash":6,"laser_pierce":4,"lightning_chain":8}
        held={weapon["kind"] for weapon in me["weapons"] if weapon}
        if "lightning" in held:priority["lightning_efficiency"]=12
        gun=next((weapon for weapon in me["weapons"] if weapon and weapon["kind"]=="gun"),None)
        if gun:
            ws=gun["stats"];mag=ws.get("mag",12);cooldown=ws.get("cooldown",.24);reload=ws.get("reload",2.4)
            before=mag/max(1e-9,mag*cooldown+reload)
            after=(mag+8)/max(1e-9,(mag+8)*cooldown+reload*.8)
            # First drum beats a15% damage upgrade for sustained fire;
            # later drums have smaller returns. Use actual upgraded stats.
            priority["gun_mag"]=11.5 if after/before>1.15 else 9.8
        if self.healing and me["hp"]<.5*me["max_hp"]:priority["nanites"]=10.5
        for upgrade in self.config.get("upgrades",[]):
            if upgrade.get("requires") and upgrade["requires"] not in held:
                priority[upgrade["id"]]=1
        return max(range(len(offer["choices"])),key=lambda i:priority.get(offer["choices"][i]["id"],3))

    def retreat_goal(self,obs,enemies):
        me=obs["self"];x,y,z=me["pos"];zone=obs["zone"]
        center=zone["next_center"];radius=zone["next_radius"]
        # Use the next safe area early; little time is available in late phases.
        safe=max(0,radius-14-me["stats"].get("radius",2.5))
        candidates=[(center[0],center[1])]
        if math.dist((x,y),center)<=safe:
            candidates.append((x,y))
        if safe>5:
            ring=min(safe*.78,max(20,safe-45))
            for k in range(16):
                theta=self.phase+k*TAU/16
                candidates.append((center[0]+ring*math.cos(theta),center[1]+ring*math.sin(theta)))
        nearest=sorted(enemies,key=lambda e:math.dist(e["pos"][:2],(x,y)))[:3]
        def score(point):
            px,py=point
            if self.world.blocked[self.world.cell(px,py)]: return 1e8
            value=math.dist((x,y),point)*.04
            for enemy in nearest:
                distance=math.dist(enemy["pos"][:2],point)
                value+=8000/(distance+25)
                if distance<230:
                    target=[enemy["pos"][0],enemy["pos"][1],enemy["pos"][2]+5]
                    eye=[px,py,self.world.height(px,py)+8]
                    if self.world.clear_ray(eye,target) is not False: value+=17
            if not nearest and point==(x,y): value+=6
            return value
        goal=min(candidates,key=score)
        threats=bool(enemies) or me["hp"]<.8*me["max_hp"]
        if not threats:
            loot=[]
            for cube in obs["cubes"]:
                if math.dist(cube["pos"][:2],center)<safe and abs(cube["pos"][2]-z)<5:
                    loot.append((math.dist(cube["pos"][:2],(x,y))*.6,cube["pos"][:2]))
            for pickup in obs["pickups"]:
                if me["weapons"][1] is None and pickup["kind"]!="gun" and abs(pickup["pos"][2]-z)<5:
                    if math.dist(pickup["pos"][:2],center)<safe:
                        loot.append((math.dist(pickup["pos"][:2],(x,y)),pickup["pos"][:2]))
            if loot:
                cost,point=min(loot,key=lambda item:item[0])
                if cost<110: goal=point
        if me["hp"]<.5*me["max_hp"]:
            for drop in obs.get("drops",[]):
                if drop["lands_in"]<8 and math.dist(drop["pos"][:2],(x,y))<90:
                    if all(math.dist(e["pos"][:2],drop["pos"][:2])>100 for e in enemies):
                        goal=drop["pos"][:2]
        return goal

    def strategic_goal(self,obs,enemies):
        me=obs["self"];zone=obs["zone"];x,y,z=me["pos"]
        next_distance=math.dist((x,y),zone["next_center"])
        margin=max(0,zone["next_radius"]-me["stats"].get("radius",2.5)-12)
        outside_next=max(0,next_distance-margin)
        urgent=(not me["in_zone"] or zone["next_radius"]<65 or
                (outside_next>0 and zone["shrink_end"]-obs["t"]<outside_next/me["stats"].get("walk_speed",11.7)+9))
        self.combat_target=None
        if urgent:return self.retreat_goal(obs,enemies)
        nearby=[enemy for enemy in enemies if math.dist(enemy["pos"][:2],(x,y))<145]
        target=min(enemies,key=lambda enemy:self.target_score(enemy,me)) if enemies else None
        if target and math.dist(target["pos"][:2],(x,y))>220:target=None
        # Healing is an explicit break from combat, not an automatic HP gate
        # that stops defending while a pursuer is still able to shoot.
        if self.healing and (me["hp"]>.83*me["max_hp"] or any(math.dist(e["pos"][:2],(x,y))<65 for e in enemies)):
            self.healing=False
        if me["hp"]<.43*me["max_hp"] and obs["t"]-self.last_hurt>1:
            if not target or math.dist(target["pos"][:2],(x,y))>125:self.healing=True
        if self.healing:
            for drop in obs.get("drops",[]):
                if drop["lands_in"]<6 and math.dist(drop["pos"][:2],(x,y))<110:
                    if all(math.dist(enemy["pos"][:2],drop["pos"][:2])>85 for enemy in enemies):return drop["pos"][:2]
            return self.retreat_goal(obs,enemies)
        resources=[]
        for cube,_ in self.cube_memory.values():
            d=math.dist(cube["pos"][:2],(x,y))
            if d<90 and abs(cube["pos"][2]-z)<5 and math.dist(cube["pos"][:2],zone["next_center"])<margin:
                danger=sum(max(0,60-math.dist(enemy["pos"][:2],cube["pos"][:2])) for enemy in nearby)
                resources.append((d*.35+danger*.8,cube["pos"][:2]))
        current_secondary=self.secondary(me)
        if current_secondary is None or current_secondary["kind"]!="lightning":
            weights={"lightning":.45,"mortar":.7,"laser":.85}
            for pickup,_ in self.loot_memory.values():
                d=math.dist(pickup["pos"][:2],(x,y))
                permitted=current_secondary is None or pickup["kind"]=="lightning"
                distance_limit=135 if current_secondary is None else 70
                if permitted and pickup["kind"] in weights and d<distance_limit and abs(pickup["pos"][2]-z)<5:
                    if math.dist(pickup["pos"][:2],zone["next_center"])<margin:
                        danger=sum(max(0,55-math.dist(enemy["pos"][:2],pickup["pos"][:2])) for enemy in nearby)
                        resources.append((d*weights[pickup["kind"]]+danger,pickup["pos"][:2]))
        if resources:
            cost,point=min(resources,key=lambda item:item[0])
            if cost<45 and (len(nearby)<3 or math.dist(point,(x,y))<15):return point
        if target:
            weapon=self.secondary(me)
            kind=weapon["kind"] if weapon else "gun"
            desired=34 if kind=="lightning" and me["energy"]>=9 else 58 if kind=="mortar" else 105 if kind=="laser" else 76
            if kind=="lightning":desired=min(desired,weapon["stats"].get("range",45)*.8)
            if len(nearby)>=3:desired=max(desired,90)
            if target.get("hp",1400)<260 and len(nearby)<=2:desired=min(desired,42)
            self.combat_target=target;self.combat_range=desired
            dx,dy=x-target["pos"][0],y-target["pos"][1]
            direction=unit(dx,dy)
            point=[target["pos"][0]+direction[0]*desired,target["pos"][1]+direction[1]*desired]
            if math.dist(point,zone["center"])<zone["radius"]-10:return point
        # If there is no active pursuer, approach a modest isolated farm target
        # rather than destroying distant crates and leaving their cubes behind.
        farms=[]
        for drone in obs["mechs"]:
            if drone["kind"]=="npc" and math.dist(drone["pos"][:2],(x,y))<110:
                direction=unit(x-drone["pos"][0],y-drone["pos"][1])
                farms.append((math.dist(drone["pos"][:2],(x,y))*.8,[drone["pos"][0]+direction[0]*55,drone["pos"][1]+direction[1]*55]))
        for crate in obs["crates"]:
            if abs(crate["pos"][2]-z)<5:farms.append((math.dist(crate["pos"][:2],(x,y)),crate["pos"][:2]))
        if farms:
            distance,point=min(farms,key=lambda item:item[0])
            if distance<100 and math.dist(point,zone["next_center"])<margin:return point
        return self.retreat_goal(obs,enemies)

    def move(self,obs,enemies):
        me=obs["self"];x,y,z=me["pos"];stats=me["stats"]
        if self.last_position is not None:
            moved=math.dist(me["pos"][:2],self.last_position)
            trying=math.hypot(*self.previous_move)>.5
            self.stuck=self.stuck+.1 if trying and moved<.13 else max(0,self.stuck-.2)
        self.last_position=me["pos"][:2]
        if obs["t"]>=self.plan_at or not me["in_zone"]:
            self.goal=self.strategic_goal(obs,enemies)
            self.path=self.world.path(me["pos"],self.goal)
            self.plan_at=obs["t"]+.7
        while self.path and math.dist((x,y),self.path[0])<6:
            self.path.pop(0)
        waypoint=self.path[0] if self.path else self.goal
        desired=unit(waypoint[0]-x,waypoint[1]-y)
        duel=self.combat_target
        if duel:
            separation=math.dist(duel["pos"][:2],(x,y))
            if abs(separation-self.combat_range)<12:
                radial=unit(x-duel["pos"][0],y-duel["pos"][1])
                side=1 if math.sin(self.phase+obs["t"]*.7)>0 else -1
                desired=[-radial[1]*side,radial[0]*side]
        nearest=min((math.dist(e["pos"][:2],(x,y)) for e in enemies),default=1e6)
        boost=me["energy"]>35 and (nearest<100 or not me["in_zone"] or self.stuck>.6)
        weapon=self.secondary(me)
        if duel and weapon and weapon["kind"]=="lightning":
            boost=me["energy"]>65 and math.dist(duel["pos"][:2],(x,y))>self.combat_range+25
        if not me["in_zone"]:boost=me["energy"]>8
        speed=stats.get("boost_speed",19.5) if boost else stats.get("walk_speed",11.7)
        if math.dist((x,y),waypoint)<3 and nearest>110:
            desired=[0.0,0.0]
        angle=math.atan2(desired[1],desired[0]) if any(desired) else me["aim"][0]
        options=[desired,[0.0,0.0]]
        options.extend([math.cos(angle+k*math.pi/8),math.sin(angle+k*math.pi/8)] for k in range(-8,8))
        radius=stats.get("radius",2.5)
        height=stats.get("height",9)
        zone=obs["zone"]
        bullets=obs.get("projectiles",[])[:45]
        def score(direction):
            dx,dy=direction
            px,py=x+dx*speed*.65,y+dy*speed*.65
            value=-7*(dx*desired[0]+dy*desired[1])
            if duel:
                value+=abs(math.dist((px,py),duel["pos"][:2])-self.combat_range)*1.2
            if not self.world.free(px,py,z,radius,height,stats.get("step_up",1.2)):
                value+=500
            if self.world.height(px,py)>z+max(1.2,math.hypot(px-x,py-y)*1.15):value+=200
            distance=math.dist((px,py),zone["center"])
            if distance>zone["radius"]-radius-3:value+=150+(distance-zone["radius"]+radius+3)*zone["dps"]*.3
            for enemy in enemies:
                ex,ey=enemy["pos"][:2]
                dist=math.hypot(px-ex,py-ey)
                value+=1400/max(18,dist)
                if "lightning" in enemy.get("weapons",[]) and dist<55:value+=(55-dist)*1.2
                if enemy.get("charging"):
                    vx,vy=px-ex,py-ey;eyaw=enemy["aim"][0]
                    along=vx*math.cos(eyaw)+vy*math.sin(eyaw)
                    lateral=abs(vx*math.sin(eyaw)-vy*math.cos(eyaw))
                    if 0<along<280 and lateral<radius+5:value+=80*(1-lateral/(radius+5))
            for bullet in bullets:
                p,v=bullet["pos"],bullet["vel"]
                rx,ry=p[0]-x,p[1]-y
                vx,vy=v[0]-dx*speed,v[1]-dy*speed
                vv=vx*vx+vy*vy
                time=max(0,min(.7,-(rx*vx+ry*vy)/vv)) if vv else 0
                distance=math.hypot(rx+vx*time,ry+vy*time)
                bz=p[2]+v[2]*time
                if bullet["kind"]=="mortar":bz-=.5*self.config["weapons"]["mortar"]["gravity"]*time*time
                if z-2<bz<z+height+2 and distance<radius+3:
                    value+=100*(1-distance/(radius+3))
            return value
        chosen=min(options,key=score)
        jump=False
        if self.stuck>.7 and me["energy"]>25:
            jump=me["grounded"];boost=True
        elif nearest<85 and me["energy"]>55 and int(obs["t"]*10)%24==0:
            jump=me["grounded"]
        self.previous_move=chosen
        return chosen,boost,jump

    def aim_fire(self,obs,enemies):
        me=obs["self"];x,y,z=me["pos"];stats=me["stats"]
        origin=[x,y,z+stats.get("muzzle_height",7)]
        targets=[]
        regen=self.healing
        for enemy in sorted(enemies,key=lambda enemy:self.target_score(enemy,me)):
            distance=math.dist(enemy["pos"][:2],(x,y))
            if distance>290 or (regen and distance>85):continue
            center=[enemy["pos"][0],enemy["pos"][1],enemy["pos"][2]+4.5*(1+.05*enemy.get("cubes",0))]
            if self.world.clear_ray(origin,center):
                score=self.target_score(enemy,me)
                if enemy.get("charging"):score-=20
                targets.append((score,enemy,center))
        if not targets and not enemies and not regen:
            for drone in obs["mechs"]:
                if drone["kind"]!="npc":continue
                distance=math.dist(drone["pos"][:2],(x,y))
                center=[drone["pos"][0],drone["pos"][1],drone["pos"][2]+self.config["npc"].get("height",3.5)*.5]
                if 48<distance<115 and self.world.clear_ray(origin,center):targets.append((distance*.8,drone,center))
            for crate in obs["crates"]:
                distance=math.dist(crate["pos"][:2],(x,y))
                if distance<80 and abs(crate["pos"][2]-z)<15:
                    center=[crate["pos"][0],crate["pos"][1],crate["pos"][2]+1.2]
                    if self.world.clear_ray(origin,center):targets.append((distance,crate,center))
        if not targets:
            # Face the nearest threat for rear armor; otherwise scan in a slow arc.
            if enemies:
                enemy=min(enemies,key=lambda e:math.dist(e["pos"][:2],(x,y)))
                yaw=math.atan2(enemy["pos"][1]-y,enemy["pos"][0]-x)
            else:yaw=self.phase+obs["t"]*.7
            gun=next((weapon for weapon in me["weapons"] if weapon and weapon["kind"]=="gun"),None)
            reload=bool(gun and gun.get("ammo",0)<gun["stats"].get("mag",12) and not gun.get("reload",0))
            return [yaw,0.0],[False,False],reload
        _,target,center=min(targets,key=lambda item:item[0])
        self.target_id=target["id"]
        velocity=target.get("vel",[0,0,0])
        distance=math.dist(center,origin)
        weapons=me["weapons"]
        secondary=next(((i,w) for i,w in enumerate(weapons) if w and w["kind"]!="gun"),None)
        gunpoint=intercept(origin,center,velocity,next((w["stats"].get("speed",252) for w in weapons if w and w["kind"]=="gun"),252))
        aimpoint=gunpoint
        primary="gun"
        pitch=None
        if secondary:
            slot,weapon=secondary;kind=weapon["kind"];ws=weapon["stats"]
            if kind=="laser" and distance<ws.get("range",280) and (weapon.get("charge",0)>0 or weapon["cooldown"]<=.05):
                primary="laser";aimpoint=center
            elif kind=="lightning" and distance<ws.get("range",45):primary="lightning";aimpoint=center
            elif kind=="mortar" and 27<distance<230 and weapon["cooldown"]<=.05:
                speed=ws.get("speed",72);gravity=ws.get("gravity",22)
                mortar_origin=[x,y,z+stats.get("height",9)+.5]
                point=center[:]
                for _ in range(3):
                    horizontal=math.dist(point[:2],(x,y));rise=point[2]-mortar_origin[2]
                    disc=speed**4-gravity*(gravity*horizontal**2+2*rise*speed**2)
                    if disc<0:break
                    pitch=math.atan2(speed*speed-math.sqrt(disc),gravity*max(horizontal,.01))
                    flight=horizontal/(speed*math.cos(pitch))
                    point=[center[i]+velocity[i]*flight for i in range(3)]
                if pitch is not None and stats.get("min_pitch",-.7)<=pitch<=stats.get("max_pitch",1.3):
                    primary="mortar";aimpoint=point
        yaw=math.atan2(aimpoint[1]-y,aimpoint[0]-x)
        pitch=(math.atan2(aimpoint[2]-origin[2],math.dist(aimpoint[:2],(x,y))) if primary!="mortar" else pitch)
        pitch=max(stats.get("min_pitch",-.7),min(stats.get("max_pitch",1.3),pitch))
        error_yaw=abs(angle_delta(yaw,me["aim"][0]));error_pitch=abs(pitch-me["aim"][1])
        radius=2.5*(1+.05*target.get("cubes",0)) if target.get("kind")=="mech" else 1.4
        tolerance=max(.015,math.atan2(radius*.8,max(distance,1)))
        fire=[False,False]
        reload=False
        for i,weapon in enumerate(weapons):
            if not weapon:continue
            ws=weapon["stats"];kind=weapon["kind"]
            aligned=error_yaw<tolerance and error_pitch<tolerance*1.5
            if kind=="gun":
                gun_yaw=math.atan2(gunpoint[1]-y,gunpoint[0]-x)
                gun_pitch=math.atan2(gunpoint[2]-origin[2],math.dist(gunpoint[:2],(x,y)))
                gun_aligned=abs(angle_delta(gun_yaw,me["aim"][0]))<tolerance and abs(gun_pitch-me["aim"][1])<tolerance*1.5
                fire[i]=distance<ws.get("range",230) and gun_aligned
                reload=weapon.get("ammo",0)<=0
            elif kind=="laser":
                charge=weapon.get("charge",0)
                fire[i]=primary=="laser" and (charge<ws.get("charge",.75) or not aligned)
            elif kind=="lightning":
                fire[i]=distance<ws.get("range",45) and error_yaw<math.radians(ws.get("cone_deg",30))*.45 and me["energy"]>=ws.get("energy",3)
            elif kind=="mortar":fire[i]=primary=="mortar" and aligned
        return [yaw,pitch],fire,reload

    def act(self,obs):
        self.world.geometry_deadline=time.process_time()+.010
        self.update_memory(obs)
        me=obs["self"]
        enemies=[enemy for enemy in obs["mechs"] if enemy["kind"]=="mech"]
        if self.combat_target:
            self.combat_target=next((enemy for enemy in enemies if enemy["id"]==self.combat_target["id"]),self.combat_target)
        movement,boost,jump=self.move(obs,enemies)
        self.world.geometry_deadline=time.process_time()+.006
        aim,fire,reload=self.aim_fire(obs,enemies)
        if enemies and self.world.expired():reload=False
        self.world.geometry_deadline=None
        act={"tick":obs["tick"],"move":movement,"aim":aim,"boost":boost,"jump":jump,"fire":fire,"reload":reload}
        if obs.get("offer"):act["pick"]=self.choose_upgrade(obs["offer"],me)
        for pickup in sorted(obs["pickups"],key=lambda p:math.dist(p["pos"][:2],me["pos"][:2])+{"lightning":0,"mortar":3,"laser":6,"gun":100}.get(p["kind"],100)):
            secondary=self.secondary(me)
            swap=bool(secondary and secondary["kind"]!="lightning" and pickup["kind"]=="lightning" and not secondary.get("charge",0))
            if (me["weapons"][1] is None or swap) and pickup["kind"]!="gun":
                if math.dist(pickup["pos"][:2],me["pos"][:2])<=self.config["loot"]["pickup_radius"] and abs(pickup["pos"][2]-me["pos"][2])<=4:
                    act["take"]=pickup["id"]
                    if swap:act["drop"]=next(i for i,weapon in enumerate(me["weapons"]) if weapon and weapon["kind"]!="gun")
                    break
        return act


if __name__=="__main__":
    mf.run(Bot)
