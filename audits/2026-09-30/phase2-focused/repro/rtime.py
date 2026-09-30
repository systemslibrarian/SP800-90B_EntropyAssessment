import sys, time, resource, subprocess
t=time.time()
p=subprocess.run(sys.argv[1:],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
dt=time.time()-t
ru=resource.getrusage(resource.RUSAGE_CHILDREN)
print(f"rc={p.returncode} wall={dt:.1f}s user={ru.ru_utime:.1f}s maxrss={ru.ru_maxrss/1024:.0f}MB :: {' '.join(a.split('/')[-1] for a in sys.argv[1:])}")
