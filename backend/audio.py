# audio.py
# 
# Loki Nordstrom 


from winsound import PlaySound, SND_FILENAME, SND_ASYNC


def play_startup():
    PlaySound("assets/sound_startup.wav", SND_FILENAME | SND_ASYNC)

def play_interface():
    PlaySound("assets/sound_interface.wav", SND_FILENAME | SND_ASYNC)
