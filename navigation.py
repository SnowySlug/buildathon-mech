"""Published-map navigation and geometric shooting checks; standard library only."""

import array
import heapq
import json
import math
from pathlib import Path
import sys


def inside(x, y, ring):
    odd = False
    x0, y0 = ring[-2:]
    for i in range(0, len(ring), 2):
        x1, y1 = ring[i:i + 2]
        if (y0 > y) != (y1 > y) and x < (x1-x0)*(y-y0)/(y1-y0)+x0:
            odd = not odd
        x0, y0 = x1, y1
    return odd


class World:
    step = 5.0

    def __init__(self, directory, config):
        root = Path(directory)
        self.data = json.loads((root / "v2/world.json").read_text())
        self.bounds = self.data["bounds"]
        self.terrain = self.data["terrain"]
        self.heights = array.array("h", (root / "v2/terrain.i16").read_bytes())
        if sys.byteorder != "little":
            self.heights.byteswap()
        self.prisms = self.data["prisms"]
        self.bins = {}
        self.prism_bounds = []
        for number, prism in enumerate(self.prisms):
            ring = prism["ring"]
            bounds = min(ring[::2]), min(ring[1::2]), max(ring[::2]), max(ring[1::2])
            self.prism_bounds.append(bounds)
            for i in range(math.floor(bounds[0]/32), math.floor(bounds[2]/32)+1):
                for j in range(math.floor(bounds[1]/32), math.floor(bounds[3]/32)+1):
                    self.bins.setdefault((i,j), []).append(number)
        self.x0, self.y0 = self.bounds["minX"]+4, self.bounds["minY"]+4
        self.nx = int((self.bounds["maxX"]-self.x0-4)/self.step)+1
        self.ny = int((self.bounds["maxY"]-self.y0-4)/self.step)+1
        self.ground = [self.height(*self.point(n)) for n in range(self.nx*self.ny)]
        raw = bytearray(self.nx*self.ny)
        radius = config["mech"]["radius"]
        height = config["mech"]["height"]
        step_up = config["mech"]["step_up"]
        for p, box in zip(self.prisms, self.prism_bounds):
            min_i = max(0, int((box[0]-self.x0)/self.step)-1)
            max_i = min(self.nx-1, int((box[2]-self.x0)/self.step)+1)
            min_j = max(0, int((box[1]-self.y0)/self.step)-1)
            max_j = min(self.ny-1, int((box[3]-self.y0)/self.step)+1)
            for j in range(min_j, max_j+1):
                for i in range(min_i, max_i+1):
                    n = j*self.nx+i
                    if p["base"] < self.ground[n]+height+.4 and p["top"] > self.ground[n]+step_up:
                        x,y = self.point(n)
                        if inside(x,y,p["ring"]) and not any(inside(x,y,h) for h in p.get("holes",[])):
                            raw[n] = 1
        self.blocked = bytearray(raw)
        for n, flag in enumerate(raw):
            if flag:
                i,j = n%self.nx,n//self.nx
                for dj in (-1,0,1):
                    for di in (-1,0,1):
                        if 0 <= i+di < self.nx and 0 <= j+dj < self.ny:
                            self.blocked[(j+dj)*self.nx+i+di] = 1

    def height(self, x, y):
        t = self.terrain
        u = max(0,min(t["nx"]-1.001,(x-t["minX"])/t["step"]))
        v = max(0,min(t["ny"]-1.001,(y-t["minY"])/t["step"]))
        i,j = int(u),int(v)
        a,b = u-i,v-j
        n = j*t["nx"]+i
        return .01*((1-b)*((1-a)*self.heights[n]+a*self.heights[n+1]) +
                    b*((1-a)*self.heights[n+t["nx"]]+a*self.heights[n+t["nx"]+1]))

    def point(self, n):
        return self.x0+(n%self.nx)*self.step,self.y0+(n//self.nx)*self.step

    def cell(self, x, y):
        i = max(0,min(self.nx-1,round((x-self.x0)/self.step)))
        j = max(0,min(self.ny-1,round((y-self.y0)/self.step)))
        return j*self.nx+i

    def nearest_free(self, n):
        if not self.blocked[n]:
            return n
        i,j = n%self.nx,n//self.nx
        for r in range(1,18):
            best = None
            for dj in range(-r,r+1):
                for di in range(-r,r+1):
                    if max(abs(di),abs(dj)) != r:
                        continue
                    ni,nj = i+di,j+dj
                    if 0<=ni<self.nx and 0<=nj<self.ny:
                        q = nj*self.nx+ni
                        if not self.blocked[q] and (best is None or di*di+dj*dj<best[0]):
                            best = di*di+dj*dj,q
            if best:
                return best[1]
        return n

    def path(self, position, goal, limit=2200):
        start = self.nearest_free(self.cell(*position[:2]))
        finish = self.nearest_free(self.cell(*goal[:2]))
        fi,fj = finish%self.nx,finish//self.nx
        def heuristic(n):
            return math.hypot(n%self.nx-fi,n//self.nx-fj)
        heap = [(heuristic(start),0,start)]
        costs, parents = {start:0}, {}
        best = start
        visited = 0
        while heap and visited < limit:
            _,cost,n = heapq.heappop(heap)
            if cost != costs[n]:
                continue
            visited += 1
            if heuristic(n)<heuristic(best):
                best=n
            if n == finish:
                best=n
                break
            i,j = n%self.nx,n//self.nx
            for di,dj in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                ni,nj = i+di,j+dj
                if not (0<=ni<self.nx and 0<=nj<self.ny):
                    continue
                q=nj*self.nx+ni
                if self.blocked[q]:
                    continue
                if di and dj and (self.blocked[j*self.nx+ni] or self.blocked[nj*self.nx+i]):
                    continue
                length=1.41421356237 if di and dj else 1.0
                rise=self.ground[q]-self.ground[n]
                if rise>self.step*length*1.1:
                    continue
                nc=cost+length+max(0,rise)*.025
                if nc<costs.get(q,math.inf):
                    costs[q]=nc;parents[q]=n
                    heapq.heappush(heap,(nc+heuristic(q),nc,q))
        path=[]
        while best!=start:
            path.append(self.point(best));best=parents[best]
        path.reverse()
        return path

    def candidates(self, x, y, radius=0):
        found=set()
        for i in range(math.floor((x-radius)/32),math.floor((x+radius)/32)+1):
            for j in range(math.floor((y-radius)/32),math.floor((y+radius)/32)+1):
                found.update(self.bins.get((i,j),()))
        return found

    def free(self,x,y,z,radius=2.5,height=9,step_up=1.2):
        b=self.bounds
        if x<b["minX"]+radius or x>b["maxX"]-radius or y<b["minY"]+radius or y>b["maxY"]-radius:
            return False
        for n in self.candidates(x,y,radius+1):
            p=self.prisms[n]
            if p["top"]<=z+step_up or p["base"]>=z+height+.1:
                continue
            for dx,dy in ((0,0),(radius,0),(-radius,0),(0,radius),(0,-radius)):
                if inside(x+dx,y+dy,p["ring"]) and not any(inside(x+dx,y+dy,h) for h in p.get("holes",[])):
                    return False
        return True

    def clear_ray(self,a,b):
        dx,dy,dz=b[0]-a[0],b[1]-a[1],b[2]-a[2]
        found=set()
        steps=max(1,int(math.hypot(dx,dy)/24)+1)
        for k in range(steps+1):
            f=k/steps
            found.update(self.candidates(a[0]+dx*f,a[1]+dy*f))
        for n in found:
            p=self.prisms[n]
            if max(a[2],b[2])<p["base"] or min(a[2],b[2])>p["top"]:
                continue
            hits=[0.0,1.0]
            for ring in [p["ring"],*p.get("holes",[])]:
                x0,y0=ring[-2:]
                for i in range(0,len(ring),2):
                    x1,y1=ring[i:i+2]
                    ex,ey=x1-x0,y1-y0
                    determinant=dx*ey-dy*ex
                    if abs(determinant)>1e-9:
                        rx,ry=x0-a[0],y0-a[1]
                        t=(rx*ey-ry*ex)/determinant
                        u=(rx*dy-ry*dx)/determinant
                        if 0<t<1 and 0<=u<=1:
                            hits.append(t)
                    x0,y0=x1,y1
            hits.sort()
            for left,right in zip(hits,hits[1:]):
                t=(left+right)/2
                x,y,z=a[0]+dx*t,a[1]+dy*t,a[2]+dz*t
                if p["base"]<=z<=p["top"] and inside(x,y,p["ring"]) and not any(inside(x,y,h) for h in p.get("holes",[])):
                    return False
        # Terrain blocks shots too. Sampling is conservative near ground.
        for k in range(1,steps):
            f=k/steps
            if a[2]+dz*f<self.height(a[0]+dx*f,a[1]+dy*f)+.15:
                return False
        return True
