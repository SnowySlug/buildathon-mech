"""Placement-focused mechfight/1 bot; no score claim without live matches."""

import math
import random
import time
import mechfight as mf
from navigation import World
from roof import RoofController

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
    name="Snowy-Perch-v3"

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
        self.previous_move=[0,0]
        self.target_id=None
        self.roof_controller=RoofController(self.world,self.config)

    def choose_upgrade(self,offer,me):
        priority={"nanites":11,"servos":10,"armor":9,"plating":8.5,"jets":8,
                  "reactor":7.5,"gun_velocity":7,"gun_damage":6.5,"gun_rate":6,
                  "gun_mag":5.8,"laser_damage":6,"laser_charge":6.8,
                  "lightning_range":7,"lightning_efficiency":6,"gyros":5,
                  "sensors":4,"capacitor":5,"mortar_reload":6,"mortar_velocity":5,
                  "mortar_splash":5,"laser_pierce":2,"lightning_chain":4}
        return max(range(len(offer["choices"])),key=lambda i:priority.get(offer["choices"][i]["id"],3))

    def strategic_goal(self,obs,enemies):
        if self.roof_controller.active_goal is not None:return self.roof_controller.active_goal
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
                    if self.world.clear_ray(eye,target): value+=17
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

    def move(self,obs,enemies):
        command=self.roof_controller.command(obs,enemies)
        if command is not None:
            self.previous_move=command["move"]
            self.last_position=obs["self"]["pos"][:2]
            self.stuck=0
            return command["move"],command["boost"],command["jump"]
        desired_goal=self.roof_controller.active_goal
        if desired_goal is not None and (self.goal is None or math.dist(desired_goal,self.goal)>8):self.plan_at=-100
        return self.ground_move(obs,enemies)

    def ground_move(self,obs,enemies):
        me=obs["self"];x,y,z=me["pos"];stats=me["stats"]
        if self.last_position is not None:
            moved=math.dist(me["pos"][:2],self.last_position)
            trying=math.hypot(*self.previous_move)>.5
            self.stuck=self.stuck+.1 if trying and moved<.13 else max(0,self.stuck-.2)
        self.last_position=me["pos"][:2]
        if obs["t"]>=self.plan_at:
            self.goal=self.strategic_goal(obs,enemies)
            self.path=self.world.path(me["pos"],self.goal)
            self.plan_at=obs["t"]+1.5
        while self.path and math.dist((x,y),self.path[0])<6:
            self.path.pop(0)
        waypoint=self.path[0] if self.path else self.goal
        desired=unit(waypoint[0]-x,waypoint[1]-y)
        nearest=min((math.dist(e["pos"][:2],(x,y)) for e in enemies),default=1e6)
        boost=me["energy"]>35 and (nearest<100 or not me["in_zone"] or self.stuck>.6)
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
        regen=me["hp"]<.65*me["max_hp"]
        for enemy in sorted(enemies,key=lambda e:math.dist(e["pos"][:2],(x,y))-(40 if e["id"]==self.target_id else 0)):
            distance=math.dist(enemy["pos"][:2],(x,y))
            if distance>290 or (regen and distance>85):continue
            center=[enemy["pos"][0],enemy["pos"][1],enemy["pos"][2]+4.5*(1+.05*enemy.get("cubes",0))]
            horizontal=math.dist(center[:2],(x,y))
            low=origin[2]+math.tan(stats.get("min_pitch",-.7))*horizontal
            high=origin[2]+math.tan(stats.get("max_pitch",1.3))*horizontal
            target_height=self.config["mech"].get("height",9)*(1+self.config["cubes"].get("size_per_cube",.05)*enemy.get("cubes",0))
            reachable_low=max(low,enemy["pos"][2]+.7)
            reachable_high=min(high,enemy["pos"][2]+target_height-.5)
            if reachable_low>reachable_high:continue
            center[2]=max(reachable_low,min(reachable_high,center[2]))
            if self.world.clear_ray(origin,center):
                score=distance+max(0,enemy.get("hp",1400)-400)*.025
                if enemy["id"]==self.target_id:score-=40
                if enemy.get("charging"):score-=20
                targets.append((score,enemy,center))
        if not targets and not enemies and not regen:
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
            return [yaw,0.0],[False,False],False
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
            if kind=="laser" and distance<ws.get("range",280) and (weapon.get("charge",0)>0 or (weapon["cooldown"]<=.05 and distance>65)):
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
                # Both guns can fire while a laser charges when their own
                # intercept solution matches the actual turret orientation.
                fire[i]=distance<ws.get("range",230) and gun_aligned
                reload=weapon.get("ammo",0)<=0 or (weapon.get("ammo",0)<3 and distance>100)
            elif kind=="laser":
                charge=weapon.get("charge",0)
                fire[i]=primary=="laser" and (charge<ws.get("charge",.75) or not aligned)
            elif kind=="lightning":
                fire[i]=distance<ws.get("range",45) and error_yaw<math.radians(ws.get("cone_deg",30))*.45 and me["energy"]>18
            elif kind=="mortar":fire[i]=primary=="mortar" and aligned
        return [yaw,pitch],fire,reload

    def act(self,obs):
        # Shared across roof scoring and targeting. An exhausted LOS query is
        # unknown, never evidence of safe cover, and never authorizes a shot.
        self.world.geometry_deadline=time.process_time()+.010
        me=obs["self"]
        enemies=[enemy for enemy in obs["mechs"] if enemy["kind"]=="mech"]
        movement,boost,jump=self.move(obs,enemies)
        # Reserve an independent targeting slice so a difficult cover plan
        # cannot consume the entire frame and suppress otherwise safe shots.
        self.world.geometry_deadline=time.process_time()+.004
        aim,fire,reload=self.aim_fire(obs,enemies)
        if self.roof_controller.hold_fire:fire=[False,False]
        if self.roof_controller.stage in ("climb","transfer","land"):
            # Laser charging halves horizontal movement during a transfer.
            for slot,weapon in enumerate(me["weapons"]):
                if weapon and weapon["kind"]=="laser":fire[slot]=False
        act={"tick":obs["tick"],"move":movement,"aim":aim,"boost":boost,"jump":jump,"fire":fire,"reload":reload}
        if obs.get("offer"):act["pick"]=self.choose_upgrade(obs["offer"],me)
        for pickup in sorted(obs["pickups"],key=lambda p:math.dist(p["pos"][:2],me["pos"][:2])):
            if me["weapons"][1] is None and pickup["kind"] in ("laser","lightning"):
                if math.dist(pickup["pos"][:2],me["pos"][:2])<=self.config["loot"]["pickup_radius"] and abs(pickup["pos"][2]-me["pos"][2])<=4:
                    act["take"]=pickup["id"];break
        self.world.geometry_deadline=None
        return act


if __name__=="__main__":
    mf.run(Bot)
