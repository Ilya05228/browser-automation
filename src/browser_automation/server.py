# start_server.py
from camoufox.server import launch_server


def start_server():

    launch_server(
        headless=False,
        port=9223,
        ws_path="camoufox",
        geoip=False,
    )
