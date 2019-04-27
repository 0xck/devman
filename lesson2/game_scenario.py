PHRASES = {
    # Только на английском, Repl.it ломается на кириллице
    1957: "First Artificial Earth's Satellite",
    1961: "Gagarin is first human in Space!",
    1965: "Leonov was the first person in outer space!",
    1969: "Armstrong got on the moon!",
    1971: "First orbital space station Salute-1",
    1981: "Flight of the Shuttle Columbia",
    1998: 'ISS start building',
    2004: 'Opportunity arrived on Mars',
    2011: 'Messenger launch to Mercury',
    2019: 'Opportunity sent its last message',
    2020: "Take the plasma gun! Shoot the garbage!",
}


def get_garbage_delay_tics(year):
    if year < 1961:
        return None
    elif year < 1969:
        return 20
    elif year < 1981:
        return 14
    elif year < 1995:
        return 10
    elif year < 2010:
        return 8
    elif year < 2020:
        return 6
    else:
        return 2
