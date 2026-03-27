import time
import sys
from core.dsp_engine import engine_instance

engine_instance.start_stream('file', {'filename': 'test_signal.iq', 'format': 'uint8'})
for i in range(5):
    time.sleep(1)
    print(f"{i}s - Is playing: {engine_instance.is_playing}")
    if not engine_instance.worker_thread.is_alive():
        print("Thread died!")
        break
