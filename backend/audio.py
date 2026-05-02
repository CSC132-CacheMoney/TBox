from winsound import PlaySound, SND_FILENAME, SND_ASYNC
from os.path import join

collection = {
    "startup": join("assets", "sound_startup.wav"),
    "interface": join("assets", "sound_interface.wav")
}

def play_startup():
    PlaySound(collection["startup"], SND_FILENAME | SND_ASYNC)

def play_interface():
    PlaySound(collection["interface"], SND_FILENAME | SND_ASYNC)
