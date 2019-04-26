from glob import iglob

from exceptions import EmptyFrame


def get_frames(path_pattern):

    frames = []

    for frame_file in sorted(iglob(path_pattern)):
        with open(frame_file, "r") as file:
            frames.append(file.read())

    if not frames or not all(frames):
        raise EmptyFrame("Frame can not be empty")

    return frames
