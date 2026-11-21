"""Rooftop navigation using published prism geometry and live jet parameters.

This is a strategy hypothesis, not a local replica of the match simulator.
"""

import math
import time
from navigation import inside

TAU=2*math.pi


def segment_distance(x,y,ax,ay,bx,by):
    dx,dy=bx-ax,by-ay
    denominator=dx*dx+dy*dy
    t=max(0,min(1,((x-ax)*dx+(y-ay)*dy)/denominator)) if denominator else 0
    return math.hypot(x-ax-t*dx,y-ay-t*dy)


def clearance(x,y,prism):
    if not inside(x,y,prism["ring"]) or any(inside(x,y,h) for h in prism.get("holes",[])):
        return -1
    best=math.inf
    for ring in (prism["ring"],*prism.get("holes",[])):
        ax,ay=ring[-2:]
        for i in range(0,len(ring),2):
            bx,by=ring[i:i+2]
            best=min(best,segment_distance(x,y,ax,ay,bx,by));ax,ay=bx,by
    return best


def ray_exit(point,direction,prism):
    px,py=point;dx,dy=direction;hits=[]
    for ring in (prism["ring"],*prism.get("holes",[])):
        ax,ay=ring[-2:]
        for i in range(0,len(ring),2):
            bx,by=ring[i:i+2];ex,ey=bx-ax,by-ay
            determinant=dx*ey-dy*ex
            if abs(determinant)>1e-8:
                rx,ry=ax-px,ay-py
                t=(rx*ey-ry*ex)/determinant
                u=(rx*dy-ry*dx)/determinant
                if t>1e-6 and 0<=u<=1:hits.append(t)
            ax,ay=bx,by
    if not hits:return None
    t=min(hits)
    return px+t*dx,py+t*dy


