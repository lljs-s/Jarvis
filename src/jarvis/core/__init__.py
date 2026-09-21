"""Der Kern: alles, was Jarvis kann - ohne zu wissen, wer fragt.

Hier liegt die Logik (Agent, Modelle, Werkzeuge). Sie kennt weder HTTP noch
die Oberflaeche. Dadurch koennen CLI und Web-Server denselben Kern benutzen,
und keiner von beiden kann an den Sicherheitspruefungen vorbei.
"""
