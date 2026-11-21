"""Constant-velocity intercept under the published constant-gravity model."""
import math


def solve(origin,target,velocity,speed,gravity,ttl=7,min_pitch=-.7,max_pitch=1.3):
    """Return earliest positive ballistic intercept (yaw,pitch,time), or None.

    Scan brackets of the quartic norm(r+v*t+[0,0,g*t*t/2])**2=speed**2*t*t,
    then bisect. This is the low/early arc; no simulator or empirical score.
    """
    if speed<=0 or gravity<0 or ttl<=0:return None
    r=[target[k]-origin[k] for k in range(3)]
    def residual(t):
        return sum((r[k]+velocity[k]*t+(gravity*t*t/2 if k==2 else 0))**2 for k in range(3))-speed*speed*t*t
    left=.001;before=residual(left)
    for k in range(1,129):
        right=ttl*k/128;after=residual(right)
        if before>=0 and after<=0:
            lo,hi=left,right
            for _ in range(24):
                mid=(lo+hi)/2
                if residual(mid)>0:lo=mid
                else:hi=mid
            t=(lo+hi)/2
            vector=[r[j]+velocity[j]*t+(gravity*t*t/2 if j==2 else 0) for j in range(3)]
            yaw=math.atan2(vector[1],vector[0]);pitch=math.atan2(vector[2],math.hypot(*vector[:2]))
            if min_pitch<=pitch<=max_pitch:return yaw,pitch,t
        left=right;before=after
    return None


def arc_clear(world,origin,yaw,pitch,speed,gravity,flight):
    """Check bounded short chords, leaving the final impact region unchecked.

    Unknown geometry is never permission to shoot. The final chord intentionally
    ends just before the target surface; collision at the intended impact is OK.
    """
    flat=speed*math.cos(pitch)
    def point(t):return [origin[0]+flat*math.cos(yaw)*t,origin[1]+flat*math.sin(yaw)*t,
                         origin[2]+speed*math.sin(pitch)*t-gravity*t*t/2]
    end=max(0,flight-.04);steps=max(2,min(32,math.ceil(end/.10)))
    previous=origin
    for k in range(1,steps+1):
        current=point(end*k/steps)
        if world.clear_ray(previous,current) is not True:return False
        previous=current
    return True
