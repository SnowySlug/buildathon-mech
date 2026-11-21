"""Published-map navigation and geometric shooting checks; standard library only."""

import array
import heapq
import json
import math
from pathlib import Path
import sys
import time


def inside(x, y, ring):
    odd = False
    x0, y0 = ring[-2:]
    for i in range(0, len(ring), 2):
        x1, y1 = ring[i:i + 2]
        if (y0 > y) != (y1 > y) and x < (x1-x0)*(y-y0)/(y1-y0)+x0:
            odd = not odd
        x0, y0 = x1, y1
    return odd



def crossed_cells(a,b,step=32):
    """Supercover grid DDA, including bins touched at exact corner crossings."""
    dx,dy=b[0]-a[0],b[1]-a[1]
    i,j=math.floor(a[0]/step),math.floor(a[1]/step)
    end_i,end_j=math.floor(b[0]/step),math.floor(b[1]/step)
    yield i,j
    si=1 if dx>0 else -1 if dx<0 else 0
    sj=1 if dy>0 else -1 if dy<0 else 0
    tx=(((i+1 if si>0 else i)*step-a[0])/dx) if si else math.inf
    ty=(((j+1 if sj>0 else j)*step-a[1])/dy) if sj else math.inf
    delta_x=step/abs(dx) if si else math.inf
    delta_y=step/abs(dy) if sj else math.inf
    remaining=abs(end_i-i)+abs(end_j-j)+3
    while (i,j)!=(end_i,end_j) and remaining>0:
        remaining-=1
        if abs(tx-ty)<1e-12:
            yield i+si,j
            yield i,j+sj
            i+=si;j+=sj;tx+=delta_x;ty+=delta_y
        elif tx<ty:
            i+=si;tx+=delta_x
        else:
            j+=sj;ty+=delta_y
        yield i,j


def exact_clear_ray(world,a,b,inside):
    """None means budget-exhausted, never positive evidence of safe cover."""
    deadline=getattr(world,"geometry_deadline",None)
    def expired():return deadline is not None and time.process_time()>=deadline
    if expired():return None
    dx,dy,dz=b[0]-a[0],b[1]-a[1],b[2]-a[2]
    found=set()
    for cell in crossed_cells(a,b):found.update(world.bins.get(cell,()))
    for number in found:
        if expired():return None
        prism=world.prisms[number]
        if abs(dz)<1e-12:
            if not prism["base"]<=a[2]<=prism["top"]:continue
            low,high=0.0,1.0
        else:
            lower=(prism["base"]-a[2])/dz;upper=(prism["top"]-a[2])/dz
            low=max(0.0,min(lower,upper));high=min(1.0,max(lower,upper))
            if low>=high:continue
        # Z-plane intersections are necessary even when XY never crosses an edge.
        hits=[low,high]
        for ring in (prism["ring"],*prism.get("holes",[])):
            if expired():return None
            x0,y0=ring[-2:]
            for index in range(0,len(ring),2):
                x1,y1=ring[index:index+2]
                ex,ey=x1-x0,y1-y0
                determinant=dx*ey-dy*ex
                if abs(determinant)>1e-9:
                    rx,ry=x0-a[0],y0-a[1]
                    t=(rx*ey-ry*ex)/determinant
                    u=(rx*dy-ry*dx)/determinant
                    if low<t<high and 0<=u<=1:hits.append(t)
                x0,y0=x1,y1
        hits.sort()
        for left,right in zip(hits,hits[1:]):
            if expired():return None
            t=(left+right)/2;x=a[0]+dx*t;y=a[1]+dy*t
            if inside(x,y,prism["ring"]) and not any(inside(x,y,hole) for hole in prism.get("holes",[])):
                return False
    # Terrain sampling is intentionally unchanged in this isolated variant.
    steps=max(1,int(math.hypot(dx,dy)/24)+1)
    for index in range(1,steps):
        if expired():return None
        t=index/steps
        if a[2]+dz*t<world.height(a[0]+dx*t,a[1]+dy*t)+.15:return False
    return True


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
        return exact_clear_ray(self,a,b,inside)
