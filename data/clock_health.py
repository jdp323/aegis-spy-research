"""Bounded NTP measurement; never changes the operating-system clock."""
import socket,struct,time,math
from datetime import datetime,timezone
EPOCH=2208988800
def decode_offset(packet,request,t1,t4):
    if len(packet)!=48 or packet[0]>>6==3 or packet[0]&7 not in (4,5) or not 1<=packet[1]<=15 or packet[24:32]!=request[40:48]:raise ValueError('INVALID_NTP_RESPONSE')
    def read(offset):
        sec,frac=struct.unpack('!II',packet[offset:offset+8]);return sec-EPOCH+frac/2**32
    t2,t3=read(32),read(40)
    if t3<t2 or not 0<=t4-t1<=5:raise ValueError('INVALID_NTP_TIMING')
    offset=((t2-t1)+(t3-t4))/2;delay=(t4-t1)-(t3-t2)
    if not math.isfinite(offset) or abs(offset)>86400 or delay<-.01 or delay>5:raise ValueError('INVALID_NTP_TIMING')
    return {'offset_seconds':offset,'roundtrip_seconds':delay}
def measure(host='time.windows.com',timeout=2,exchange=None,clock=time.time):
    at=datetime.now(timezone.utc).isoformat()
    try:
        t1=clock();sec=int(t1)+EPOCH;frac=int((t1-int(t1))*2**32);request=bytearray(48);request[0]=0x23;request[40:48]=struct.pack('!II',sec,frac)
        if exchange:packet=exchange(bytes(request))
        else:
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
                sock.settimeout(timeout);sock.connect((socket.gethostbyname(host),123));sock.send(request);packet=sock.recv(49)
        result=decode_offset(packet,request,t1,clock())
        return {'state':'MEASURED','at':at,'source':host,**result,'system_clock_changed':False}
    except Exception:return {'state':'UNAVAILABLE','at':at,'source':host,'offset_seconds':None,'system_clock_changed':False}
def tick(store,config,now,publish=None,probe=measure):
    from data.models import stamp
    old=store.get('ntp_clock',{})
    if old and 0<=(now-stamp(old['at'])).total_seconds()<3600:return old
    result=probe();result['at']=now.isoformat();store.put('ntp_clock',result)
    if result['offset_seconds'] is not None and abs(result['offset_seconds'])>1.5 and publish and __import__('monitoring.simple_notifications',fromlist=['enabled']).enabled(config,'system'):
        key='ntp-warning-'+now.date().isoformat()
        if not store.get(key):
            store.put(key,{'at':now.isoformat()})
            publish(store,key,'DATA WARNING — Computer clock offset exceeds 1.5 seconds. Run ops/fix_clock_admin.ps1 in an administrator PowerShell terminal: net start w32time; w32tm /resync. AEGIS does not elevate or change time settings.','PRIVATE','owner',kind='RESEARCH')
    return result
