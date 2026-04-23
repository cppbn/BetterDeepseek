from ChatApp.main import app as app1
from SandBox.main import app as app2
import uvicorn
import multiprocessing

def run_app1():
    uvicorn.run(app1, host="127.0.0.1", port=8010)

def run_app2():
    uvicorn.run(app2, host="127.0.0.1", port=8020)

if __name__ == "__main__":
    p1 = multiprocessing.Process(target=run_app1)
    p2 = multiprocessing.Process(target=run_app2)
    p1.start()
    p2.start()
    p1.join()
    p2.join()