class RoofController:
    def __init__(self,world,config):
        self.world=world;self.config=config
        self.roofs=[]
        radius=config["mech"]["radius"]
        height=config["mech"]["height"]
        for number,prism in enumerate(world.prisms):
            if prism["kind"] not in ("building","stadium"):continue
            box=world.prism_bounds[number]
            points=[]
            # Coarse geometry sampling happens during hello, not decisions.
            for ix in range(math.floor((box[0]+radius+3)/8),math.ceil((box[2]-radius-3)/8)+1):
                for iy in range(math.floor((box[1]+radius+3)/8),math.ceil((box[3]-radius-3)/8)+1):
                    x,y=ix*8.0,iy*8.0
                    c=clearance(x,y,prism)
                    if c<radius+3:continue
                    ground=world.height(x,y)
                    rise=prism["top"]-ground
                    if not 6<=rise<=44:continue
                    if not world.free(x,y,prism["top"],radius,height):continue
                    points.append((c,x,y))
            if not points:continue
            points.sort(reverse=True)
            _,x,y=points[0]
            # Preserve spatially different cover choices, rather than eight
            # adjacent samples at the same center of a large roof.
            selected=[]
            for point in points:
                if all(math.dist(point[1:],other[1:])>10 for other in selected):selected.append(point)
                if len(selected)>=8:break
            self.roofs.append({"id":number,"prism":prism,"center":[x,y],"top":prism["top"],
                               "clearance":points[0][0],"points":[[p[1],p[2]] for p in selected]})
        self.target=None;self.stage=None;self.active_goal=None
        self.select_at=0;self.started=0;self.perch_goal=None;self.perch_plan_at=0
        self.hold_fire=False;self.abort_reason=None
        self.regen_safe=False

    def energy_budget(self,rise,stats):
        jet=stats.get("jet_drain",self.config["mech"].get("jet_drain",15))
        vertical=stats.get("max_rise_speed",10)
        if stats.get("jet_accel",34)<=stats.get("gravity",22) or vertical<=0:return math.inf
        distance=2*stats.get("radius",2.5)+14
        speed=max(1,stats.get("boost_speed",19.5));accel=max(1,stats.get("air_accel",12))
        accelerate_distance=speed*speed/(2*accel)
        horizontal=(math.sqrt(2*distance/accel) if distance<=accelerate_distance else
                    speed/accel+(distance-accelerate_distance)/speed)
        # Allow a second for closed-loop braking and half a second of margin.
        return jet*((rise+2)/vertical+horizontal+1.5)+8

    def safe(self,point,roof,radius,height):
        deadline=getattr(self.world,"geometry_deadline",None)
        if deadline is not None and time.process_time()>=deadline:return False
        return clearance(*point,roof["prism"])>=radius+1 and self.world.free(*point,roof["top"],radius,height)

    def launch_plan(self,roof,position,stats):
        radius=stats.get("radius",2.5);height=stats.get("height",9)
        cx,cy=roof["center"]
        bearing=math.atan2(position[1]-cy,position[0]-cx)
        choices=[]
        for offset in (0,.35,-.35,.7,-.7,1.2,-1.2,math.pi):
            theta=bearing+offset;direction=math.cos(theta),math.sin(theta)
            edge=ray_exit(roof["center"],direction,roof["prism"])
            if edge is None:continue
            launch=[edge[0]+direction[0]*(radius+8),edge[1]+direction[1]*(radius+8)]
            landing=[edge[0]-direction[0]*(radius+6),edge[1]-direction[1]*(radius+6)]
            ground=self.world.height(*launch)
            if not self.safe(landing,roof,radius,height):continue
            if self.world.blocked[self.world.cell(*launch)]:continue
            if not self.world.free(*launch,ground,radius,height):continue
            rise=roof["top"]-ground
            if rise<4 or rise>44:continue
            choices.append((math.dist(position[:2],launch),launch,landing,rise))
        return min(choices,key=lambda p:p[0]) if choices else None

    def choose(self,obs,enemies):
        me=obs["self"];zone=obs["zone"];radius=me["stats"].get("radius",2.5)
        if me["energy"]<60 or zone["next_radius"]<40:return None
        choices=[]
        for roof in self.roofs:
            if math.dist(roof["center"],zone["next_center"])>zone["next_radius"]-radius-12:continue
            distance=math.dist(me["pos"][:2],roof["center"])
            if distance>190:continue
            plan=self.launch_plan(roof,me["pos"],me["stats"])
            if plan is None:continue
            travel,launch,landing,rise=plan
            required=self.energy_budget(rise,me["stats"])
            if required>me["energy"]:continue
            if math.dist(landing,zone["next_center"])>zone["next_radius"]-radius-5:continue
            if any(math.dist(enemy["pos"][:2],launch)<45 for enemy in enemies):continue
            cost=travel*.075-rise*.45-roof["clearance"]*.25
            for enemy in sorted(enemies,key=lambda e:math.dist(e["pos"][:2],roof["center"]))[:3]:
                d=math.dist(enemy["pos"][:2],roof["center"])
                if d<180:
                    exposed=self.world.clear_ray([enemy["pos"][0],enemy["pos"][1],enemy["pos"][2]+7],
                                                 [*roof["center"],roof["top"]+4.5])
                    cost+=12 if exposed is not False else -8
            choices.append((cost,roof,launch,landing,rise))
        return min(choices,key=lambda p:p[0]) if choices else None

    def abandon(self,now,reason):
        self.target=None;self.stage=None;self.active_goal=None
        self.select_at=now+8;self.hold_fire=False;self.abort_reason=reason
        self.regen_safe=False

    def horizontal(self,point,me,boost=False):
        speed=me["stats"].get("boost_speed" if boost else "walk_speed",19.5 if boost else 11.7)
        dx,dy=point[0]-me["pos"][0],point[1]-me["pos"][1]
        vx,vy=me["vel"][:2]
        command=[(dx*1.65-vx*.35)/speed,(dy*1.65-vy*.35)/speed]
        length=math.hypot(*command)
        if length>1:command=[v/length for v in command]
        return command

    def command(self,obs,enemies):
        self.active_goal=None;self.hold_fire=False
        me=obs["self"];now=obs["t"];zone=obs["zone"]
        radius=me["stats"].get("radius",2.5);height=me["stats"].get("height",9)
        if self.target is None and now>=self.select_at:
            self.select_at=now+4
            choice=self.choose(obs,enemies)
            if choice:
                _,self.target,self.launch,self.landing,self.rise=choice
                self.stage="approach";self.started=now
        if self.target is None:return None
        roof=self.target;top=roof["top"];x,y,z=me["pos"]
        if math.dist(roof["center"],zone["next_center"])>zone["next_radius"]-radius-5:
            self.abandon(now,"roof_outside_future_zone");return None
        on_roof=clearance(x,y,roof["prism"])>=radius+.5 and z>=top-.8
        if me["grounded"] and on_roof:self.stage="perch"
        if self.stage=="approach":
            if now-self.started>26:
                self.abandon(now,"approach_timeout");return None
            self.active_goal=self.launch
            if math.dist((x,y),self.launch)>5:return None
            if me["energy"]<self.energy_budget(self.rise,me["stats"])-8:
                if any(math.dist(enemy["pos"][:2],(x,y))<140 for enemy in enemies):
                    self.abandon(now,"unsafe_to_wait_for_jet_energy");return None
                return {"move":[0,0],"boost":False,"jump":False}
            self.stage="climb";self.started=now;self.climb_z=z
        if self.stage=="climb":
            if now-self.started>8 or me["energy"]<6:
                self.abandon(now,"climb_budget_or_timeout");return None
            if now-self.started>1.5 and z<self.climb_z+2:
                self.abandon(now,"overhang_or_no_vertical_progress");return None
            if z<top+1:
                return {"move":self.horizontal(self.launch,me,True),"boost":True,"jump":me["grounded"]}
            self.stage="transfer";self.started=now
        if self.stage=="transfer":
            if now-self.started>5 or me["energy"]<3:
                self.abandon(now,"transfer_timeout");return None
            if on_roof:
                self.stage="land";self.started=now
            else:
                return {"move":self.horizontal(self.landing,me,True),"boost":True,"jump":False}
        if self.stage=="land":
            if now-self.started>6:
                self.abandon(now,"landing_timeout");return None
            if not me["grounded"]:
                return {"move":self.horizontal(roof["center"],me),"boost":False,"jump":False}
            if not on_roof:
                self.abandon(now,"landing_missed");return None
            self.stage="perch"
        if self.stage=="perch":
            if not on_roof:
                self.abandon(now,"left_roof");return None
            wants_regen=me["hp"]<.90*me["max_hp"]
            self.hold_fire=wants_regen and self.regen_safe
            if now>=self.perch_plan_at:
                self.perch_plan_at=now+.6
                points=list(roof["points"])+[roof["center"],[x,y]]
                closest=sorted(enemies,key=lambda e:math.dist(e["pos"][:2],(x,y)))
                if closest and not wants_regen:
                    enemy=closest[0];theta=math.atan2(enemy["pos"][1]-roof["center"][1],enemy["pos"][0]-roof["center"][0])
                    direction=math.cos(theta),math.sin(theta)
                    edge=ray_exit(roof["center"],direction,roof["prism"])
                    if edge:points.append([edge[0]-direction[0]*(radius+3),edge[1]-direction[1]*(radius+3)])
                safe_points=[point for point in points if self.safe(point,roof,radius,height)]
                if not safe_points:
                    deadline=getattr(self.world,"geometry_deadline",None)
                    if deadline is not None and time.process_time()>=deadline:
                        self.perch_plan_at=now+.1;self.regen_safe=False;self.hold_fire=False
                        return {"move":[0,0],"boost":False,"jump":False}
                    self.abandon(now,"no_supported_perch_point");return None
                profiles={}
                def exposure(point):
                    key=tuple(point)
                    if key in profiles:return profiles[key]
                    exposed=0;shootable=0
                    for enemy in closest:
                        enemy_muzzle=[enemy["pos"][0],enemy["pos"][1],enemy["pos"][2]+7]
                        if self.world.clear_ray(enemy_muzzle,[*point,top+height-.5]) is not False:exposed+=1
                        delta=enemy["pos"][2]+4.5-(top+me["stats"].get("muzzle_height",7))
                        pitch=math.atan2(delta,math.dist(point,enemy["pos"][:2]))
                        if me["stats"].get("min_pitch",-.7)<=pitch<=me["stats"].get("max_pitch",1.3):
                            if self.world.clear_ray([*point,top+me["stats"].get("muzzle_height",7)],
                                                    [enemy["pos"][0],enemy["pos"][1],enemy["pos"][2]+4.5]):shootable+=1
                    profiles[key]=exposed,shootable
                    return exposed,shootable
                # Damage suppresses regeneration. Holding fire under unavoidable
                # crossfire only gives up defense; require a concealed point.
                self.regen_safe=wants_regen and any(exposure(point)[0]==0 for point in safe_points)
                self.hold_fire=self.regen_safe
                def score(point):
                    exposed,shootable=exposure(point)
                    value=math.dist(point,(x,y))*.10+exposed*(30 if self.hold_fire else 7)
                    if not self.hold_fire:value-=14*min(1,shootable)
                    return value
                self.perch_goal=min(safe_points,key=score)
            desired=self.horizontal(self.perch_goal,me)
            # Stay on supported roof while walking; no risky boost at edges.
            predicted=[x+desired[0]*me["stats"].get("walk_speed",11.7)*.4,
                       y+desired[1]*me["stats"].get("walk_speed",11.7)*.4]
            if not self.safe(predicted,roof,radius,height):desired=[0,0]
            return {"move":desired,"boost":False,"jump":False}
        return None
