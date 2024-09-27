import signal


def signal_handler(signal, frame):
    print('You pressed Ctrl+C!')
    exit(0)
