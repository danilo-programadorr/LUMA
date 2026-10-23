"""Local durable scheduler: eligibility only, never tools."""
import argparse,os,time
from .executor_worker import service
from .app.database import DEFAULT_URL

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--once',action='store_true');args=parser.parse_args()
    execution=service(os.environ.get('LUMA_DATABASE_URL',DEFAULT_URL))
    try:
        while True:
            print('eligible_transitions='+str(len(execution.tick())))
            if args.once:break
            time.sleep(1)
    finally:execution.store.close()

if __name__=='__main__':main()
